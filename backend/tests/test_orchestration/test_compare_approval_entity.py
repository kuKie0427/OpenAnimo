"""Test that entity_type / entity_ids flow properly through approval nodes.

Covers the entity context path added to _manual_approval_node and its callers
(characters_approval_node, shots_approval_node, outline_approval_node,
character_images_approval_node, shot_images_approval_node).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.orchestration.nodes import (
    _manual_approval_node,
    character_images_approval_node,
    characters_approval_node,
    outline_approval_node,
    shots_approval_node,
)
from app.orchestration.state import Phase2State


# ---------------------------------------------------------------------------
# Helper — build the standard SimpleNamespace runtime used by most tests
# ---------------------------------------------------------------------------


def _make_runtime(*, auto_mode: bool = False, **kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=auto_mode,
            gate_modes=set(),
            agent_context=SimpleNamespace(
                project=SimpleNamespace(id=1, **kwargs),
                run=SimpleNamespace(id=1, thread_id=None),
                session=None,
                completion_info=None,
            ),
            orchestrator=SimpleNamespace(
                _set_run=AsyncMock(return_value=SimpleNamespace()),
                set_run_state=AsyncMock(return_value=SimpleNamespace()),
                ws=SimpleNamespace(send_event=AsyncMock()),
                session=None,
            ),
        )
    )


# ===================================================================
# Test 1 — _manual_approval_node with entity_type / entity_ids
# ===================================================================


@pytest.mark.asyncio
async def test_manual_approval_node_passes_entity_context_to_interrupt(
    monkeypatch,
) -> None:
    """Direct call: verify interrupt() payload receives entity context."""

    interrupt_payloads: list[dict] = []

    def _capture_interrupt(payload: dict) -> str:
        interrupt_payloads.append(payload)
        return ""

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

    runtime = _make_runtime()

    result = await _manual_approval_node(
        runtime,
        approval_stage="characters_approval",
        history_key="plan_characters",
        gate="characters",
        message="test message",
        next_stage="plan_shots",
        entity_type="character",
        entity_ids=[1, 2, 3],
    )

    # fmt: off
    assert len(interrupt_payloads) == 1
    assert interrupt_payloads[0]["entity_type"] == "character"
    assert interrupt_payloads[0]["entity_ids"] == [1, 2, 3]
    # Existing fields still intact
    assert interrupt_payloads[0]["gate"] == "characters"
    assert interrupt_payloads[0]["message"] == "test message"

    # Result routing — no feedback means approved, route to next_stage
    assert result["route_stage"] == "plan_shots"
    assert result["review_requested"] is False
    # fmt: on


# ===================================================================
# Test 2 — characters_approval_node with populated characters
# ===================================================================


@pytest.mark.asyncio
async def test_characters_approval_node_passes_entity_context(monkeypatch) -> None:
    """Wrapper spy: characters_approval_node forwards entity_type + entity_ids."""

    manual_approval_calls: list[dict] = []

    async def _spy_manual_approval(runtime: Any, **kwargs: Any) -> dict[str, Any]:
        manual_approval_calls.append(kwargs)
        return {
            "current_stage": kwargs.get("approval_stage", ""),
            "approval_history": [kwargs.get("history_key", "")],
            "approval_feedback": "",
            "review_requested": True,
            "route_stage": kwargs.get("next_stage", ""),
        }

    monkeypatch.setattr(
        "app.orchestration.nodes._manual_approval_node", _spy_manual_approval
    )

    runtime = _make_runtime(
        characters=[
            SimpleNamespace(id=101, name="Hero"),
            SimpleNamespace(id=102, name="Villain"),
        ],
    )
    state: Phase2State = {"project_id": 1, "run_id": 1}

    await characters_approval_node(state, runtime)

    assert len(manual_approval_calls) == 1
    assert manual_approval_calls[0]["entity_type"] == "character"
    assert manual_approval_calls[0]["entity_ids"] == [101, 102]


# ===================================================================
# Test 3 — shots_approval_node with populated shots
# ===================================================================


@pytest.mark.asyncio
async def test_shots_approval_node_passes_entity_context(monkeypatch) -> None:
    """Wrapper spy: shots_approval_node forwards entity_type + entity_ids
    with merged character + shot summaries."""

    interrupt_payloads: list[dict] = []

    def _capture_interrupt(payload: dict) -> str:
        interrupt_payloads.append(payload)
        return ""

    monkeypatch.setattr(
        "app.orchestration.nodes.interrupt", _capture_interrupt
    )

    runtime = _make_runtime(
        characters=[
            SimpleNamespace(
                id=1, name="Hero", description="Main character",
                image_url="/hero.png", approval_state="approved",
            ),
            SimpleNamespace(
                id=2, name="Villain", description="Antagonist",
                image_url=None, approval_state="approved",
            ),
        ],
        shots=[
            SimpleNamespace(
                id=201, description="Opening", dialogue="Hello",
                image_url="/opening.png", approval_state="draft",
            ),
            SimpleNamespace(
                id=202, description="Climax", dialogue="Fight",
                image_url="/climax.png", approval_state="draft",
            ),
        ],
    )
    state: Phase2State = {"project_id": 1, "run_id": 1}

    await shots_approval_node(state, runtime)

    assert len(interrupt_payloads) == 1
    payload = interrupt_payloads[0]
    assert payload["entity_type"] == "shot"
    assert payload["entity_ids"] == [201, 202]
    # entity_summaries should merge character (first) + shot (second)
    summaries = payload["entity_summaries"]
    assert len(summaries) == 4
    # Characters come first
    assert summaries[0]["entity_id"] == 1
    assert summaries[0]["entity_name"] == "Hero"
    assert summaries[0]["approval_state"] == "approved"
    assert summaries[1]["entity_id"] == 2
    assert summaries[1]["entity_name"] == "Villain"
    # Shots come after
    assert summaries[2]["entity_id"] == 201
    assert summaries[2]["entity_name"] == "Opening"
    assert summaries[2]["approval_state"] == "draft"
    assert summaries[3]["entity_id"] == 202
    assert summaries[3]["entity_name"] == "Climax"


# ===================================================================
# Test 4 — outline_approval_node (no entity context)
# ===================================================================


@pytest.mark.asyncio
async def test_outline_approval_node_omits_entity_context(monkeypatch) -> None:
    """Wrapper spy: outline_approval_node does NOT pass entity_type / entity_ids."""

    manual_approval_calls: list[dict] = []

    async def _spy_manual_approval(runtime: Any, **kwargs: Any) -> dict[str, Any]:
        manual_approval_calls.append(kwargs)
        # Return review_requested=True so outline_approval_node skips DB ops
        return {
            "current_stage": kwargs.get("approval_stage", ""),
            "approval_history": [kwargs.get("history_key", "")],
            "approval_feedback": "",
            "review_requested": True,
            "route_stage": kwargs.get("next_stage", ""),
        }

    monkeypatch.setattr(
        "app.orchestration.nodes._manual_approval_node", _spy_manual_approval
    )

    runtime = _make_runtime()
    state: Phase2State = {"project_id": 1, "run_id": 1}

    await outline_approval_node(state, runtime)

    assert len(manual_approval_calls) == 1
    assert "entity_type" not in manual_approval_calls[0]
    assert "entity_ids" not in manual_approval_calls[0]


# ===================================================================
# Test 5 — characters_approval_node with empty characters
# ===================================================================


@pytest.mark.asyncio
async def test_characters_approval_node_empty_characters_yields_none_ids(
    monkeypatch,
) -> None:
    """When project.characters is empty list, entity_ids is None."""

    manual_approval_calls: list[dict] = []

    async def _spy_manual_approval(runtime: Any, **kwargs: Any) -> dict[str, Any]:
        manual_approval_calls.append(kwargs)
        return {
            "current_stage": kwargs.get("approval_stage", ""),
            "approval_history": [kwargs.get("history_key", "")],
            "approval_feedback": "",
            "review_requested": True,
            "route_stage": kwargs.get("next_stage", ""),
        }

    monkeypatch.setattr(
        "app.orchestration.nodes._manual_approval_node", _spy_manual_approval
    )

    runtime = _make_runtime(characters=[])
    state: Phase2State = {"project_id": 1, "run_id": 1}

    await characters_approval_node(state, runtime)

    assert len(manual_approval_calls) == 1
    assert manual_approval_calls[0]["entity_type"] == "character"
    assert manual_approval_calls[0]["entity_ids"] is None


# ===================================================================
# Test 6 — character_images_approval_node with populated characters
# ===================================================================


@pytest.mark.asyncio
async def test_character_images_approval_node_passes_entity_context(
    monkeypatch,
) -> None:
    """Wrapper spy: character_images_approval_node forwards entity_type + entity_ids."""

    manual_approval_calls: list[dict] = []

    async def _spy_manual_approval(runtime: Any, **kwargs: Any) -> dict[str, Any]:
        manual_approval_calls.append(kwargs)
        return {
            "current_stage": kwargs.get("approval_stage", ""),
            "approval_history": [kwargs.get("history_key", "")],
            "approval_feedback": "",
            "review_requested": True,
            "route_stage": kwargs.get("next_stage", ""),
        }

    monkeypatch.setattr(
        "app.orchestration.nodes._manual_approval_node", _spy_manual_approval
    )

    runtime = _make_runtime(
        characters=[
            SimpleNamespace(id=301, name="Mentor"),
            SimpleNamespace(id=302, name="Sidekick"),
        ],
    )
    state: Phase2State = {"project_id": 1, "run_id": 1}

    await character_images_approval_node(state, runtime)

    assert len(manual_approval_calls) == 1
    assert manual_approval_calls[0]["entity_type"] == "character"
    assert manual_approval_calls[0]["entity_ids"] == [301, 302]


# ===================================================================
# Test 7 — auto_mode short-circuits interrupt() even with entity context
# ===================================================================


@pytest.mark.asyncio
async def test_manual_approval_node_auto_mode_skips_interrupt_with_entity(
    monkeypatch,
) -> None:
    """auto_mode=True: _manual_approval_node returns auto-approval, never calls
    interrupt(), even when entity_type / entity_ids are provided."""

    interrupt_invoked = False

    def _fail_interrupt(payload: dict) -> str:
        nonlocal interrupt_invoked
        interrupt_invoked = True
        raise AssertionError("interrupt() should NOT be called in auto mode")

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _fail_interrupt)

    runtime = _make_runtime(auto_mode=True)

    result = await _manual_approval_node(
        runtime,
        approval_stage="shot_images_approval",
        history_key="render_shots",
        gate="render",
        message="dummy",
        next_stage="critique_shot_images",
        entity_type="shot",
        entity_ids=[1, 2],
    )

    assert not interrupt_invoked
    assert result["route_stage"] == "critique_shot_images"
    assert result["review_requested"] is False

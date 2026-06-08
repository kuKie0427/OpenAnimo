"""Test per-gate gate_modes feature for approval nodes.

Covers:
- gate_modes allows specific gates to auto-pass while others interrupt
- auto_mode=True backward compatibility (all gates auto)
- auto_mode=False backward compatibility (all gates manual)
- CRITIC_GATE_MAP translation for critique gates
- gate_modes with invalid gate names
- shot_images_approval_node unconditional auto-approval (not affected by gate_modes)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

import app.orchestration.nodes as nodes_mod
from app.orchestration.nodes import (
    _manual_approval_node,
    _critic_interrupt,
    shot_images_approval_node,
    CRITIC_GATE_MAP,
)



# -------------------------------------------------------------------
# Helper - build the standard SimpleNamespace runtime with gate_modes
# -------------------------------------------------------------------


def _make_runtime(
    *, auto_mode: bool = False, gate_modes: set[str] | None = None, **kwargs: Any
) -> SimpleNamespace:
    resolved_gate_modes = set() if gate_modes is None else gate_modes
    return SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=auto_mode,
            gate_modes=resolved_gate_modes,
            agent_context=SimpleNamespace(
                project=SimpleNamespace(id=1, **kwargs),
                run=SimpleNamespace(id=1, thread_id=None),
                session=None,
                completion_info=None,
                settings=SimpleNamespace(
                    critique_enabled=True, critique_max_rounds=2
                ),
            ),
            orchestrator=SimpleNamespace(
                _set_run=AsyncMock(return_value=SimpleNamespace()),
                set_run_state=AsyncMock(return_value=SimpleNamespace()),
                ws=SimpleNamespace(send_event=AsyncMock()),
                session=None,
            ),
        )
    )


# -------------------------------------------------------------------
# Helper - manage interrupt monkeypatch with module-level setattr
# -------------------------------------------------------------------


def _patch_interrupt(fake_func):
    """Replace nodes_mod.interrupt with fake_func, return original for restore."""
    original = nodes_mod.interrupt
    nodes_mod.interrupt = fake_func
    return original


def _restore_interrupt(original):
    nodes_mod.interrupt = original


# ===================================================================
# Test 1 — gate_modes={"outline"} allows outline to auto-pass
#         & other gates still interrupt
# ===================================================================


@pytest.mark.asyncio
async def test_gate_modes_outline_auto_passes() -> None:
    """gate_modes={"outline"}: outline gate should auto-approve."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"outline"})
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(
            AssertionError("should not be called")
        )
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="outline_approval",
            history_key="plan_outline",
            gate="outline",
            message="msg",
            next_stage="plan_characters",
        )

        assert result["route_stage"] == "plan_characters"
        assert result["review_requested"] is False
        assert result["approval_feedback"] == ""
    finally:
        _restore_interrupt(orig)


@pytest.mark.asyncio
async def test_gate_modes_outline_auto_other_gates_still_interrupt() -> None:
    """gate_modes={"outline"}: characters gate should still interrupt."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"outline"})

    tracker: dict[str, bool] = {"called": False}

    def _fake_interrupt(payload) -> None:
        tracker["called"] = True
        return None

    orig = _patch_interrupt(_fake_interrupt)
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="characters_approval",
            history_key="plan_characters",
            gate="characters",
            message="msg",
            next_stage="plan_shots",
        )

        assert tracker["called"], "interrupt should have been called"
        assert result["route_stage"] == "plan_shots"
        assert result["review_requested"] is False
    finally:
        _restore_interrupt(orig)


# ===================================================================
# Test 2 — only render-stage gates auto-pass
# ===================================================================


@pytest.mark.asyncio
async def test_gate_modes_render_stage_only() -> None:
    """gate_modes={"character_images","shot_images"}: only render stage auto-passes."""
    runtime = _make_runtime(
        auto_mode=False, gate_modes={"character_images", "shot_images"}
    )

    tracker: dict[str, bool] = {"called": False}

    def _fake_interrupt_char(payload) -> None:
        tracker["called"] = True
        return None

    orig = _patch_interrupt(_fake_interrupt_char)
    try:
        await _manual_approval_node(
            runtime,
            approval_stage="characters_approval",
            history_key="plan_characters",
            gate="characters",
            message="msg",
            next_stage="plan_shots",
        )
        assert tracker["called"], "characters gate should interrupt"
    finally:
        _restore_interrupt(orig)


# ===================================================================
# Test 3 — auto_mode=True backward compatibility
# ===================================================================


@pytest.mark.asyncio
async def test_auto_mode_true_legacy() -> None:
    """auto_mode=True (no gate_modes): all gates auto-approve (backward compat)."""
    runtime = _make_runtime(auto_mode=True)
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(
            AssertionError("should not be called")
        ),
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="shots_approval",
            history_key="plan_shots",
            gate="shots",
            message="msg",
            next_stage="render_characters",
        )
        assert result["route_stage"] == "render_characters"
        assert result["review_requested"] is False
    finally:
        _restore_interrupt(orig)


# ===================================================================
# Test 4 — auto_mode=False backward compatibility
# ===================================================================


@pytest.mark.asyncio
async def test_auto_mode_false_legacy() -> None:
    """auto_mode=False (no gate_modes): all gates interrupt (backward compat)."""
    runtime = _make_runtime(auto_mode=False)

    tracker: dict[str, bool] = {"called": False}

    def _fake_interrupt(payload) -> None:
        tracker["called"] = True
        return None

    orig = _patch_interrupt(_fake_interrupt)
    try:
        await _manual_approval_node(
            runtime,
            approval_stage="compose_approval",
            history_key="compose_merge",
            gate="compose",
            message="msg",
            next_stage="__end__",
        )
        assert tracker["called"], "interrupt should have been called"
    finally:
        _restore_interrupt(orig)


# ===================================================================
# Test 5 — gate_modes with critique gates
# ===================================================================


@pytest.mark.asyncio
async def test_critic_interrupt_gate_modes_critique_characters() -> None:
    """gate_modes={"critique_characters"}: critique_character_images gate is auto-skipped."""
    runtime = _make_runtime(
        auto_mode=False, gate_modes={"critique_characters"}
    )
    agent_ctx = runtime.context.agent_context

    result = await _critic_interrupt(
        runtime,
        agent_ctx,
        "critique_character_images",
        {
            "entity_type": "character",
            "total": 2,
            "results": [],
        },
    )

    assert result == {}, "gate_modes with mapped critique gate should skip interrupt"


@pytest.mark.asyncio
async def test_critic_interrupt_gate_modes_critique_shot_images() -> None:
    """gate_modes={"critique_shots"}: critique_shot_images gate is auto-skipped."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"critique_shots"})
    agent_ctx = runtime.context.agent_context

    result = await _critic_interrupt(
        runtime,
        agent_ctx,
        "critique_shot_images",
        {
            "entity_type": "shot",
            "total": 2,
            "results": [],
        },
    )
    assert result == {}


# ===================================================================
# Test 6 — gate_modes empty set = all manual
# ===================================================================


@pytest.mark.asyncio
async def test_gate_modes_empty_set_all_manual() -> None:
    """gate_modes=set(): all gates interrupt (same as auto_mode=False)."""
    runtime = _make_runtime(auto_mode=False, gate_modes=set())

    tracker: dict[str, bool] = {"called": False}

    def _fake_interrupt(payload) -> None:
        tracker["called"] = True
        return None

    orig = _patch_interrupt(_fake_interrupt)
    try:
        await _manual_approval_node(
            runtime,
            approval_stage="outline_approval",
            history_key="plan_outline",
            gate="outline",
            message="msg",
            next_stage="plan_characters",
        )
        assert tracker["called"], "interrupt should have been called"
    finally:
        _restore_interrupt(orig)


# ===================================================================
# Test 7 — invalid gate names in gate_modes are harmless
# ===================================================================


@pytest.mark.asyncio
async def test_gate_modes_invalid_names_ignored() -> None:
    """gate_modes with invalid names: valid gate 'outline' still auto-passes."""
    runtime = _make_runtime(
        auto_mode=False, gate_modes={"invalid_name", "outline"}
    )
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(
            AssertionError("should not be called")
        ),
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="outline_approval",
            history_key="plan_outline",
            gate="outline",
            message="msg",
            next_stage="plan_characters",
        )
        assert result["route_stage"] == "plan_characters"
    finally:
        _restore_interrupt(orig)


# ===================================================================
# Test 8 — CRITIC_GATE_MAP correctness
# ===================================================================


def test_critic_gate_map_translation() -> None:
    """CRITIC_GATE_MAP correctly maps critique node names to gate_modes keys."""
    assert CRITIC_GATE_MAP["critique_character_images"] == "critique_characters"
    assert CRITIC_GATE_MAP["critique_shot_images"] == "critique_shots"
    assert len(CRITIC_GATE_MAP) == 2


# ===================================================================
# Test 9 — shot_images_approval_node unconditional auto-approval
# ===================================================================


@pytest.mark.asyncio
async def test_shot_images_auto_approval_video_invalid_not_affected() -> None:
    """shot_images_approval_node unconditional auto-approval on invalid video provider.
    This is NOT affected by gate_modes."""
    orchestrator = SimpleNamespace(
        _set_run=AsyncMock(return_value=SimpleNamespace()),
        set_run_state=AsyncMock(return_value=SimpleNamespace()),
        ws=SimpleNamespace(send_event=AsyncMock()),
        session=SimpleNamespace(),
    )
    project = SimpleNamespace(id=1)
    run = SimpleNamespace(
        id=2, provider_snapshot={"video": {"valid": False}}
    )
    agent_ctx = SimpleNamespace(
        project=project,
        run=run,
        session=SimpleNamespace(),
        target_ids=None,
        completion_info=None,
    )
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=False,
            gate_modes=set(),
            orchestrator=orchestrator,
            agent_context=agent_ctx,
        )
    )
    state = SimpleNamespace(status="draft")
    result = await shot_images_approval_node(state, runtime)

    assert result["route_stage"] == "critique_shot_images"
    assert result["review_requested"] is False


# ===================================================================
# Test 12 — gate_modes matches characters/shots/character_images/shot_images
# ===================================================================


@pytest.mark.asyncio
async def test_gate_modes_characters_auto_passes() -> None:
    """gate_modes={"characters"}: characters gate auto-approves (gate name matches)."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"characters"})
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(AssertionError("should not be called"))
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="characters_approval",
            history_key="plan_characters",
            gate="characters",
            message="msg",
            next_stage="plan_shots",
        )
        assert result["route_stage"] == "plan_shots"
        assert result["review_requested"] is False
    finally:
        _restore_interrupt(orig)


@pytest.mark.asyncio
async def test_gate_modes_shots_auto_passes() -> None:
    """gate_modes={"shots"}: shots gate auto-approves (gate name matches)."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"shots"})
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(AssertionError("should not be called"))
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="shots_approval",
            history_key="plan_shots",
            gate="shots",
            message="msg",
            next_stage="render_characters",
        )
        assert result["route_stage"] == "render_characters"
        assert result["review_requested"] is False
    finally:
        _restore_interrupt(orig)


@pytest.mark.asyncio
async def test_gate_modes_character_images_auto_passes() -> None:
    """gate_modes={"character_images"}: character_images gate auto-approves."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"character_images"})
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(AssertionError("should not be called"))
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="character_images_approval",
            history_key="render_characters",
            gate="character_images",
            message="msg",
            next_stage="critique_character_images",
        )
        assert result["route_stage"] == "critique_character_images"
        assert result["review_requested"] is False
    finally:
        _restore_interrupt(orig)


@pytest.mark.asyncio
async def test_gate_modes_shot_images_auto_passes() -> None:
    """gate_modes={"shot_images"}: shot_images gate auto-approves."""
    runtime = _make_runtime(auto_mode=False, gate_modes={"shot_images"})
    orig = _patch_interrupt(
        lambda payload: (_ for _ in ()).throw(AssertionError("should not be called"))
    )
    try:
        result = await _manual_approval_node(
            runtime,
            approval_stage="shot_images_approval",
            history_key="render_shots",
            gate="shot_images",
            message="msg",
            next_stage="critique_shot_images",
        )
        assert result["route_stage"] == "critique_shot_images"
        assert result["review_requested"] is False
    finally:
        _restore_interrupt(orig)

    state = await shot_images_approval_node({}, runtime)
    assert state["route_stage"] == "critique_shot_images"

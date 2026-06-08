"""Tests for entity-level cleanup and target_ids pipeline.

Covers:
- _cleanup_for_rerun with target_ids routing (None / character-only / shot-only / both)
- _build_entity_summaries helper for character and shot entity types
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.agents.orchestrator import GenerationOrchestrator
from app.config import Settings
from app.orchestration.nodes import (
    _build_entity_summaries,
    shot_images_approval_node,
    shots_approval_node,
)
from app.orchestration.state import Phase2State


# ---------------------------------------------------------------------------
# Helpers — patterns from test_agents/test_orchestrator.py
# ---------------------------------------------------------------------------


class MockWsManager:
    def __init__(self) -> None:
        self.events: list[tuple[int, dict]] = []

    async def send_event(self, project_id: int, event: dict) -> None:
        self.events.append((project_id, event))


class FakeResult:
    def __init__(self, rows: list[Any] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeSession:
    def __init__(
        self,
        project: Any = None,
        run: Any = None,
        rows: list[Any] | None = None,
        scalars_result: list[Any] | None = None,
    ) -> None:
        self.project = project
        self.run = run
        self.rows = rows or []
        self.scalars_result = scalars_result
        self.executed: list[Any] = []
        self.added: list[Any] = []
        self.commits = 0
        self.refreshed: list[Any] = []
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeResult:
        self.executed.append(statement)
        return FakeResult(rows=self.scalars_result or self.rows, scalar=None)

    async def get(self, model: Any, ident: Any) -> Any | None:
        if model.__name__ == "Project":
            return self.project
        if model.__name__ == "AgentRun":
            return self.run
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        self.refreshed.append(obj)

    async def rollback(self) -> None:
        self.rollbacks += 1

    def add(self, obj: Any) -> None:
        self.added.append(obj)


def _make_orchestrator(project_id: int = 1) -> GenerationOrchestrator:
    """Create a minimal orchestrator for cleanup tests (no real DB)."""
    project = SimpleNamespace(id=project_id)
    session = FakeSession(project=project)
    return GenerationOrchestrator(
        settings=Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            anthropic_api_key="test",
            image_api_key="test",
            video_api_key="test",
        ),
        ws=MockWsManager(),
        session=session,
    )


def _make_runtime(*, auto_mode: bool = False, **kwargs: Any) -> SimpleNamespace:
    """Build a SimpleNamespace runtime matching the pattern from test_compare_approval_entity."""
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
# Test 1 — target_ids=None → full cleanup (backward compatible)
# ===================================================================


@pytest.mark.asyncio
async def test_cleanup_target_ids_none_full_cleanup(monkeypatch: Any) -> None:
    """target_ids=None → sub-cleanup functions receive no id filters.

    When target_ids is None, _cleanup_for_rerun sets character_ids=None and
    shot_ids=None, so all sub-functions are called with only project_id
    (full cleanup — backward compatible with old behavior).
    """
    orch = _make_orchestrator()
    called: list[tuple[str, int, Any]] = []

    async def clear_chars(pid: int, character_ids: Any = None) -> None:
        called.append(("clear_chars", pid, character_ids))

    async def clear_shots(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_shots", pid, shot_ids))

    async def clear_videos(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_videos", pid, shot_ids))

    monkeypatch.setattr(orch, "_clear_character_images", clear_chars)
    monkeypatch.setattr(orch, "_clear_shot_images", clear_shots)
    monkeypatch.setattr(orch, "_clear_shot_videos", clear_videos)

    await orch._cleanup_for_rerun(1, "render", mode="incremental", target_ids=None)

    assert called == [
        ("clear_chars", 1, None),
        ("clear_shots", 1, None),
        ("clear_videos", 1, None),
    ]


# ===================================================================
# Test 2 — target_ids.character_ids=[3] → character-only targeting
# ===================================================================


@pytest.mark.asyncio
async def test_cleanup_target_ids_character_only(monkeypatch: Any) -> None:
    """target_ids.character_ids=[3] → character cleanup targeted, shots full."""
    orch = _make_orchestrator()
    called: list[tuple[str, int, Any]] = []

    async def clear_chars(pid: int, character_ids: Any = None) -> None:
        called.append(("clear_chars", pid, character_ids))

    async def clear_shots(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_shots", pid, shot_ids))

    async def clear_videos(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_videos", pid, shot_ids))

    monkeypatch.setattr(orch, "_clear_character_images", clear_chars)
    monkeypatch.setattr(orch, "_clear_shot_images", clear_shots)
    monkeypatch.setattr(orch, "_clear_shot_videos", clear_videos)

    target_ids = SimpleNamespace(character_ids=[3], shot_ids=[])

    await orch._cleanup_for_rerun(
        1, "render", mode="incremental", target_ids=target_ids
    )

    assert called == [
        ("clear_chars", 1, [3]),
        ("clear_shots", 1, None),
        ("clear_videos", 1, None),
    ]


# ===================================================================
# Test 3 — empty character_ids → treated as None
# ===================================================================


@pytest.mark.asyncio
async def test_cleanup_target_ids_empty_character_ids(monkeypatch: Any) -> None:
    """target_ids.character_ids=[] → empty list treated as None (full cleanup)."""
    orch = _make_orchestrator()
    called: list[tuple[str, int, Any]] = []

    async def clear_chars(pid: int, character_ids: Any = None) -> None:
        called.append(("clear_chars", pid, character_ids))

    async def clear_shots(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_shots", pid, shot_ids))

    async def clear_videos(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_videos", pid, shot_ids))

    monkeypatch.setattr(orch, "_clear_character_images", clear_chars)
    monkeypatch.setattr(orch, "_clear_shot_images", clear_shots)
    monkeypatch.setattr(orch, "_clear_shot_videos", clear_videos)

    target_ids = SimpleNamespace(character_ids=[], shot_ids=[])

    await orch._cleanup_for_rerun(
        1, "render", mode="incremental", target_ids=target_ids
    )

    assert called == [
        ("clear_chars", 1, None),
        ("clear_shots", 1, None),
        ("clear_videos", 1, None),
    ]


# ===================================================================
# Test 4 — target_ids.shot_ids=[5,7] → shot-only targeting
# ===================================================================


@pytest.mark.asyncio
async def test_cleanup_target_ids_shot_only(monkeypatch: Any) -> None:
    """target_ids.shot_ids=[5,7] → shot cleanup targeted, characters full."""
    orch = _make_orchestrator()
    called: list[tuple[str, int, Any]] = []

    async def clear_chars(pid: int, character_ids: Any = None) -> None:
        called.append(("clear_chars", pid, character_ids))

    async def clear_shots(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_shots", pid, shot_ids))

    async def clear_videos(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_videos", pid, shot_ids))

    monkeypatch.setattr(orch, "_clear_character_images", clear_chars)
    monkeypatch.setattr(orch, "_clear_shot_images", clear_shots)
    monkeypatch.setattr(orch, "_clear_shot_videos", clear_videos)

    target_ids = SimpleNamespace(character_ids=[], shot_ids=[5, 7])

    await orch._cleanup_for_rerun(
        1, "render", mode="incremental", target_ids=target_ids
    )

    assert called == [
        ("clear_chars", 1, None),
        ("clear_shots", 1, [5, 7]),
        ("clear_videos", 1, [5, 7]),
    ]


# ===================================================================
# Test 5 — render incremental + both character_ids and shot_ids
# ===================================================================


@pytest.mark.asyncio
async def test_cleanup_render_incremental_with_both_ids(monkeypatch: Any) -> None:
    """render incremental + target_ids with character_ids=[1,2] and shot_ids=[3,4].

    All three sub-cleanup functions should receive the correct targeted IDs.
    """
    orch = _make_orchestrator()
    called: list[tuple[str, int, Any]] = []

    async def clear_chars(pid: int, character_ids: Any = None) -> None:
        called.append(("clear_chars", pid, character_ids))

    async def clear_shots(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_shots", pid, shot_ids))

    async def clear_videos(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_videos", pid, shot_ids))

    monkeypatch.setattr(orch, "_clear_character_images", clear_chars)
    monkeypatch.setattr(orch, "_clear_shot_images", clear_shots)
    monkeypatch.setattr(orch, "_clear_shot_videos", clear_videos)

    target_ids = SimpleNamespace(character_ids=[1, 2], shot_ids=[3, 4])

    await orch._cleanup_for_rerun(
        1, "render", mode="incremental", target_ids=target_ids
    )

    assert called == [
        ("clear_chars", 1, [1, 2]),
        ("clear_shots", 1, [3, 4]),
        ("clear_videos", 1, [3, 4]),
    ]


# ===================================================================
# Test 6 — compose incremental + target_ids.shot_ids → only videos
# ===================================================================


@pytest.mark.asyncio
async def test_cleanup_compose_incremental_with_shot_ids(monkeypatch: Any) -> None:
    """compose incremental + target_ids.shot_ids=[10] → only _clear_shot_videos called."""
    orch = _make_orchestrator()
    called: list[tuple[str, int, Any]] = []

    async def clear_videos(pid: int, shot_ids: Any = None) -> None:
        called.append(("clear_videos", pid, shot_ids))

    monkeypatch.setattr(orch, "_clear_shot_videos", clear_videos)

    target_ids = SimpleNamespace(character_ids=[], shot_ids=[10])

    await orch._cleanup_for_rerun(
        1, "compose", mode="incremental", target_ids=target_ids
    )

    assert called == [
        ("clear_videos", 1, [10]),
    ]


# ===================================================================
# Test 7 — _build_entity_summaries character type
# ===================================================================


def test_build_entity_summaries_character() -> None:
    """_build_entity_summaries character type returns correct summary dicts.

    Only characters whose id is in entity_ids are included. Fields map as:
    - entity_name ← name
    - description ← description
    - image_url, approval_state ← direct attributes
    """
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            agent_context=SimpleNamespace(
                project=SimpleNamespace(
                    characters=[
                        SimpleNamespace(
                            id=1,
                            name="Alice",
                            description="Hero",
                            image_url="alice.png",
                            approval_state="approved",
                        ),
                        SimpleNamespace(
                            id=2,
                            name="Bob",
                            description="Sidekick",
                            image_url="bob.png",
                            approval_state="draft",
                        ),
                        SimpleNamespace(
                            id=3,
                            name="Charlie",
                            description="Villain",
                            image_url=None,
                            approval_state="draft",
                        ),
                    ]
                )
            )
        )
    )

    result = _build_entity_summaries(runtime, "character", [1, 3])

    assert len(result) == 2
    assert result[0]["entity_id"] == 1
    assert result[0]["entity_name"] == "Alice"
    assert result[0]["description"] == "Hero"
    assert result[0]["image_url"] == "alice.png"
    assert result[0]["approval_state"] == "approved"
    assert result[1]["entity_id"] == 3
    assert result[1]["entity_name"] == "Charlie"
    assert result[1]["description"] == "Villain"
    assert result[1]["image_url"] is None
    assert result[1]["approval_state"] == "draft"


# ===================================================================
# Test 8 — _build_entity_summaries shot type
# ===================================================================


def test_build_entity_summaries_shot() -> None:
    """_build_entity_summaries shot type returns correct summary dicts.

    Shot summaries differ from character: entity_name ← description attribute,
    description ← dialogue attribute (not shot description).
    """
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            agent_context=SimpleNamespace(
                project=SimpleNamespace(
                    shots=[
                        SimpleNamespace(
                            id=101,
                            description="Opening scene",
                            dialogue="Hello world",
                            image_url="shot1.png",
                            approval_state="approved",
                        ),
                        SimpleNamespace(
                            id=102,
                            description="Action sequence",
                            dialogue="Fight!",
                            image_url="shot2.png",
                            approval_state="draft",
                        ),
                        SimpleNamespace(
                            id=103,
                            description="Closing scene",
                            dialogue=None,
                            image_url=None,
                            approval_state="draft",
                        ),
                    ]
                )
            )
        )
    )

    result = _build_entity_summaries(runtime, "shot", [101, 103])

    assert len(result) == 2
    assert result[0]["entity_id"] == 101
    assert result[0]["entity_name"] == "Opening scene"
    # shot uses dialogue as description field
    assert result[0]["description"] == "Hello world"
    assert result[0]["image_url"] == "shot1.png"
    assert result[0]["approval_state"] == "approved"
    assert result[1]["entity_id"] == 103
    assert result[1]["entity_name"] == "Closing scene"
    assert result[1]["description"] is None
    assert result[1]["image_url"] is None
    assert result[1]["approval_state"] == "draft"


# ===================================================================
# Test 9 — shots_approval_node with merged character + shot summaries
# ===================================================================


@pytest.mark.asyncio
async def test_shots_approval_includes_characters(monkeypatch) -> None:
    """shots_approval_node merges character summaries into entity_summaries payload.

    Characters (already approved) appear first in the merged list;
    shots (pending approval) appear after. entity_type stays "shot"
    and entity_ids stays the shot IDs.
    """
    interrupt_payloads: list[dict] = []

    def _capture_interrupt(payload: dict) -> str:
        interrupt_payloads.append(payload)
        return ""

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

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
    summaries = payload["entity_summaries"]
    assert len(summaries) == 4
    # Characters come first
    assert summaries[0]["entity_id"] == 1
    assert summaries[0]["entity_name"] == "Hero"
    assert summaries[0]["approval_state"] == "approved"
    assert summaries[1]["entity_id"] == 2
    assert summaries[1]["entity_name"] == "Villain"
    assert summaries[1]["approval_state"] == "approved"
    # Shots come after
    assert summaries[2]["entity_id"] == 201
    assert summaries[2]["entity_name"] == "Opening"
    assert summaries[2]["approval_state"] == "draft"
    assert summaries[3]["entity_id"] == 202
    assert summaries[3]["entity_name"] == "Climax"
    assert summaries[3]["approval_state"] == "draft"


# ===================================================================
# Test 10 — shot_images_approval_node with merged summaries
# ===================================================================


@pytest.mark.asyncio
async def test_shot_images_approval_includes_character_images(monkeypatch) -> None:
    """shot_images_approval_node merges character summaries into interrupt payload.

    _is_video_provider_invalid is patched to return False so the node
    proceeds to the human-approval path instead of auto-approving.
    """
    interrupt_payloads: list[dict] = []

    def _capture_interrupt(payload: dict) -> str:
        interrupt_payloads.append(payload)
        return ""

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)
    monkeypatch.setattr(
        "app.orchestration.nodes._is_video_provider_invalid", lambda _: False
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

    await shot_images_approval_node(state, runtime)

    assert len(interrupt_payloads) == 1
    payload = interrupt_payloads[0]
    assert payload["entity_type"] == "shot"
    assert payload["entity_ids"] == [201, 202]
    summaries = payload["entity_summaries"]
    assert len(summaries) == 4
    # Characters first
    assert summaries[0]["entity_id"] == 1
    assert summaries[0]["entity_name"] == "Hero"
    assert summaries[0]["approval_state"] == "approved"
    assert summaries[1]["entity_id"] == 2
    assert summaries[1]["entity_name"] == "Villain"
    assert summaries[1]["approval_state"] == "approved"
    # Shots after
    assert summaries[2]["entity_id"] == 201
    assert summaries[2]["entity_name"] == "Opening"
    assert summaries[2]["approval_state"] == "draft"
    assert summaries[3]["entity_id"] == 202
    assert summaries[3]["entity_name"] == "Climax"
    assert summaries[3]["approval_state"] == "draft"


# ===================================================================
# Test 11 — auto_mode skips interrupt with merged summaries
# ===================================================================


@pytest.mark.asyncio
async def test_merged_summaries_respect_auto_mode(monkeypatch) -> None:
    """auto_mode=True: shots_approval_node returns auto-approval, never calls interrupt."""
    interrupt_invoked = False

    def _fail_interrupt(payload: dict) -> str:
        nonlocal interrupt_invoked
        interrupt_invoked = True
        raise AssertionError("interrupt() should NOT be called in auto mode")

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _fail_interrupt)

    runtime = _make_runtime(
        auto_mode=True,
        characters=[
            SimpleNamespace(
                id=1, name="Hero", description="Main character",
                image_url="/hero.png", approval_state="approved",
            ),
        ],
        shots=[
            SimpleNamespace(
                id=201, description="Opening", dialogue="Hello",
                image_url="/opening.png", approval_state="draft",
            ),
        ],
    )
    state: Phase2State = {"project_id": 1, "run_id": 1}

    result = await shots_approval_node(state, runtime)

    assert not interrupt_invoked
    assert result["route_stage"] == "render_characters"
    assert result["review_requested"] is False

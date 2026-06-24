from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.orchestration.runtime import (
    build_graph_config,
    build_phase2_runtime_context,
    build_stage_recovery_config,
    get_checkpoint_history,
)


# --- build_graph_config ---


def test_build_graph_config_with_thread_id():
    run = SimpleNamespace(thread_id="tid-123", id=42)
    cfg = build_graph_config(run)
    assert cfg == {"configurable": {"thread_id": "tid-123"}}


def test_build_graph_config_fallback_to_id():
    run = SimpleNamespace(thread_id=None, id=42)
    cfg = build_graph_config(run)
    assert cfg == {"configurable": {"thread_id": "agent-run-42"}}


def test_build_graph_config_empty_thread_id():
    run = SimpleNamespace(thread_id="  ", id=99)
    cfg = build_graph_config(run)
    assert cfg == {"configurable": {"thread_id": "agent-run-99"}}


def test_build_graph_config_no_id_raises():
    run = SimpleNamespace(thread_id=None, id=None)
    with pytest.raises(ValueError, match="Run must define either thread_id or id"):
        build_graph_config(run)


def test_build_graph_config_arbitrary_object():
    run = SimpleNamespace(thread_id=None, id=None)
    with pytest.raises(ValueError, match="Run must define either thread_id or id"):
        build_graph_config(run)


# --- build_phase2_runtime_context ---


def test_build_phase2_runtime_context_defaults():
    ctx = build_phase2_runtime_context(orchestrator="orch", agent_context="ac")
    assert ctx.orchestrator == "orch"
    assert ctx.agent_context == "ac"
    assert ctx.start_stage == "plan_outline"
    assert ctx.auto_mode is False


def test_build_phase2_runtime_context_custom():
    ctx = build_phase2_runtime_context(
        orchestrator="orch",
        agent_context="ac",
        start_stage="script",
        auto_mode=True,
    )
    assert ctx.start_stage == "script"
    assert ctx.auto_mode is True


# --- build_stage_recovery_config ---


@pytest.mark.asyncio
async def test_build_stage_recovery_config_async():
    run = SimpleNamespace(thread_id="tid-1", id=1)

    class FakeSnapshot:
        def __init__(self, next, config):
            self.next = next
            self.config = config

    async def fake_history(config, limit=None):
        yield FakeSnapshot(next=("script",), config={"configurable": {"thread_id": "tid-1", "from": "snap"}})
        yield FakeSnapshot(next=("plan",), config={"configurable": {"thread_id": "tid-1"}})

    graph = SimpleNamespace(aget_state_history=fake_history)
    cfg = await build_stage_recovery_config(graph, run, before_stage="script")
    assert cfg["configurable"]["from"] == "snap"


@pytest.mark.asyncio
async def test_build_stage_recovery_config_no_match_returns_default():
    run = SimpleNamespace(thread_id="tid-1", id=1)

    async def empty_history(config, limit=None):
        return
        yield  # pragma: no cover

    graph = SimpleNamespace(aget_state_history=empty_history)
    cfg = await build_stage_recovery_config(graph, run, before_stage="script")
    assert cfg == {"configurable": {"thread_id": "tid-1"}}


@pytest.mark.asyncio
async def test_build_stage_recovery_config_sync_fallback():
    run = SimpleNamespace(thread_id="tid-1", id=1)

    class FakeSnapshot:
        def __init__(self):
            self.next = ("character",)
            self.config = {"configurable": {"thread_id": "tid-1", "sync": True}}

    graph = SimpleNamespace(get_state_history=lambda config, limit=None: [FakeSnapshot()])
    cfg = await build_stage_recovery_config(graph, run, before_stage="character")
    assert cfg["configurable"]["sync"] is True


# --- get_checkpoint_history ---


@pytest.mark.asyncio
async def test_get_checkpoint_history_async():
    run = SimpleNamespace(thread_id="tid-1", id=1)
    snapshots = ["s1", "s2"]

    async def fake_history(config, limit=None):
        for s in snapshots:
            yield s

    graph = SimpleNamespace(aget_state_history=fake_history)
    result = await get_checkpoint_history(graph, run)
    assert result == ["s1", "s2"]


@pytest.mark.asyncio
async def test_get_checkpoint_history_sync_fallback():
    run = SimpleNamespace(thread_id="tid-1", id=1)

    def fake_history(config, limit=None):
        return ["s1", "s2"]

    graph = SimpleNamespace(get_state_history=fake_history)
    result = await get_checkpoint_history(graph, run)
    assert result == ["s1", "s2"]


@pytest.mark.asyncio
async def test_get_checkpoint_history_with_limit():
    run = SimpleNamespace(thread_id="tid-1", id=1)
    captured_limit = {}

    async def fake_history(config, limit=None):
        captured_limit["limit"] = limit
        yield "s1"

    graph = SimpleNamespace(aget_state_history=fake_history)
    await get_checkpoint_history(graph, run, limit=5)
    assert captured_limit["limit"] == 5

from __future__ import annotations

from operator import add
from types import SimpleNamespace
from typing import Any
from typing import Annotated, get_args, get_origin, get_type_hints
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.agents.orchestrator import GenerationOrchestrator
from app.orchestration.nodes import (
    _normalize_resume_value,
    _auto_approval_result,
    _approval_result,
    _manual_approval_node,
    shot_images_approval_node,
    review_node,
    route_after_characters_approval,
    route_after_shots_approval,
    route_after_character_images_approval,
    route_after_shot_images_approval,
    route_after_compose_videos,
    route_after_compose_merge,
    route_after_compose_approval,
    route_after_review,
    route_after_critique_character_images,
    route_after_critique_shot_images,
    route_from_start,
)


class MockWsManager:
    def __init__(self):
        self.events = []

    async def send_event(self, project_id: int, event: dict):
        self.events.append((project_id, event))


def test_phase2_state_contract_uses_thread_id_and_stage_history_reducer() -> None:
    from app.orchestration.state import Phase2State

    hints = get_type_hints(Phase2State, include_extras=True)

    assert hints["project_id"] is int
    assert hints["run_id"] is int
    assert hints["thread_id"] is str
    assert hints["current_stage"] is str

    stage_history_hint = hints["stage_history"]
    assert get_origin(stage_history_hint) is Annotated
    assert get_args(stage_history_hint)[1] is add

    assert "shot_id" not in hints
    assert "artifact_id" not in hints


def test_phase2_runtime_config_uses_persisted_run_thread_id() -> None:
    from app.orchestration.runtime import build_graph_config
    from app.models.run import Run

    run = Run(project_id=7, thread_id="thread-7")

    assert build_graph_config(run) == {"configurable": {"thread_id": "thread-7"}}


def test_route_helpers_fall_back_to_expected_stages() -> None:
    assert route_after_characters_approval({}) == "plan_shots"
    assert route_after_shots_approval({}) == "render_characters"
    assert route_after_character_images_approval({}) == "critique_character_images"
    assert route_after_shot_images_approval({}) == "critique_shot_images"
    assert route_after_compose_videos({}) == "compose_merge"
    assert route_after_compose_merge({}) == "add_audio"
    assert route_after_compose_approval({}) == "__end__"
    assert route_after_review({}) == "plan_characters"
    assert route_after_critique_character_images({}) == "render_shots"
    assert route_after_critique_shot_images({}) == "compose_videos"
    assert route_from_start({}) == "plan_outline"


def test_approval_result_helpers_set_review_routing() -> None:
    approved = _approval_result(
        approval_stage="characters_approval",
        history_key="plan_characters",
        next_stage="plan_shots",
        feedback="",
    )
    revised = _approval_result(
        approval_stage="characters_approval",
        history_key="plan_characters",
        next_stage="plan_shots",
        feedback="needs work",
    )
    auto = _auto_approval_result(
        approval_stage="characters_approval",
        history_key="plan_characters",
        next_stage="plan_shots",
    )

    assert approved["route_stage"] == "plan_shots"
    assert approved["review_requested"] is False
    assert revised["route_stage"] == "review"
    assert revised["review_requested"] is True
    assert auto["approval_feedback"] == ""


@pytest.mark.asyncio
async def test_manual_approval_node_auto_mode_short_circuits() -> None:
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=True,
            gate_modes=set(),
            agent_context=SimpleNamespace(
                project=SimpleNamespace(id=1),
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

    result = await _manual_approval_node(
        runtime,
        approval_stage="characters_approval",
        history_key="plan_characters",
        gate="plan",
        message="msg",
        next_stage="plan_shots",
    )

    assert result["route_stage"] == "plan_shots"
    assert result["review_requested"] is False


@pytest.mark.asyncio
async def test_manual_approval_node_normalizes_interrupt_resume(monkeypatch) -> None:
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=False,
            gate_modes=set(),
            agent_context=SimpleNamespace(
                project=SimpleNamespace(id=1),
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

    monkeypatch.setattr("app.orchestration.nodes.interrupt", lambda payload: {"feedback": "  ok  "})

    result = await _manual_approval_node(
        runtime,
        approval_stage="characters_approval",
        history_key="plan_characters",
        gate="plan",
        message="msg",
        next_stage="plan_shots",
    )

    assert result["approval_feedback"] == "ok"
    assert result["route_stage"] == "review"


@pytest.mark.asyncio
async def test_manual_approval_node_routes_to_review_when_feedback_present(monkeypatch) -> None:
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=False,
            gate_modes=set(),
            agent_context=SimpleNamespace(
                project=SimpleNamespace(id=1),
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

    monkeypatch.setattr("app.orchestration.nodes.interrupt", lambda payload: " needs review ")

    result = await _manual_approval_node(
        runtime,
        approval_stage="characters_approval",
        history_key="plan_characters",
        gate="plan",
        message="msg",
        next_stage="plan_shots",
    )

    assert result["review_requested"] is True
    assert result["route_stage"] == "review"


def test_phase2_graph_exports_durable_entrypoints() -> None:
    import app.orchestration as orchestration

    assert callable(orchestration.build_phase2_graph)
    assert orchestration.phase2_graph is not None

    compiled = orchestration.build_phase2_graph().compile()

    assert compiled is not None


class _NoopAgent:
    def __init__(self, name: str, executed: list[str]) -> None:
        self.name = name
        self._executed = executed

    async def run_outline(self, _ctx: Any) -> None:
        self._executed.append(f"{self.name}_outline")

    async def run_characters(self, _ctx: Any) -> None:
        self._executed.append(f"{self.name}_characters")

    async def run_shots(self, _ctx: Any) -> None:
        self._executed.append(f"{self.name}_shots")

    async def run_videos(self, _ctx: Any) -> None:
        self._executed.append(f"{self.name}_videos")

    async def run_merge(self, _ctx: Any) -> None:
        self._executed.append(f"{self.name}_merge")

    async def run(self, _ctx: Any) -> None:
        self._executed.append(self.name)


class _Ws:
    async def send_event(self, _project_id: int, _event: dict[str, Any]) -> None:
        return None


class _Orchestrator:
    def __init__(self, executed: list[str]) -> None:
        self.ws = _Ws()
        # Mock session for _check_stage_completeness: return scalar_one=0 so check passes silently
        _exec_result = AsyncMock()
        _exec_result.scalar_one = MagicMock(return_value=0)
        self.session = MagicMock()
        self.session.execute = AsyncMock(return_value=_exec_result)
        self.agents = [
            _NoopAgent("outline", executed),
            _NoopAgent("plan", executed),
            _NoopAgent("render", executed),
            _NoopAgent("compose", executed),
            _NoopAgent("review", executed),
        ]

    def _agent_index(self, agent_name: str) -> int:
        for index, agent in enumerate(self.agents):
            if agent.name == agent_name:
                return index
        raise ValueError(agent_name)

    async def _set_run(self, run: Any, **fields: Any) -> Any:
        for key, value in fields.items():
            setattr(run, key, value)
        return run

    async def set_run_state(self, run: Any, **fields: Any) -> Any:
        return await self._set_run(run, **fields)

    def get_agent(self, name: str) -> _NoopAgent:
        return self.agents[self._agent_index(name)]

    async def cleanup_for_rerun(self, project_id: int, start_agent: str, mode: str = "full") -> None:
        return None


def _initial_state(start_stage: str) -> dict[str, Any]:
    return {
        "project_id": 1,
        "run_id": 1,
        "thread_id": "agent-run-1",
        "current_stage": start_stage,
        "stage_history": [],
        "approval_history": [],
        "artifact_lineage": [],
        "review_requested": False,
        "approval_feedback": "",
        "route_stage": start_stage,
        "route_mode": "full",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_stage", "production_node_name", "approval_node_name", "expected_agents", "expected_gate"),
    [
        (
            "plan_characters",
            "plan_characters_node",
            "characters_approval_node",
            ["plan_characters"],
            "characters",
        ),
        (
            "render_characters",
            "render_characters_node",
            "character_images_approval_node",
            ["render_characters"],
            "character_images",
        ),
    ],
)
async def test_phase2_graph_routes_into_approval_before_next_stage(
    start_stage: str,
    production_node_name: str,
    approval_node_name: str,
    expected_agents: list[str],
    expected_gate: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.orchestration import nodes as nodes_module
    from app.orchestration.runtime import build_phase2_runtime_context

    executed: list[str] = []
    orchestrator = _Orchestrator(executed)
    runtime_context = build_phase2_runtime_context(
        orchestrator=orchestrator,
        agent_context=SimpleNamespace(
            project=SimpleNamespace(id=1),
            run=SimpleNamespace(id=1, resource_type=None, resource_id=None, provider_snapshot={}),
            session=None,
            target_ids=None,
            completion_info=None,
        ),
        start_stage=start_stage,  # type: ignore[arg-type]
        auto_mode=False,
    )
    runtime = SimpleNamespace(context=runtime_context)
    interrupted: dict[str, Any] = {}

    def _pause(payload: dict[str, Any]) -> dict[str, Any]:
        interrupted["payload"] = payload
        return payload

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _pause)

    production_node = getattr(nodes_module, production_node_name)
    approval_node = getattr(nodes_module, approval_node_name)

    stage_state = await production_node(_initial_state(start_stage), runtime)
    approval_state = await approval_node(stage_state, runtime)

    assert executed == expected_agents
    assert approval_state["route_stage"] == "review"
    assert interrupted["payload"]["gate"] == expected_gate


@pytest.mark.asyncio
async def test_phase2_graph_compose_skips_to_approval_after_substeps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.orchestration.nodes import (
        compose_approval_node,
        compose_merge_node,
        compose_videos_node,
    )
    from app.orchestration.runtime import build_phase2_runtime_context

    executed: list[str] = []
    orchestrator = _Orchestrator(executed)
    runtime_context = build_phase2_runtime_context(
        orchestrator=orchestrator,
        agent_context=SimpleNamespace(
            project=SimpleNamespace(id=1),
            run=SimpleNamespace(id=1, resource_type=None, resource_id=None, provider_snapshot={}),
            session=None,
            target_ids=None,
            completion_info=None,
        ),
        start_stage="compose_videos",  # type: ignore[arg-type]
        auto_mode=False,
    )
    runtime = SimpleNamespace(context=runtime_context)
    interrupted: dict[str, Any] = {}

    def _approve(payload: dict[str, Any]) -> dict[str, str]:
        interrupted["payload"] = payload
        return {"action": "approve"}

    monkeypatch.setattr("app.orchestration.nodes.interrupt", _approve)

    compose_state = await compose_videos_node(_initial_state("compose_videos"), runtime)
    merge_state = await compose_merge_node(compose_state, runtime)
    approval_state = await compose_approval_node(merge_state, runtime)

    assert executed == ["compose_videos", "compose_merge"]
    assert approval_state["current_stage"] == "compose_approval"
    assert approval_state["approval_feedback"] == ""
    assert approval_state["route_stage"] == "__end__"
    assert interrupted["payload"]["gate"] == "compose"


@pytest.mark.asyncio
async def test_compose_videos_skips_when_video_provider_invalid() -> None:
    """When video provider is invalid, compose_videos node skips its work."""
    from app.orchestration.nodes import compose_videos_node

    executed: list[str] = []
    orchestrator = _Orchestrator(executed)
    runtime = SimpleNamespace(
        context=SimpleNamespace(
            auto_mode=False,
            orchestrator=orchestrator,
            agent_context=SimpleNamespace(
                project=SimpleNamespace(id=1),
                run=SimpleNamespace(
                    id=1,
                    resource_type=None,
                    resource_id=None,
                    provider_snapshot={"video": {"valid": False}},
                ),
                session=None,
                target_ids=None,
                completion_info=None,
            ),
        )
    )

    state = await compose_videos_node({}, runtime)

    assert executed == []  # compose agent was never called
    assert "stage:compose_videos" in state.get("artifact_lineage", [])
    assert "stage:compose_merge" in state.get("artifact_lineage", [])
    assert state["video_generation_skipped"] is True
    assert route_after_compose_videos(state) == "__end__"


def test_normalize_resume_value_handles_supported_shapes() -> None:
    assert _normalize_resume_value(None) == ""
    assert _normalize_resume_value("  yes  ") == "yes"
    assert _normalize_resume_value({"feedback": "  fine  "}) == "fine"
    assert _normalize_resume_value({"text": "  ok  "}) == "ok"
    assert _normalize_resume_value(123) == "123"


@pytest.mark.asyncio
async def test_shot_images_approval_auto_routes_to_compose_when_video_invalid() -> None:
    orchestrator = GenerationOrchestrator(
        settings=Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            anthropic_api_key="test",
            image_api_key="test",
            video_api_key="test",
        ),
        ws=MockWsManager(),
        session=None,
    )
    project = SimpleNamespace(id=1)
    run = SimpleNamespace(id=2, provider_snapshot={"video": {"valid": False}})
    agent_ctx = SimpleNamespace(
        project=project, run=run, session=SimpleNamespace(), target_ids=None, completion_info=None
    )
    runtime = SimpleNamespace(
        context=SimpleNamespace(auto_mode=False, gate_modes=set(), orchestrator=orchestrator, agent_context=agent_ctx)
    )

    state = await shot_images_approval_node({}, runtime)

    assert state["route_stage"] == "critique_shot_images"


def test_route_helpers_prefer_route_stage_and_fallbacks():
    assert route_from_start({}) == "plan_outline"
    assert route_after_review({}) == "plan_characters"
    assert route_after_characters_approval({}) == "plan_shots"
    assert route_after_characters_approval({"review_requested": True}) == "review"
    assert route_after_shots_approval({}) == "render_characters"
    assert route_after_shots_approval({"review_requested": True}) == "review"
    assert route_after_shot_images_approval({}) == "critique_shot_images"


@pytest.mark.asyncio
async def test_review_node_routes_to_plan_and_cleans_up(monkeypatch):
    orchestrator = GenerationOrchestrator(
        settings=Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            anthropic_api_key="test",
            image_api_key="test",
            video_api_key="test",
        ),
        ws=MockWsManager(),
        session=SimpleNamespace(refresh=lambda obj: None),
    )
    project = SimpleNamespace(id=1)
    run = SimpleNamespace(id=2)
    agent_ctx = SimpleNamespace(
        project=project,
        run=run,
        session=SimpleNamespace(),
        user_feedback="keep it short",
        feedback_type="plan",
        rerun_mode=None,
        target_ids=None,
        completion_info=None,
    )
    runtime = SimpleNamespace(
        context=SimpleNamespace(orchestrator=orchestrator, agent_context=agent_ctx)
    )

    async def review_run(ctx):
        return {"start_agent": "plan", "mode": "incremental", "target_ids": None}

    review_agent = SimpleNamespace(run=review_run)
    orchestrator.agents = [SimpleNamespace(name="plan"), review_agent]
    monkeypatch.setattr(orchestrator, "_agent_index", lambda name: 1 if name == "review" else 0)

    cleaned = {"called": False}

    async def fake_cleanup(project_id, start_agent, mode="full"):
        cleaned["called"] = True
        cleaned["args"] = (project_id, start_agent, mode)

    monkeypatch.setattr(orchestrator, "_cleanup_for_rerun", fake_cleanup)

    async def fake_refresh(obj):
        return None

    orchestrator.session = SimpleNamespace(refresh=fake_refresh)

    state = await review_node({"approval_feedback": "need shorter"}, runtime)

    assert cleaned["called"] is True
    assert cleaned["args"] == (1, "plan", "incremental")
    assert state["route_stage"] == "plan_characters"
    assert state["route_mode"] == "incremental"

"""E2E tests for AgentTrace records via live backend API."""

from __future__ import annotations

import sqlite3

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlmodel import select

from app.agents import orchestrator as orchestrator_mod
from app.api.v1.routes import generation as generation_routes
from app.models.agent_run import AgentRun
from app.models.agent_trace import AgentTrace
from app.services import agent_runner as agent_runner_mod
from app.services.fake_text import FakeTextService
from app.services.provider_resolution import resolve_project_provider_settings
from tests.agent_fixtures import FakeImageService, FakeVideoService


pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def _stub_async_provider_resolution(
    monkeypatch: Any, e2e_stub_services: Any, test_db_engine_sessionmaker: Any
) -> None:
    """Stub provider resolution, factory imports, Redis, BG tasks, audio, DB bindings.

    Six issues addressed:
    1. resolve_project_provider_settings_async does live API probing → stub it
    2. create_text_service etc. are imported via 'from X import Y' style in
       orchestrator.py / critic.py / agent_runner.py, creating local bindings
       that the conftest-level monkeypatch on text_factory cannot reach.
       We patch the local bindings directly.
    3. conftest patches get_redis with AsyncMock class (not awaitable), which
       breaks _cleanup_run. We override with a proper awaitable mock.
    4. ASGITransport does not execute Starlette BackgroundTasks. We patch
       BackgroundTasks.add_task to execute immediately so the pipeline runs.
    5. ComposeAgent.run_add_audio runs FFmpeg on fake video URLs that don't
       exist as local files. We stub it as a no-op.
    """

    async def _fake_resolver(project: Any, settings: Any, **kwargs: Any) -> Any:
        return resolve_project_provider_settings(project, settings)

    monkeypatch.setattr(
        generation_routes, "resolve_project_provider_settings_async", _fake_resolver
    )

    # Patch local 'from X import Y' bindings for create_text_service
    monkeypatch.setattr(
        orchestrator_mod, "create_text_service", lambda s: FakeTextService(s)
    )
    monkeypatch.setattr(
        agent_runner_mod, "create_text_service", lambda s: FakeTextService(s)
    )

    # Patch local 'from X import Y' bindings for create_image_service
    monkeypatch.setattr(
        orchestrator_mod, "create_image_service", lambda s: FakeImageService()
    )
    monkeypatch.setattr(
        agent_runner_mod, "create_image_service", lambda s: FakeImageService()
    )

    # Patch local 'from X import Y' bindings for create_video_service
    monkeypatch.setattr(
        orchestrator_mod, "create_video_service", lambda s: FakeVideoService()
    )
    monkeypatch.setattr(
        agent_runner_mod, "create_video_service", lambda s: FakeVideoService()
    )

    _redis_mock = AsyncMock()
    monkeypatch.setattr(
        "app.orchestration.redis.get_redis",
        AsyncMock(return_value=_redis_mock),
    )

    def _immediate_add(
        self: Any, func: Any, *args: Any, **kwargs: Any
    ) -> None:
        if asyncio.iscoroutinefunction(func):
            asyncio.ensure_future(func(*args, **kwargs))
        else:
            asyncio.get_running_loop().run_in_executor(None, func, *args, **kwargs)

    monkeypatch.setattr(
        generation_routes.BackgroundTasks, "add_task", _immediate_add
    )

    # Stub ComposeAgent.run_add_audio — fake videos don't exist as local files
    import app.agents.compose as compose_mod

    async def _stub_add_audio(self: Any, ctx: Any) -> None:
        await self.send_message(ctx, "音频已合成完毕（E2E stub - 跳过 FFmpeg）", progress=1.0)
        ctx.completion_info = type(
            "obj",
            (object,),
            {"completed": "音频已合成", "details": "", "next": "", "question": ""},
        )()

    monkeypatch.setattr(compose_mod.ComposeAgent, "run_add_audio", _stub_add_audio)

    # Patch local 'from X import Y' binding for async_session_maker in
    # generation.py — the conftest patches the module-level attribute but
    # generation.py imported it with 'from app.db.session import async_session_maker'.
    _, session_maker = test_db_engine_sessionmaker
    monkeypatch.setattr(generation_routes, "async_session_maker", session_maker)

    # Ensure agent_trace table exists — conftest's create_all ran before
    # our test module loaded the AgentTrace model, so the table is missing.
    engine, _ = test_db_engine_sessionmaker
    db_url = str(engine.url).replace("sqlite+aiosqlite:///", "")
    with sqlite3.connect(db_url) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS agent_trace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES agentrun(id),
                agent_name TEXT NOT NULL,
                stage TEXT NOT NULL,
                method TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                llm_calls INTEGER DEFAULT 0,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                images_generated INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error TEXT
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_agent_trace_run_id ON agent_trace(run_id)"
        )


async def _wait_for_run(session_maker: Any, run_id: int, timeout: int = 60) -> str:
    """Poll DB until run completes. Returns final status."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        async with session_maker() as session:
            run = await session.get(AgentRun, run_id)
            if run and run.status in ("succeeded", "failed", "cancelled"):
                return run.status
        await asyncio.sleep(1)
    raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")


async def _create_project(async_client: Any) -> dict:
    """Create a test project via API."""
    resp = await async_client.post(
        "/api/v1/projects",
        json={"title": "E2E AgentTrace Test", "story": "A test story", "style": "anime"},
    )
    assert resp.status_code == 201, f"Project creation failed: {resp.text}"
    return resp.json()


async def _trigger_generate(async_client: Any, project_id: int) -> dict:
    """Trigger generation with auto_mode=True."""
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={"auto_mode": True},
    )
    assert resp.status_code == 201, f"Generate trigger failed: {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_trace_entries_written(
    async_client: Any,
    test_session: Any,
    test_settings: Any,
    test_db_engine_sessionmaker: Any,
    e2e_stub_services: Any,
) -> None:
    """E2E-AT-01: Verify >=6 agent_trace entries after full pipeline run."""
    project = await _create_project(async_client)
    run = await _trigger_generate(async_client, project["id"])

    _, session_maker = test_db_engine_sessionmaker
    status = await _wait_for_run(session_maker, run["id"])
    assert status == "succeeded", f"Run ended with status {status}"

    async with session_maker() as session:
        result = await session.execute(
            select(AgentTrace).where(AgentTrace.run_id == run["id"])
        )
        traces = list(result.scalars().all())

    assert len(traces) >= 6, (
        f"Expected >= 6 agent_trace entries, got {len(traces)}"
    )


@pytest.mark.asyncio
async def test_trace_fields_populated(
    async_client: Any,
    test_session: Any,
    test_settings: Any,
    test_db_engine_sessionmaker: Any,
    e2e_stub_services: Any,
) -> None:
    """E2E-AT-02: Verify all trace fields are populated and successful."""
    project = await _create_project(async_client)
    run = await _trigger_generate(async_client, project["id"])

    _, session_maker = test_db_engine_sessionmaker
    status = await _wait_for_run(session_maker, run["id"])
    assert status == "succeeded"

    async with session_maker() as session:
        result = await session.execute(
            select(AgentTrace).where(AgentTrace.run_id == run["id"])
        )
        traces = list(result.scalars().all())

    assert len(traces) >= 6

    for t in traces:
        assert t.agent_name, f"agent_name is empty for trace {t.id}"
        assert t.stage, f"stage is empty for trace {t.id}"
        assert t.method, f"method is empty for trace {t.id}"
        assert t.start_time is not None, f"start_time is None for trace {t.id}"
        assert t.end_time is not None, f"end_time is None for trace {t.id}"
        assert t.start_time <= t.end_time, (
            f"start_time {t.start_time} > end_time {t.end_time} for trace {t.id}"
        )
        assert t.llm_calls >= 0, f"llm_calls negative for trace {t.id}"
        assert t.status == "completed", (
                f"trace {t.id} status is '{t.status}' not 'completed'"
            )


@pytest.mark.asyncio
async def test_trace_chain_order(
    async_client: Any,
    test_session: Any,
    test_settings: Any,
    test_db_engine_sessionmaker: Any,
    e2e_stub_services: Any,
) -> None:
    """E2E-AT-03: Verify traces form a monotonic time sequence with correct stage order."""
    # Standard production stage order
    stage_order = [
        "plan_outline",
        "plan_characters",
        "plan_shots",
        "render_characters",
        "render_shots",
        "compose_videos",
        "compose_merge",
        "add_audio",
    ]

    project = await _create_project(async_client)
    run = await _trigger_generate(async_client, project["id"])

    _, session_maker = test_db_engine_sessionmaker
    status = await _wait_for_run(session_maker, run["id"])
    assert status == "succeeded"

    async with session_maker() as session:
        result = await session.execute(
            select(AgentTrace)
            .where(AgentTrace.run_id == run["id"])
            .order_by(AgentTrace.start_time)
        )
        traces = list(result.scalars().all())

    assert len(traces) >= 6

    # Verify start_time is monotonic (non-decreasing)
    for i in range(1, len(traces)):
        assert traces[i].start_time >= traces[i - 1].start_time, (
            f"Trace {i} start_time {traces[i].start_time} < "
            f"trace {i - 1} start_time {traces[i - 1].start_time}"
        )

    # Verify agent_name sequence follows pipeline stage order
    seen_stages = [t.stage for t in traces if t.stage in stage_order]
    filtered_stages = [s for s in stage_order if s in seen_stages]
    assert seen_stages == filtered_stages[: len(seen_stages)], (
        f"Stage order mismatch. Expected prefix of {filtered_stages}, got {seen_stages}"
    )

"""Shared fixtures and helpers for E2E tests."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.agents import orchestrator as orchestrator_mod
from app.api.v1.routes import generation as generation_routes
from app.models.agent_run import AgentRun
from app.services import agent_runner as agent_runner_mod
from app.services.fake_text import FakeTextService
from app.services.provider_resolution import resolve_project_provider_settings
from tests.agent_fixtures import FakeImageService, FakeVideoService


@pytest.fixture(autouse=True)
def _e2e_autostub(monkeypatch: Any, e2e_stub_services: Any) -> None:
    """Stub provider resolution, factory local bindings, Redis, BG tasks, audio.

    This fixture autowires all necessary stubs for every E2E test.
    """

    async def _fake_resolver(project: Any, settings: Any, **kwargs: Any) -> Any:
        return resolve_project_provider_settings(project, settings)

    monkeypatch.setattr(
        generation_routes, "resolve_project_provider_settings_async", _fake_resolver
    )

    # Stub local 'from X import Y' bindings for factory functions
    monkeypatch.setattr(
        orchestrator_mod, "create_text_service", lambda s: FakeTextService(s)
    )
    monkeypatch.setattr(
        agent_runner_mod, "create_text_service", lambda s: FakeTextService(s)
    )
    monkeypatch.setattr(
        orchestrator_mod, "create_image_service", lambda s: FakeImageService()
    )
    monkeypatch.setattr(
        agent_runner_mod, "create_image_service", lambda s: FakeImageService()
    )
    monkeypatch.setattr(
        orchestrator_mod, "create_video_service", lambda s: FakeVideoService()
    )
    monkeypatch.setattr(
        agent_runner_mod, "create_video_service", lambda s: FakeVideoService()
    )

    # Redis mock (awaitable instance)
    _redis_mock = AsyncMock()
    monkeypatch.setattr(
        "app.orchestration.redis.get_redis",
        AsyncMock(return_value=_redis_mock),
    )

    # BackgroundTasks: execute immediately instead of deferring
    def _immediate_add(self: Any, func: Any, *args: Any, **kwargs: Any) -> None:
        if asyncio.iscoroutinefunction(func):
            asyncio.ensure_future(func(*args, **kwargs))
        else:
            asyncio.get_running_loop().run_in_executor(None, func, *args, **kwargs)

    monkeypatch.setattr(
        generation_routes.BackgroundTasks, "add_task", _immediate_add
    )

    # Stub audio (FFmpeg fails on fake video URLs)
    import app.agents.compose as compose_mod

    async def _stub_add_audio(self: Any, ctx: Any) -> None:
        await self.send_message(
            ctx, "音频已合成完毕（E2E stub - 跳过 FFmpeg）", progress=1.0
        )
        ctx.completion_info = type(
            "obj",
            (object,),
            {"completed": "音频已合成", "details": "", "next": "", "question": ""},
        )()

    monkeypatch.setattr(compose_mod.ComposeAgent, "run_add_audio", _stub_add_audio)


async def wait_for_run(session_maker: Any, run_id: int, timeout: int = 60) -> str:
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


async def create_project(async_client: Any) -> dict:
    """Create a test project via API."""
    resp = await async_client.post(
        "/api/v1/projects",
        json={"title": "E2E Test", "story": "A test story", "style": "anime"},
    )
    assert resp.status_code == 201, f"Project creation failed: {resp.text}"
    return resp.json()


async def trigger_generate(async_client: Any, project_id: int) -> dict:
    """Trigger generation with auto_mode=True."""
    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={"auto_mode": True},
    )
    assert resp.status_code == 201, f"Generate trigger failed: {resp.text}"
    return resp.json()

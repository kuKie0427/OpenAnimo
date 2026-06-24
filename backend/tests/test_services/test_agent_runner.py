from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent_run import AgentRun
from app.models.project import Project
from app.services.agent_runner import run_agent_plan


class _FakeWs:
    def __init__(self):
        self.events: list[tuple[int, dict]] = []

    async def send_event(self, project_id: int, event: dict):
        self.events.append((project_id, event))


class _FakeAgent:
    def __init__(self, name: str = "test_agent"):
        self.name = name

    async def run(self, ctx):
        pass


@pytest.fixture
def fake_ws():
    return _FakeWs()


@pytest.fixture
def fake_settings():
    s = MagicMock()
    s.text_provider = "openai"
    s.image_provider = "openai"
    s.video_provider = "openai"
    return s


@pytest.mark.asyncio
async def test_run_agent_plan_empty_plan(fake_ws, fake_settings):
    run = AgentRun(project_id=1, id=10)
    run.id = 10
    project = Project(id=1, title="t")

    with (
        patch("app.services.agent_runner.async_session_maker") as mock_sm,
        patch("app.services.agent_runner.create_text_service", return_value=MagicMock()),
        patch("app.services.agent_runner.create_image_service", return_value=MagicMock()),
        patch("app.services.agent_runner.create_video_service", return_value=MagicMock()),
        patch("app.services.agent_runner.task_manager"),
    ):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=[project, run])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_sm.return_value = mock_session

        await run_agent_plan(
            project_id=1,
            run_id=10,
            agent_plan=[],
            settings=fake_settings,
            ws=fake_ws,
        )

    assert run.status == "succeeded"
    assert run.progress == 1.0
    assert any(e[1].get("type") == "run_completed" for e in fake_ws.events)


@pytest.mark.asyncio
async def test_run_agent_plan_cancelled(fake_ws, fake_settings):
    run = AgentRun(project_id=1, id=10)
    run.id = 10

    class _CancelAgent:
        name = "cancel_agent"

        async def run(self, ctx):
            raise asyncio.CancelledError()

    with (
        patch("app.services.agent_runner.async_session_maker") as mock_sm,
        patch("app.services.agent_runner.create_text_service", return_value=MagicMock()),
        patch("app.services.agent_runner.create_image_service", return_value=MagicMock()),
        patch("app.services.agent_runner.create_video_service", return_value=MagicMock()),
        patch("app.services.agent_runner.task_manager"),
    ):
        cancel_session = AsyncMock()
        cancel_run = AgentRun(project_id=1, id=10)
        cancel_run.id = 10
        cancel_run.status = "running"
        cancel_session.get = AsyncMock(return_value=cancel_run)
        cancel_session.commit = AsyncMock()
        cancel_session.add = MagicMock()
        cancel_session.__aenter__ = AsyncMock(return_value=cancel_session)
        cancel_session.__aexit__ = AsyncMock(return_value=False)
        mock_sm.return_value = cancel_session

        with pytest.raises(asyncio.CancelledError):
            await run_agent_plan(
                project_id=1,
                run_id=10,
                agent_plan=[_CancelAgent()],
                settings=fake_settings,
                ws=fake_ws,
            )

    assert cancel_run.status == "cancelled"
    assert any(e[1].get("type") == "run_cancelled" for e in fake_ws.events)


@pytest.mark.asyncio
async def test_run_agent_plan_failure(fake_ws, fake_settings):
    run = AgentRun(project_id=1, id=10)
    run.id = 10
    project = Project(id=1, title="t")

    class _FailAgent:
        name = "fail_agent"

        async def run(self, ctx):
            raise RuntimeError("boom")

    with (
        patch("app.services.agent_runner.async_session_maker") as mock_sm,
        patch("app.services.agent_runner.create_text_service", return_value=MagicMock()),
        patch("app.services.agent_runner.create_image_service", return_value=MagicMock()),
        patch("app.services.agent_runner.create_video_service", return_value=MagicMock()),
        patch("app.services.agent_runner.task_manager"),
    ):
        fail_session = AsyncMock()
        fail_run = AgentRun(project_id=1, id=10)
        fail_run.id = 10
        fail_run.status = "running"
        fail_session.get = AsyncMock(side_effect=[project, run, fail_run])
        fail_session.commit = AsyncMock()
        fail_session.add = MagicMock()
        fail_session.__aenter__ = AsyncMock(return_value=fail_session)
        fail_session.__aexit__ = AsyncMock(return_value=False)
        mock_sm.return_value = fail_session

        await run_agent_plan(
            project_id=1,
            run_id=10,
            agent_plan=[_FailAgent()],
            settings=fake_settings,
            ws=fake_ws,
        )

    assert fail_run.status == "failed"
    assert fail_run.error == "boom"
    assert any(e[1].get("type") == "run_failed" for e in fake_ws.events)

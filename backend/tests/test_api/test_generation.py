from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.api.deps import get_app_settings, get_db_session, get_ws_manager
from app.agents.review_rules import ReviewRuleEngine
from app.api.v1.routes import generation as generation_routes
from app.main import create_app
from app.models.agent_run import AgentRun
from app.schemas.project import ProjectProviderEntry
from tests.factories import create_project, create_run


def _provider_resolution_deterministic() -> generation_routes.ProviderResolution:
    return generation_routes.ProviderResolution(
        valid=True,
        text=ProjectProviderEntry(
            selected_key="anthropic",
            source="default",
            resolved_key="anthropic",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
        image=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key="openai",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
        video=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key="openai",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
    )


def _immediate_task(coro):
    """Helper to make asyncio.create_task synchronous for testing"""
    loop = asyncio.get_running_loop()
    inner = None
    frame = getattr(coro, "cr_frame", None)
    if frame is not None:
        inner = frame.f_locals.get("coro")
    coro.close()
    if inner is not None:
        inner.close()
    future = loop.create_future()
    future.set_result(None)
    return future


async def _noop_task() -> None:
    return None


async def _return_resolution(_project, _settings, resolution):
    return resolution


def _invalid_provider_resolution() -> generation_routes.ProviderResolution:
    return generation_routes.ProviderResolution(
        valid=False,
        text=ProjectProviderEntry(
            selected_key="openai",
            source="project",
            resolved_key=None,
            valid=False,
            reason_code="provider_missing_credentials",
            reason_message="缺少 OpenAI 文本凭据",
        ),
        image=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key="openai",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
        video=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key="openai",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
    )


def _video_only_invalid_provider_resolution() -> generation_routes.ProviderResolution:
    return generation_routes.ProviderResolution(
        valid=False,
        text=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key="openai",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
        image=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key="openai",
            valid=True,
            reason_code=None,
            reason_message=None,
        ),
        video=ProjectProviderEntry(
            selected_key="openai",
            source="default",
            resolved_key=None,
            valid=False,
            reason_code="provider_missing_credentials",
            reason_message="缺少 OpenAI 视频凭据",
        ),
    )


@pytest.mark.asyncio
async def test_generate_project_not_found(async_client):
    res = await async_client.post("/api/v1/projects/99999/generate", json={})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_start_project_task_registers_created_task(monkeypatch):
    created_coroutines: list[object] = []
    registered_tasks: list[tuple[int, object]] = []

    class DummyTask:
        def add_done_callback(self, callback):
            self.callback = callback

    dummy_task = DummyTask()

    monkeypatch.setattr(
        generation_routes.asyncio,
        "create_task",
        lambda coro: created_coroutines.append(coro) or dummy_task,
    )
    monkeypatch.setattr(
        generation_routes.task_manager,
        "register",
        lambda project_id, task: registered_tasks.append((project_id, task)),
    )

    async def worker() -> None:
        return None

    await generation_routes._start_project_task(42, worker())

    assert len(created_coroutines) == 1
    assert registered_tasks == [(42, dummy_task)]
    created_coroutines[0].close()


@pytest.mark.asyncio
async def test_generate_project_success(async_client, test_session, monkeypatch):
    expected_snapshot = (
        _provider_resolution_deterministic().as_project_provider_settings().model_dump(mode="json")
    )
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(
            project,
            settings,
            _provider_resolution_deterministic(),
        ),
    )

    project = await create_project(test_session)
    res = await async_client.post(f"/api/v1/projects/{project.id}/generate", json={})
    assert res.status_code == 201
    data = res.json()
    run = await test_session.get(AgentRun, data["id"])
    assert run is not None
    assert run.status == "running"
    assert data["provider_snapshot"] == expected_snapshot
    assert run.provider_snapshot == expected_snapshot


@pytest.mark.asyncio
async def test_generate_project_returns_provider_precheck_failed_without_creating_run(
    async_client, test_session, monkeypatch
):
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(
            project, settings, _invalid_provider_resolution()
        ),
    )

    project = await create_project(test_session)
    before = (await test_session.execute(select(AgentRun))).scalars().all()

    res = await async_client.post(f"/api/v1/projects/{project.id}/generate", json={})

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "PROVIDER_PRECHECK_FAILED"
    assert data["error"]["details"]["provider_resolution"]["modalities"]["text"]["reason_code"] == (
        "provider_missing_credentials"
    )
    after = (await test_session.execute(select(AgentRun))).scalars().all()
    assert len(after) == len(before)


@pytest.mark.asyncio
async def test_generate_project_allows_start_when_only_video_provider_is_invalid(
    async_client, test_session, monkeypatch
):
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(
            project, settings, _video_only_invalid_provider_resolution()
        ),
    )

    project = await create_project(test_session)

    res = await async_client.post(f"/api/v1/projects/{project.id}/generate", json={})

    assert res.status_code == 201
    data = res.json()
    run = await test_session.get(AgentRun, data["id"])
    assert run is not None
    assert run.status == "running"


@pytest.mark.asyncio
async def test_generate_project_does_not_require_admin_token(
    test_session, test_settings, ws_manager, monkeypatch
):
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(
            project,
            settings,
            generation_routes.ProviderResolution(
                valid=True,
                text=ProjectProviderEntry(
                    selected_key="anthropic",
                    source="default",
                    resolved_key="anthropic",
                    valid=True,
                    reason_code=None,
                    reason_message=None,
                ),
                image=ProjectProviderEntry(
                    selected_key="openai",
                    source="default",
                    resolved_key="openai",
                    valid=True,
                    reason_code=None,
                    reason_message=None,
                ),
                video=ProjectProviderEntry(
                    selected_key="openai",
                    source="default",
                    resolved_key="openai",
                    valid=True,
                    reason_code=None,
                    reason_message=None,
                ),
            ),
        ),
    )

    app = create_app()

    async def override_get_session():
        yield test_session

    async def override_get_settings():
        return test_settings

    async def override_get_ws():
        return ws_manager

    app.dependency_overrides[get_db_session] = override_get_session
    app.dependency_overrides[get_app_settings] = override_get_settings
    app.dependency_overrides[get_ws_manager] = override_get_ws

    project = await create_project(test_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(f"/api/v1/projects/{project.id}/generate", json={})

    assert res.status_code == 201


@pytest.mark.asyncio
async def test_cancel_project_run_no_active(async_client, test_session):
    project = await create_project(test_session)
    res = await async_client.post(f"/api/v1/projects/{project.id}/cancel")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "no_active_run"


@pytest.mark.asyncio
async def test_cancel_project_run_updates(async_client, test_session):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id, status="running")

    res = await async_client.post(f"/api/v1/projects/{project.id}/cancel")
    assert res.status_code == 200
    await test_session.refresh(run)
    assert run.status == "cancelled"


@pytest.mark.asyncio
async def test_feedback_project_success(async_client, test_session, monkeypatch):
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(
            project,
            settings,
            _provider_resolution_deterministic(),
        ),
    )

    project = await create_project(test_session)
    res = await async_client.post(
        f"/api/v1/projects/{project.id}/feedback",
        json={"content": "Please adjust tone"},
    )
    assert res.status_code == 202
    data = res.json()
    run = await test_session.get(AgentRun, data["run_id"])
    assert run is not None
    assert run.status == "queued"
    assert (
        run.provider_snapshot
        == _provider_resolution_deterministic()
        .as_project_provider_settings()
        .model_dump(mode="json")
    )

    from app.models.message import Message

    res = await test_session.execute(select(Message).where(Message.run_id == run.id))
    messages = res.scalars().all()
    assert len(messages) == 1
    assert messages[0].content == "Please adjust tone"


@pytest.mark.asyncio
async def test_feedback_project_returns_409_for_active_conflict(async_client, test_session):
    project = await create_project(test_session)
    await create_run(test_session, project_id=project.id, status="running")

    res = await async_client.post(
        f"/api/v1/projects/{project.id}/feedback",
        json={"content": "Please adjust tone"},
    )

    assert res.status_code == 409
    body = res.json()
    assert "run" in body or "state" in body or "kind" in body


@pytest.mark.asyncio
async def test_review_rule_engine_routes_shot_feedback_to_render(test_session, test_settings):
    from tests.agent_fixtures import FakeLLM, make_context

    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    ctx = await make_context(
        test_session,
        test_settings,
        project=project,
        run=run,
        llm=FakeLLM("{}"),
    )
    ctx.user_feedback = "请重新渲染这个镜头"
    ctx.feedback_type = "shot"

    engine = ReviewRuleEngine()
    routing = await engine.run(ctx)

    assert routing["start_agent"] == "render"
    assert routing["mode"] == "incremental"


@pytest.mark.asyncio
async def test_resume_run_mismatched_project_id(async_client, test_session):
    """Resume a run that belongs to a different project → 404."""
    project = await create_project(test_session)
    other_project = await create_project(test_session)
    run = await create_run(test_session, project_id=other_project.id, status="failed")

    res = await async_client.post(
        f"/api/v1/projects/{project.id}/resume",
        json={"run_id": run.id},
    )
    assert res.status_code == 404
    assert "Run not found" in res.json()["detail"]

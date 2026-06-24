from __future__ import annotations

import asyncio

import pytest

from app.api.v1.routes import generation as generation_routes
from app.schemas.project import (
    AgentRunRead,
    ProjectProviderEntry,
    ProviderResolution,
    RecoveryControlRead,
    RecoveryStageRead,
    RecoverySummaryRead,
)
from tests.factories import create_project, create_run


def _immediate_task(coro):
    """Helper to make asyncio.create_task synchronous for testing"""
    loop = asyncio.get_running_loop()
    coro.close()
    future = loop.create_future()
    future.set_result(None)
    return future


def _recovery_control(run, *, state: str, detail: str):
    summary = RecoverySummaryRead(
        project_id=run.project_id,
        run_id=run.id,
        thread_id=f"agent-run-{run.id}",
        current_stage="script",
        next_stage="character",
        preserved_stages=["ideate"],
        stage_history=[
            RecoveryStageRead(name="ideate", status="completed", artifact_count=2),
            RecoveryStageRead(name="script", status="current", artifact_count=1),
            RecoveryStageRead(name="character", status="pending", artifact_count=0),
        ],
        resumable=True,
    )
    return RecoveryControlRead(
        state=state,
        detail=detail,
        thread_id=f"agent-run-{run.id}",
        active_run=AgentRunRead.model_validate(run),
        recovery_summary=summary,
    )


def _invalid_provider_resolution() -> ProviderResolution:
    return ProviderResolution(
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


async def _return_resolution(_project, _settings, resolution: ProviderResolution) -> ProviderResolution:
    return resolution


@pytest.mark.asyncio
async def test_generate_project_rejects_second_active_full_run(
    async_client, test_session, monkeypatch
):
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(project, settings, _invalid_provider_resolution()),
    )

    project = await create_project(test_session)
    active_run = await create_run(test_session, project_id=project.id, status="running")

    async def _fake_recovery_control(**kwargs):
        return _recovery_control(
            active_run,
            state="active",
            detail="Project already has an active run",
        )

    monkeypatch.setattr(generation_routes, "build_recovery_control_surface", _fake_recovery_control)

    res = await async_client.post(f"/api/v1/projects/{project.id}/generate", json={})

    assert res.status_code == 409
    data = res.json()
    assert data["state"] == "active"
    assert "active run" in data["detail"].lower()
    assert data["available_actions"] == ["resume", "cancel"]
    assert data["thread_id"] == f"agent-run-{active_run.id}"
    assert data["recovery_summary"]["current_stage"] == "script"
    assert data["recovery_summary"]["next_stage"] == "character"
    assert data["recovery_summary"]["stage_history"][0]["name"] == "ideate"


@pytest.mark.asyncio
async def test_generate_project_conflict_is_explicit_about_resume_or_cancel(
    async_client, test_session, monkeypatch
):
    monkeypatch.setattr(generation_routes.asyncio, "create_task", _immediate_task)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _return_resolution(project, settings, _invalid_provider_resolution()),
    )

    project = await create_project(test_session)
    resumable_run = await create_run(test_session, project_id=project.id, status="failed")

    async def _fake_recovery_control(**kwargs):
        return _recovery_control(
            resumable_run,
            state="recoverable",
            detail="Project has a resumable run",
        )

    monkeypatch.setattr(generation_routes, "build_recovery_control_surface", _fake_recovery_control)

    res = await async_client.post(f"/api/v1/projects/{project.id}/generate", json={})

    assert res.status_code == 409
    data = res.json()
    assert data["state"] == "recoverable"
    assert data["available_actions"] == ["resume", "cancel"]
    assert data["thread_id"] == f"agent-run-{resumable_run.id}"
    assert data["recovery_summary"]["preserved_stages"] == ["ideate"]


@pytest.mark.asyncio
async def test_resume_project_run_returns_existing_live_run(
    async_client, test_session, monkeypatch
):
    project = await create_project(test_session)
    active_run = await create_run(test_session, project_id=project.id, status="running")

    monkeypatch.setattr(generation_routes.task_manager, "is_running", lambda _project_id: True)

    def _fail_if_spawned(_coro):
        raise AssertionError("resume endpoint should not spawn a duplicate task")

    monkeypatch.setattr(generation_routes.asyncio, "create_task", _fail_if_spawned)

    res = await async_client.post(
        f"/api/v1/projects/{project.id}/resume", json={"run_id": active_run.id}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == active_run.id
    assert data["project_id"] == project.id


@pytest.mark.asyncio
async def test_resume_project_run_starts_resume_task_for_recoverable_run(
    async_client, test_session, monkeypatch
):
    project = await create_project(test_session)
    resumable_run = await create_run(test_session, project_id=project.id, status="failed")

    captured: dict[str, int] = {}

    async def _fake_resume(self, *, project_id: int, run_id: int, auto_mode: bool = False):
        captured["project_id"] = project_id
        captured["run_id"] = run_id

    monkeypatch.setattr(
        generation_routes.GenerationOrchestrator,
        "resume_from_recovery",
        _fake_resume,
    )

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(generation_routes.asyncio, "create_task", loop.create_task)

    res = await async_client.post(
        f"/api/v1/projects/{project.id}/resume", json={"run_id": resumable_run.id}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == resumable_run.id

    await asyncio.sleep(0)
    assert captured == {"project_id": project.id, "run_id": resumable_run.id}

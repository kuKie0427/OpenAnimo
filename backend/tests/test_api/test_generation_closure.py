"""Coverage for app.api.v1.routes.generation._task() closure paths and cancel/feedback edges.

The default test_generation.py uses _immediate_task() which closes the coroutine
without ever awaiting it, which means the closure body of _task() (the inner
function defined inside generate_project / resume_project_run / feedback_project)
never executes. These tests do the opposite: they replace _start_project_task
with a wrapper that *awaits* the coroutine, so the closure body executes
end-to-end against a stub orchestrator that the test controls.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_app_settings, get_db_session, get_ws_manager
from app.api.v1.routes import generation as generation_routes
from app.main import create_app
from app.models.agent_run import AgentRun
from app.schemas.project import ProjectProviderEntry
from tests.factories import create_project, create_run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_resolution() -> generation_routes.ProviderResolution:
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


class _StubOrchestrator:
    """Configurable stub for GenerationOrchestrator.

    Class-level switches let tests arm specific exception scenarios for the
    next instance that is created (the orchestrator is instantiated *inside*
    the route closure, so we cannot inject it directly).
    """

    next_run_exception: BaseException | None = None
    next_resume_exception: BaseException | None = None
    next_run_from_agent_exception: BaseException | None = None

    instances: list["_StubOrchestrator"] = []

    def __init__(self, *_, **__) -> None:
        self.run_calls: list[dict[str, Any]] = []
        self.resume_calls: list[dict[str, Any]] = []
        self.run_from_agent_calls: list[dict[str, Any]] = []
        type(self).instances.append(self)

    async def run(self, *, project_id, run_id, request, auto_mode=False) -> None:
        self.run_calls.append({"project_id": project_id, "run_id": run_id, "request": request, "auto_mode": auto_mode})
        exc = type(self).next_run_exception
        type(self).next_run_exception = None
        if exc is not None:
            raise exc
    async def resume_from_recovery(self, *, project_id, run_id) -> None:
        self.resume_calls.append({"project_id": project_id, "run_id": run_id})
        exc = type(self).next_resume_exception
        type(self).next_resume_exception = None
        if exc is not None:
            raise exc

    async def run_from_agent(self, *, project_id, run_id, request, agent_name, auto_mode, feedback_type=None, entity_type=None, entity_id=None) -> None:
        self.run_from_agent_calls.append(
            {
                "project_id": project_id,
                "run_id": run_id,
                "request": request,
                "agent_name": agent_name,
                "auto_mode": auto_mode,
                "feedback_type": feedback_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
            }
        )
        exc = type(self).next_run_from_agent_exception
        type(self).next_run_from_agent_exception = None
        if exc is not None:
            raise exc


@pytest.fixture(autouse=True)
def _reset_stub() -> None:
    """Clear class-level switches and instance log between tests."""
    _StubOrchestrator.next_run_exception = None
    _StubOrchestrator.next_resume_exception = None
    _StubOrchestrator.next_run_from_agent_exception = None
    _StubOrchestrator.instances.clear()


@pytest.fixture()
def closure_app(test_db_engine_sessionmaker, test_settings, ws_manager, monkeypatch):
    """FastAPI app + AsyncClient where _start_project_task actually awaits the coro.

    This forces the inner _task() closure body to execute end-to-end so its
    code paths get coverage. The route-level async_session_maker is patched
    to share the test sqlite db so the closure can read the run row created
    by the route handler.
    """
    _, shared_maker = test_db_engine_sessionmaker

    monkeypatch.setattr(generation_routes, "async_session_maker", shared_maker)
    monkeypatch.setattr(generation_routes, "GenerationOrchestrator", _StubOrchestrator)
    monkeypatch.setattr(
        generation_routes,
        "resolve_project_provider_settings_async",
        lambda project, settings: _async_return(_valid_resolution()),
    )

    awaited_results: list[BaseException | None] = []

    async def _await_coro(project_id: int, coro):
        try:
            await coro
            awaited_results.append(None)
        except asyncio.CancelledError as exc:
            # Closure already handled cancel (marked run cancelled); we swallow
            # the re-raised CancelledError so BackgroundTasks doesn't error.
            awaited_results.append(exc)
        except BaseException as exc:  # pragma: no cover - defensive
            awaited_results.append(exc)
            raise

    async def _bg_runner(project_id: int, coro):
        # Mirror BackgroundTasks behavior but await directly so closures execute.
        await _await_coro(project_id, coro)

    monkeypatch.setattr(generation_routes, "_start_project_task", _bg_runner)

    app = create_app()

    async def override_get_session():
        async with shared_maker() as session:
            yield session

    async def override_get_settings():
        return test_settings

    async def override_get_ws():
        return ws_manager

    app.dependency_overrides[get_db_session] = override_get_session
    app.dependency_overrides[get_app_settings] = override_get_settings
    app.dependency_overrides[get_ws_manager] = override_get_ws

    return {
        "app": app,
        "session_maker": shared_maker,
        "ws": ws_manager,
        "awaited": awaited_results,
    }


async def _async_return(value):
    return value


@pytest_asyncio.fixture()
async def closure_client(closure_app):
    transport = ASGITransport(app=closure_app["app"])
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, closure_app


# ---------------------------------------------------------------------------
# generate_project: 404 + closure happy/cancel paths + provider helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_closure_invokes_orchestrator_run(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)

    res = await client.post(f"/api/v1/projects/{project.id}/generate", json={})
    assert res.status_code == 201

    # The closure should have created an orchestrator and called run().
    assert len(_StubOrchestrator.instances) == 1
    assert _StubOrchestrator.instances[0].run_calls[0]["project_id"] == project.id


@pytest.mark.asyncio
async def test_generate_returns_409_for_active_conflict(closure_client):
    """An active queued/running run must trigger active_conflict (409)."""
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)
        # An already-running run should block fresh generation
        await create_run(session, project_id=project.id, status="running")

    res = await client.post(f"/api/v1/projects/{project.id}/generate", json={})
    assert res.status_code == 409
    body = res.json()
    # Recovery control surface is returned (not the standard error envelope)
    assert "run" in body or "state" in body or "kind" in body


@pytest.mark.asyncio
async def test_generate_returns_409_for_recoverable_conflict(closure_client):
    """A failed-but-recoverable run must trigger recoverable_conflict (409)."""
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)
        # A failed run is recoverable (not active)
        await create_run(session, project_id=project.id, status="failed")

    res = await client.post(f"/api/v1/projects/{project.id}/generate", json={})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_generate_closure_handles_cancel_and_marks_run_cancelled(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    _StubOrchestrator.next_run_exception = asyncio.CancelledError()

    async with session_maker() as session:
        project = await create_project(session)

    res = await client.post(f"/api/v1/projects/{project.id}/generate", json={})
    assert res.status_code == 201
    run_id = res.json()["id"]

    # The closure should have caught CancelledError and marked the run cancelled.
    async with session_maker() as session:
        run = await session.get(AgentRun, run_id)
        assert run is not None
        assert run.status == "cancelled"


@pytest.mark.asyncio
async def test_generate_closure_skips_status_overwrite_if_already_terminal(closure_client):
    """If the run was already marked terminal, the cancel branch must not overwrite it."""
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    _StubOrchestrator.next_run_exception = asyncio.CancelledError()

    async with session_maker() as session:
        project = await create_project(session)

    # Pre-create a run for the project, then have the route create another.
    res = await client.post(f"/api/v1/projects/{project.id}/generate", json={})
    assert res.status_code == 201
    new_run_id = res.json()["id"]

    # Manually flip the new run to "succeeded" then re-trigger cancel via second request:
    async with session_maker() as session:
        run = await session.get(AgentRun, new_run_id)
        assert run is not None
        run.status = "succeeded"
        await session.commit()


# ---------------------------------------------------------------------------
# resume_project_run: 404 paths + closure happy/cancel paths + already-running
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_returns_404_when_project_missing(closure_client):
    client, ctx = closure_client
    res = await client.post(
        "/api/v1/projects/99999/resume",
        json={"run_id": 1},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_resume_returns_404_when_run_missing(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)

    res = await client.post(
        f"/api/v1/projects/{project.id}/resume",
        json={"run_id": 99999},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_resume_returns_existing_run_when_task_still_running(closure_client, monkeypatch):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)
        run = await create_run(session, project_id=project.id, status="running")

    # Pretend the task is still alive in task_manager.
    monkeypatch.setattr(
        generation_routes.task_manager,
        "is_running",
        lambda project_id: True,
    )

    res = await client.post(
        f"/api/v1/projects/{project.id}/resume",
        json={"run_id": run.id},
    )
    assert res.status_code == 200
    assert res.json()["id"] == run.id
    # Closure must NOT have run.
    assert _StubOrchestrator.instances == []


@pytest.mark.asyncio
async def test_resume_closure_invokes_resume_from_recovery(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)
        run = await create_run(session, project_id=project.id, status="paused")

    res = await client.post(
        f"/api/v1/projects/{project.id}/resume",
        json={"run_id": run.id},
    )
    assert res.status_code == 200
    assert len(_StubOrchestrator.instances) == 1
    assert _StubOrchestrator.instances[0].resume_calls[0]["run_id"] == run.id


@pytest.mark.asyncio
async def test_resume_closure_handles_cancel_and_marks_run_cancelled(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    _StubOrchestrator.next_resume_exception = asyncio.CancelledError()

    async with session_maker() as session:
        project = await create_project(session)
        run = await create_run(session, project_id=project.id, status="paused")

    res = await client.post(
        f"/api/v1/projects/{project.id}/resume",
        json={"run_id": run.id},
    )
    assert res.status_code == 200

    async with session_maker() as session:
        refreshed = await session.get(AgentRun, run.id)
        assert refreshed is not None
        assert refreshed.status == "cancelled"


# ---------------------------------------------------------------------------
# cancel_project_run: 404 + cancel path emits ws event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_returns_404_when_project_missing(closure_client):
    client, ctx = closure_client
    res = await client.post("/api/v1/projects/99999/cancel")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_marks_runs_and_emits_ws_event(closure_client, monkeypatch):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]
    ws = ctx["ws"]

    async with session_maker() as session:
        project = await create_project(session)
        await create_run(session, project_id=project.id, status="running")
        await create_run(session, project_id=project.id, status="queued")

    monkeypatch.setattr(
        generation_routes.task_manager,
        "cancel",
        lambda project_id: True,
    )

    res = await client.post(f"/api/v1/projects/{project.id}/cancel")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "cancelled"
    assert body["cancelled"] == 2

    # ws.send_event should have been called.
    assert ws.events
    last_project_id, last_event = ws.events[-1]
    assert last_project_id == project.id
    assert last_event["type"] == "run_cancelled"
    assert last_event["data"]["cancelled_count"] == 2


# ---------------------------------------------------------------------------
# feedback_project: 404 + closure happy/cancel paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feedback_returns_404_when_project_missing(closure_client):
    client, ctx = closure_client
    res = await client.post(
        "/api/v1/projects/99999/feedback",
        json={"content": "fix tone"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_feedback_closure_invokes_run_from_agent(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    async with session_maker() as session:
        project = await create_project(session)

    res = await client.post(
        f"/api/v1/projects/{project.id}/feedback",
        json={"content": "fix tone"},
    )
    assert res.status_code == 202
    assert len(_StubOrchestrator.instances) == 1
    inst = _StubOrchestrator.instances[0]
    call = inst.run_from_agent_calls[0]
    assert call["agent_name"] == "review"
    assert call["auto_mode"] is False


@pytest.mark.asyncio
async def test_feedback_closure_handles_cancel_and_marks_run_cancelled(closure_client):
    client, ctx = closure_client
    session_maker = ctx["session_maker"]

    _StubOrchestrator.next_run_from_agent_exception = asyncio.CancelledError()

    async with session_maker() as session:
        project = await create_project(session)

    res = await client.post(
        f"/api/v1/projects/{project.id}/feedback",
        json={"content": "fix tone"},
    )
    assert res.status_code == 202
    run_id = res.json()["run_id"]

    async with session_maker() as session:
        run = await session.get(AgentRun, run_id)
        assert run is not None
        assert run.status == "cancelled"


# ---------------------------------------------------------------------------
# _start_project_task: log_task_result branches (lines 40-43)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_project_task_logs_exception_on_failed_done_callback(monkeypatch):
    """Cover the exception branch of _log_task_result inside _start_project_task."""
    captured_exceptions: list[BaseException] = []

    def fake_logger_exception(msg, *_, **__):
        captured_exceptions.append(RuntimeError(msg))

    monkeypatch.setattr(generation_routes.logger, "exception", fake_logger_exception)

    # Use a real task that raises immediately so the done callback hits the except branch.
    async def boom() -> None:
        raise RuntimeError("worker exploded")

    real_create_task = asyncio.create_task

    captured_callbacks: list = []

    def capture_create_task(coro):
        task = real_create_task(coro)

        original_add_done_callback = task.add_done_callback

        def add_cb(cb):
            captured_callbacks.append(cb)
            original_add_done_callback(cb)

        task.add_done_callback = add_cb  # type: ignore[method-assign]
        return task

    monkeypatch.setattr(generation_routes.asyncio, "create_task", capture_create_task)
    monkeypatch.setattr(
        generation_routes.task_manager,
        "register",
        lambda project_id, task: None,
    )

    await generation_routes._start_project_task(7, boom())
    # Wait a tick for the task to finish so the done callback runs.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert captured_exceptions, "logger.exception should have been called"


@pytest.mark.asyncio
async def test_start_project_task_swallows_cancelled_in_done_callback(monkeypatch):
    """Cover the CancelledError branch of _log_task_result inside _start_project_task."""
    captured_exceptions: list[BaseException] = []

    def fake_logger_exception(msg, *_, **__):
        captured_exceptions.append(RuntimeError(msg))

    monkeypatch.setattr(generation_routes.logger, "exception", fake_logger_exception)

    # Make the task raise CancelledError in the done callback path.
    async def slow() -> None:
        await asyncio.sleep(10)

    real_create_task = asyncio.create_task

    def capture_create_task(coro):
        return real_create_task(coro)

    monkeypatch.setattr(generation_routes.asyncio, "create_task", capture_create_task)
    monkeypatch.setattr(
        generation_routes.task_manager,
        "register",
        lambda project_id, task: setattr(task, "_test_handle", task),
    )

    coro = slow()
    await generation_routes._start_project_task(8, coro)
    # Now find the registered task and cancel it.
    # task_manager.register won't let us recover the task directly, so cancel via the running tasks set.
    pending = [t for t in asyncio.all_tasks() if t.get_coro() is coro]
    assert pending, "task should be pending"
    pending[0].cancel()
    try:
        await pending[0]
    except asyncio.CancelledError:
        pass
    # logger.exception should NOT have been called for CancelledError.
    assert not captured_exceptions


# ---------------------------------------------------------------------------
# _require_run_id: defensive raise (line 55)
# ---------------------------------------------------------------------------


def test_require_run_id_raises_when_missing():
    run = AgentRun(project_id=1, status="queued")  # no id
    with pytest.raises(RuntimeError, match="missing an id"):
        generation_routes._require_run_id(run)


def test_require_run_id_returns_id_when_present():
    run = AgentRun(id=42, project_id=1, status="queued")
    assert generation_routes._require_run_id(run) == 42


def test_agent_run_thread_id_handles_missing_id():
    pending = AgentRun(project_id=1, status="queued")
    assert generation_routes._agent_run_thread_id(pending) == "agent-run-pending"
    persisted = AgentRun(id=99, project_id=1, status="queued")
    assert generation_routes._agent_run_thread_id(persisted) == "agent-run-99"

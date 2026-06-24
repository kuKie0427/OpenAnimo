"""E2E tests for WebSocket event sequence via live backend."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from .conftest import create_project, wait_for_run

pytestmark = pytest.mark.e2e

pytest.skip("WS tests need synchronous TestClient refactoring — skip for now", allow_module_level=True)


@pytest.mark.asyncio
async def test_event_sequence_order(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
    app: Any,
) -> None:
    """E2E-WS-01: Verify WS event sequence follows expected order."""
    from tests.conftest import _no_lifespan

    app.router.lifespan_context = _no_lifespan
    client = TestClient(app)

    project = await create_project(async_client)
    project_id = project["id"]

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws:
        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/generate",
            json={"auto_mode": True},
        )
        assert resp.status_code == 201, f"Generate failed: {resp.text}"
        run = resp.json()

        _, session_maker = test_db_engine_sessionmaker
        _ = await wait_for_run(session_maker, run["id"])

        collected_types: list[str] = []
        try:
            while True:
                msg = ws.receive_json(timeout=2)
                event_type = msg.get("type", "")
                collected_types.append(event_type)
        except Exception:
            pass

    assert "run_started" in collected_types, "No run_started event received"
    assert "run_completed" in collected_types, "No run_completed event received"

    started_idx = collected_types.index("run_started")
    completed_idx = collected_types.index("run_completed")
    assert started_idx < completed_idx, (
        f"run_started ({started_idx}) not before run_completed ({completed_idx})"
    )


@pytest.mark.asyncio
async def test_event_data_integrity(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
    app: Any,
) -> None:
    """E2E-WS-02: Verify WS event data validates against WsEvent schema."""
    from app.schemas.ws import WsEvent
    from tests.conftest import _no_lifespan

    app.router.lifespan_context = _no_lifespan
    client = TestClient(app)

    project = await create_project(async_client)
    project_id = project["id"]

    with client.websocket_connect(f"/ws/projects/{project_id}") as ws:
        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/generate",
            json={"auto_mode": True},
        )
        assert resp.status_code == 201, f"Generate failed: {resp.text}"
        run = resp.json()

        _, session_maker = test_db_engine_sessionmaker
        _ = await wait_for_run(session_maker, run["id"])

        events: list[dict] = []
        try:
            while True:
                msg = ws.receive_json(timeout=2)
                events.append(msg)
        except Exception:
            pass

    sample = events[: min(3, len(events))]
    for event in sample:
        ws_event = WsEvent.model_validate(event)
        assert ws_event.type is not None
        assert ws_event.data is not None

    run_events = [e for e in events if "run_" in e.get("type", "")]
    run_ids = {
        e.get("data", {}).get("run_id")
        for e in run_events
        if e.get("data") and e["data"].get("run_id")
    }
    if run_ids:
        assert len(run_ids) == 1, f"Multiple run_ids in WS events: {run_ids}"

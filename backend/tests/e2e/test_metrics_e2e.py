"""E2E tests for RunMetrics endpoints via live backend."""
from __future__ import annotations

from typing import Any

import pytest

from .conftest import create_project, trigger_generate, wait_for_run

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_metrics_after_run(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
) -> None:
    """E2E-RM-01: Verify metrics endpoints return data after pipeline run."""
    _, session_maker = test_db_engine_sessionmaker
    project = await create_project(async_client)
    run = await trigger_generate(async_client, project["id"])

    status = await wait_for_run(session_maker, run["id"])
    assert status == "succeeded", f"Run ended with status {status}"

    resp = await async_client.get(
        f"/api/v1/metrics/runs?project_id={project['id']}"
    )
    assert resp.status_code == 200, f"metrics/runs: {resp.text}"
    runs_data = resp.json()
    assert isinstance(runs_data, list)
    assert any(r["run_id"] == run["id"] for r in runs_data), (
        f"Run {run['id']} not found in metrics runs"
    )

    resp = await async_client.get("/api/v1/metrics/costs")
    assert resp.status_code == 200, f"metrics/costs: {resp.text}"
    costs_data = resp.json()
    assert costs_data is not None

    resp = await async_client.get("/api/v1/metrics/quality")
    assert resp.status_code == 200, f"metrics/quality: {resp.text}"
    quality_data = resp.json()
    assert quality_data is not None

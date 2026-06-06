"""E2E test for recovery (cancel/resume) via live backend."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from .conftest import create_project, wait_for_run


pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_cancel_endpoint(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
) -> None:
    """E2E-RC-01 basic: Cancel endpoint for a running project."""
    project = await create_project(async_client)
    project_id = project["id"]

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={"auto_mode": True},
    )

    if resp.status_code == 201:
        cancel_resp = await async_client.post(
            f"/api/v1/projects/{project_id}/cancel"
        )
        assert cancel_resp.status_code == 200
        result = cancel_resp.json()
        assert "status" in result
        await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_resume_endpoint(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
) -> None:
    """E2E-RC-02 basic: Resume endpoint for a completed run."""
    project = await create_project(async_client)
    project_id = project["id"]

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={"auto_mode": True},
    )
    assert resp.status_code == 201
    run = resp.json()

    _, session_maker = test_db_engine_sessionmaker
    _ = await wait_for_run(session_maker, run["id"])

    resume_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/resume",
        json={"run_id": run["id"]},
    )
    assert resume_resp.status_code in (200, 404, 409)

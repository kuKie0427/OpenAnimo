"""E2E test for full chain output via live backend."""
from __future__ import annotations

from typing import Any

import pytest
from sqlmodel import select

from app.models.project import Character, Shot

from .conftest import create_project, trigger_generate, wait_for_run

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_full_chain_output(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
) -> None:
    """E2E-FL-01: Verify complete pipeline produces characters, shots, and export."""
    _, session_maker = test_db_engine_sessionmaker
    project = await create_project(async_client)
    run = await trigger_generate(async_client, project["id"])

    status = await wait_for_run(session_maker, run["id"])
    assert status == "succeeded"

    async with session_maker() as session:
        result = await session.execute(
            select(Character).where(Character.project_id == project["id"])
        )
        characters = list(result.scalars().all())
    assert len(characters) >= 1, f"Expected >= 1 characters, got {len(characters)}"

    async with session_maker() as session:
        result = await session.execute(
            select(Shot).where(Shot.project_id == project["id"])
        )
        shots = list(result.scalars().all())
    assert len(shots) >= 1, f"Expected >= 1 shots, got {len(shots)}"

    resp = await async_client.post(f"/api/v1/projects/{project['id']}/export/pdf")
    assert resp.status_code == 202, f"Export failed: {resp.text}"
    export_data = resp.json()
    assert export_data["status"] == "processing"
    assert export_data["format"] == "pdf"

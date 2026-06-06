"""E2E tests for parallel execution branches via live backend."""
from __future__ import annotations

from typing import Any

import pytest
from sqlmodel import select

from app.models.agent_trace import AgentTrace

from .conftest import create_project, trigger_generate, wait_for_run

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_branches_overlap(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
) -> None:
    """E2E-PL-01: Verify render_characters and render_shots_parallel overlap in time."""
    _, session_maker = test_db_engine_sessionmaker
    project = await create_project(async_client)
    run = await trigger_generate(async_client, project["id"])

    status = await wait_for_run(session_maker, run["id"])
    assert status == "succeeded"

    async with session_maker() as session:
        result = await session.execute(
            select(AgentTrace).where(AgentTrace.run_id == run["id"])
        )
        traces = list(result.scalars().all())

    char_traces = [
        t
        for t in traces
        if "render_character" in t.stage or "render_character" in t.method
    ]
    shot_traces = [
        t
        for t in traces
        if "render_shot" in t.stage or "render_shot" in t.method
    ]

    if char_traces and shot_traces:
        char_start = min(t.start_time for t in char_traces)
        char_end = char_traces[0].end_time
        shot_range = [(t.start_time, t.end_time) for t in shot_traces]

        has_overlap = any(
            s_start <= char_end and s_end >= char_start
            for s_start, s_end in shot_range
            if s_start and s_end
        )
        assert has_overlap, (
            "No temporal overlap between render_characters and render_shots"
        )


@pytest.mark.asyncio
async def test_convergence_before_compose(
    async_client: Any,
    test_db_engine_sessionmaker: Any,
) -> None:
    """E2E-PL-02: compose_videos starts after both render branches complete."""
    _, session_maker = test_db_engine_sessionmaker
    project = await create_project(async_client)
    run = await trigger_generate(async_client, project["id"])

    status = await wait_for_run(session_maker, run["id"])
    assert status == "succeeded"

    async with session_maker() as session:
        result = await session.execute(
            select(AgentTrace).where(AgentTrace.run_id == run["id"])
        )
        traces = list(result.scalars().all())

    compose_traces = [
        t for t in traces if "compose" in t.stage and "compose_video" in t.stage
    ]
    render_traces = [t for t in traces if "render" in t.stage]

    if compose_traces and render_traces:
        compose_start = min(t.start_time for t in compose_traces)
        render_ends = [t.end_time for t in render_traces if t.end_time]

        assert all(ce <= compose_start for ce in render_ends), (
            "compose_videos starts before all render branches completed"
        )

from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient

from app.models.agent_trace import AgentTrace
from tests.factories import create_project, create_run


@pytest.mark.asyncio
async def test_get_run_summaries(async_client: AsyncClient, test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)

    trace1 = AgentTrace(
        run_id=run.id,
        agent_name="planner",
        stage="planning",
        method="generate_plan",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        end_time=datetime(2025, 1, 1, 10, 0, 5),
        llm_calls=2,
        tokens_input=100,
        tokens_output=200,
        images_generated=0,
        status="completed",
    )
    trace2 = AgentTrace(
        run_id=run.id,
        agent_name="render",
        stage="rendering",
        method="render_shot",
        start_time=datetime(2025, 1, 1, 10, 0, 5),
        end_time=datetime(2025, 1, 1, 10, 0, 15),
        llm_calls=1,
        tokens_input=50,
        tokens_output=100,
        images_generated=3,
        status="completed",
    )
    test_session.add_all([trace1, trace2])
    await test_session.commit()

    res = await async_client.get("/api/v1/metrics/runs")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    summary = next(s for s in data if s["run_id"] == run.id)
    assert summary["agent_count"] == 2
    assert summary["total_llm_calls"] == 3
    assert summary["total_tokens"] == 450
    assert summary["total_images"] == 3
    assert summary["avg_duration_seconds"] is not None
    assert 4 <= summary["avg_duration_seconds"] <= 16
    assert summary["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_get_run_summaries_filter_by_project(
    async_client: AsyncClient, test_session, test_settings
):
    project_a = await create_project(test_session, title="Project A")
    project_b = await create_project(test_session, title="Project B")
    run_a = await create_run(test_session, project_id=project_a.id)
    run_b = await create_run(test_session, project_id=project_b.id)

    trace_a = AgentTrace(
        run_id=run_a.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        end_time=datetime(2025, 1, 1, 10, 0, 5),
        llm_calls=1,
        tokens_input=10,
        tokens_output=20,
        images_generated=0,
        status="completed",
    )
    trace_b = AgentTrace(
        run_id=run_b.id,
        agent_name="render",
        stage="rendering",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        end_time=datetime(2025, 1, 1, 10, 0, 10),
        llm_calls=5,
        tokens_input=100,
        tokens_output=200,
        images_generated=10,
        status="completed",
    )
    test_session.add_all([trace_a, trace_b])
    await test_session.commit()

    res = await async_client.get(f"/api/v1/metrics/runs?project_id={project_a.id}")
    assert res.status_code == 200
    data = res.json()
    run_ids = [s["run_id"] for s in data]
    assert run_a.id in run_ids
    assert run_b.id not in run_ids


@pytest.mark.asyncio
async def test_get_run_summaries_limit(async_client: AsyncClient, test_session, test_settings):
    project = await create_project(test_session)
    for _ in range(5):
        run = await create_run(test_session, project_id=project.id)
        trace = AgentTrace(
            run_id=run.id,
            agent_name="test",
            stage="test",
            method="test",
            start_time=datetime(2025, 1, 1, 10, 0, 0),
            end_time=datetime(2025, 1, 1, 10, 0, 1),
            llm_calls=0,
            tokens_input=0,
            tokens_output=0,
            images_generated=0,
            status="completed",
        )
        test_session.add(trace)
    await test_session.commit()

    res = await async_client.get("/api/v1/metrics/runs?limit=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data) <= 2


@pytest.mark.asyncio
async def test_get_cost_aggregates(async_client: AsyncClient, test_session, test_settings):
    project = await create_project(test_session)
    run1 = await create_run(test_session, project_id=project.id)
    run2 = await create_run(test_session, project_id=project.id)

    trace1 = AgentTrace(
        run_id=run1.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        tokens_input=100,
        tokens_output=200,
        images_generated=0,
        status="completed",
    )
    trace2 = AgentTrace(
        run_id=run2.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        tokens_input=50,
        tokens_output=100,
        images_generated=0,
        status="completed",
    )
    trace3 = AgentTrace(
        run_id=run1.id,
        agent_name="render",
        stage="rendering",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        tokens_input=10,
        tokens_output=20,
        images_generated=5,
        status="completed",
    )
    test_session.add_all([trace1, trace2, trace3])
    await test_session.commit()

    res = await async_client.get("/api/v1/metrics/costs")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

    planner = next(a for a in data if a["agent_name"] == "planner")
    assert planner["total_tokens_input"] == 150
    assert planner["total_tokens_output"] == 300
    assert planner["total_runs"] == 2

    renderer = next(a for a in data if a["agent_name"] == "render")
    assert renderer["total_tokens_input"] == 10
    assert renderer["total_images_generated"] == 5
    assert renderer["total_runs"] == 1


@pytest.mark.asyncio
async def test_get_cost_aggregates_filter_by_project(
    async_client: AsyncClient, test_session, test_settings
):
    project_a = await create_project(test_session, title="A")
    project_b = await create_project(test_session, title="B")
    run_a = await create_run(test_session, project_id=project_a.id)
    run_b = await create_run(test_session, project_id=project_b.id)

    trace_a = AgentTrace(
        run_id=run_a.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        tokens_input=10,
        tokens_output=20,
        status="completed",
    )
    trace_b = AgentTrace(
        run_id=run_b.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        tokens_input=999,
        tokens_output=999,
        status="completed",
    )
    test_session.add_all([trace_a, trace_b])
    await test_session.commit()

    res = await async_client.get(f"/api/v1/metrics/costs?project_id={project_a.id}")
    assert res.status_code == 200
    data = res.json()
    planner = next(a for a in data if a["agent_name"] == "planner")
    assert planner["total_tokens_input"] == 10


@pytest.mark.asyncio
async def test_get_quality_by_stage(async_client: AsyncClient, test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)

    trace1 = AgentTrace(
        run_id=run.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="completed",
    )
    trace2 = AgentTrace(
        run_id=run.id,
        agent_name="planner",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="failed",
        error="something went wrong",
    )
    trace3 = AgentTrace(
        run_id=run.id,
        agent_name="render",
        stage="rendering",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="completed",
    )
    trace4 = AgentTrace(
        run_id=run.id,
        agent_name="render",
        stage="rendering",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="running",
    )
    test_session.add_all([trace1, trace2, trace3, trace4])
    await test_session.commit()

    res = await async_client.get("/api/v1/metrics/quality")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

    planning = next(s for s in data if s["stage"] == "planning")
    assert planning["total_count"] == 2
    assert planning["completed_count"] == 1
    assert planning["failed_count"] == 1
    assert planning["running_count"] == 0
    assert planning["error_rate"] == 0.5

    rendering = next(s for s in data if s["stage"] == "rendering")
    assert rendering["total_count"] == 2
    assert rendering["completed_count"] == 1
    assert rendering["failed_count"] == 0
    assert rendering["running_count"] == 1
    assert rendering["error_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_quality_by_stage_filter_by_project(
    async_client: AsyncClient, test_session, test_settings
):
    project_a = await create_project(test_session, title="A")
    project_b = await create_project(test_session, title="B")
    run_a = await create_run(test_session, project_id=project_a.id)
    run_b = await create_run(test_session, project_id=project_b.id)

    trace_a = AgentTrace(
        run_id=run_a.id,
        agent_name="test",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="completed",
    )
    trace_b = AgentTrace(
        run_id=run_b.id,
        agent_name="test",
        stage="planning",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="failed",
    )
    test_session.add_all([trace_a, trace_b])
    await test_session.commit()

    res = await async_client.get(f"/api/v1/metrics/quality?project_id={project_a.id}")
    assert res.status_code == 200
    data = res.json()
    planning = next(s for s in data if s["stage"] == "planning")
    assert planning["total_count"] == 1
    assert planning["completed_count"] == 1
    assert planning["failed_count"] == 0


@pytest.mark.asyncio
async def test_metrics_empty_project(async_client: AsyncClient, test_session, test_settings):
    project = await create_project(test_session)

    res = await async_client.get(f"/api/v1/metrics/runs?project_id={project.id}")
    assert res.status_code == 200
    assert res.json() == []

    res = await async_client.get(f"/api/v1/metrics/costs?project_id={project.id}")
    assert res.status_code == 200
    assert res.json() == []

    res = await async_client.get(f"/api/v1/metrics/quality?project_id={project.id}")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_metrics_no_project_id_returns_all(
    async_client: AsyncClient, test_session, test_settings
):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    trace = AgentTrace(
        run_id=run.id,
        agent_name="test",
        stage="test",
        method="test",
        start_time=datetime(2025, 1, 1, 10, 0, 0),
        status="completed",
    )
    test_session.add(trace)
    await test_session.commit()

    for endpoint in ("/api/v1/metrics/runs", "/api/v1/metrics/costs", "/api/v1/metrics/quality"):
        res = await async_client.get(endpoint)
        assert res.status_code == 200
        assert len(res.json()) > 0

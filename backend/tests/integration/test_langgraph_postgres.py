from __future__ import annotations

import pytest
from sqlmodel import select

from app.models.project import Project
from app.models.run import Run
from app.models.stage import Stage
from app.orchestration.runtime import build_graph_config
from tests.factories import create_project


@pytest.mark.asyncio
async def test_langgraph_postgres_checkpoint_survives_new_session_boundary(checkpoint_sessionmaker):
    async with checkpoint_sessionmaker() as session_one:
        project = await create_project(session_one, title="Durable checkpoint project")
        run = Run(
            project_id=project.id,
            thread_id="thread-checkpoint-001",
            status="running",
            source="langgraph",
        )
        stage = Stage(
            project_id=project.id,
            run_id=1,
            name="storyboards",
            status="running",
            source="langgraph",
        )
        session_one.add(run)
        await session_one.commit()
        await session_one.refresh(run)

        stage.run_id = run.id
        session_one.add(stage)
        await session_one.commit()
        await session_one.refresh(stage)

        run_id = run.id
        stage_id = stage.id

    async with checkpoint_sessionmaker() as session_two:
        reloaded_run = await session_two.get(Run, run_id)
        assert reloaded_run is not None
        assert reloaded_run.thread_id == "thread-checkpoint-001"
        assert build_graph_config(reloaded_run) == {
            "configurable": {"thread_id": "thread-checkpoint-001"}
        }

        reloaded_stage = await session_two.get(Stage, stage_id)
        assert reloaded_stage is not None
        assert reloaded_stage.run_id == run_id
        assert reloaded_stage.source == "langgraph"

        res = await session_two.execute(
            select(Project).where(Project.id == reloaded_run.project_id)
        )
        assert res.scalar_one() is not None

        from app.orchestration.persistence import build_postgres_checkpointer

        assert callable(build_postgres_checkpointer)

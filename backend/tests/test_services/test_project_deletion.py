from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.agent_run import AgentMessage, AgentRun
from app.models.message import Message
from app.models.project import Character, Project, Shot
from app.services import project_deletion
from tests.factories import (
    create_agent_message,
    create_character,
    create_message,
    create_project,
    create_run,
    create_shot,
)


@pytest.mark.asyncio
async def test_delete_project_by_id_removes_related_rows_and_files(test_session, monkeypatch):
    project = await create_project(test_session)
    project.video_url = "/static/videos/project.mp4"
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)

    run = await create_run(test_session, project_id=project.id, status="running")
    await create_message(test_session, run_id=run.id, project_id=project.id)
    await create_agent_message(test_session, run_id=run.id)
    await create_character(test_session, project_id=project.id, image_url="/static/characters/hero.png")
    await create_shot(
        test_session,
        project_id=project.id,
        image_url="/static/shots/shot.png",
        video_url="/static/videos/shot.mp4",
    )

    deleted_single: list[str | None] = []
    deleted_batches: list[list[str | None]] = []

    monkeypatch.setattr(project_deletion, "delete_file", lambda url: deleted_single.append(url) or True)
    monkeypatch.setattr(
        project_deletion,
        "delete_files",
        lambda urls: deleted_batches.append(list(urls)) or len(urls),
    )

    await project_deletion.delete_project_by_id(test_session, project.id)

    assert deleted_single == ["/static/videos/project.mp4"]
    assert deleted_batches == [
        ["/static/characters/hero.png"],
        ["/static/shots/shot.png"],
        ["/static/videos/shot.mp4"],
    ]
    assert await test_session.get(Project, project.id) is None
    assert (await test_session.execute(select(Character))).scalars().all() == []
    assert (await test_session.execute(select(Shot))).scalars().all() == []
    assert (await test_session.execute(select(Message))).scalars().all() == []
    assert (await test_session.execute(select(AgentMessage))).scalars().all() == []
    assert (await test_session.execute(select(AgentRun))).scalars().all() == []


@pytest.mark.asyncio
async def test_delete_project_by_id_raises_404_when_project_missing(test_session):
    with pytest.raises(HTTPException) as exc_info:
        await project_deletion.delete_project_by_id(test_session, 99999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Project not found"


@pytest.mark.asyncio
async def test_delete_projects_by_ids_ignores_missing(test_session):
    project = await create_project(test_session)

    await project_deletion.delete_projects_by_ids(test_session, [project.id, 99999])

    assert await test_session.get(Project, project.id) is None

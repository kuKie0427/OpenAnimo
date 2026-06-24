from __future__ import annotations

import pytest

from app.services.approval_gate import can_enter_clip_generation, can_enter_final_merge
from app.agents.base import TargetIds
from tests.factories import create_project, create_run, create_shot


@pytest.mark.asyncio
async def test_can_enter_clip_generation_no_run_id(test_session, test_settings):
    from app.models.agent_run import AgentRun

    run = AgentRun(project_id=99999, stage="compose", status="running")
    result = await can_enter_clip_generation(test_session, run)
    assert result is False


@pytest.mark.asyncio
async def test_can_enter_clip_generation_all_shots_approved(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(test_session, project_id=project.id)
    shot.freeze_approval()
    await test_session.commit()

    result = await can_enter_clip_generation(test_session, run)
    assert result is True


@pytest.mark.asyncio
async def test_can_enter_clip_generation_shot_not_approved(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await create_shot(test_session, project_id=project.id)
    await test_session.commit()

    result = await can_enter_clip_generation(test_session, run)
    assert result is False


@pytest.mark.asyncio
async def test_can_enter_clip_generation_no_shots(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await test_session.commit()

    result = await can_enter_clip_generation(test_session, run)
    assert result is False


@pytest.mark.asyncio
async def test_can_enter_clip_generation_with_target_ids(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    shot1 = await create_shot(test_session, project_id=project.id)
    shot1.freeze_approval()
    await create_shot(test_session, project_id=project.id)
    await test_session.commit()

    target_ids = TargetIds(shot_ids=[shot1.id])
    result = await can_enter_clip_generation(test_session, run, target_ids=target_ids)
    assert result is True


@pytest.mark.asyncio
async def test_can_enter_clip_generation_target_ids_not_approved(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(test_session, project_id=project.id)
    await test_session.commit()

    target_ids = TargetIds(shot_ids=[shot.id])
    result = await can_enter_clip_generation(test_session, run, target_ids=target_ids)
    assert result is False


@pytest.mark.asyncio
async def test_can_enter_clip_generation_resource_type_shot(test_session, test_settings):
    project = await create_project(test_session)
    shot = await create_shot(test_session, project_id=project.id)
    shot.freeze_approval()
    run = await create_run(test_session, project_id=project.id)
    run.resource_type = "shot"
    run.resource_id = shot.id
    await test_session.commit()

    result = await can_enter_clip_generation(test_session, run)
    assert result is True


@pytest.mark.asyncio
async def test_can_enter_clip_generation_target_ids_not_found(test_session, test_settings):
    project = await create_project(test_session)
    run = await create_run(test_session, project_id=project.id)
    await test_session.commit()

    target_ids = TargetIds(shot_ids=[99999])
    result = await can_enter_clip_generation(test_session, run, target_ids=target_ids)
    assert result is False


@pytest.mark.asyncio
async def test_can_enter_final_merge_no_blocking(test_session, test_settings):
    project = await create_project(test_session)
    await create_shot(test_session, project_id=project.id, video_url="http://test/video.mp4")
    await test_session.commit()

    result = await can_enter_final_merge(test_session, project)
    assert result is True


@pytest.mark.asyncio
async def test_can_enter_final_merge_blocking_clips(test_session, test_settings):
    project = await create_project(test_session)
    await create_shot(test_session, project_id=project.id, video_url=None)
    await test_session.commit()

    result = await can_enter_final_merge(test_session, project)
    assert result is False

from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.agents.base import TargetIds
from app.agents.render import RenderAgent
from app.agents.compose import ComposeAgent
from app.api.deps import SessionDep, SettingsDep, WsManagerDep, get_or_404, require_run_id
from app.config import Settings
from app.models.agent_run import AgentRun
from app.models.project import Character, Project, Shot, ShotCharacterBinding
from app.schemas.project import AgentRunRead, RegenerateRequest, ShotRead, ShotUpdate
from app.services.agent_runner import run_agent_plan
from app.services.creative_control import (
    collect_project_blocking_clips,
    invalidate_shot_clip_output,
    invalidate_shot_storyboard_outputs,
)
from app.services.file_cleaner import delete_file
from app.services.task_manager import task_manager
from app.ws.manager import ConnectionManager

router = APIRouter()


def _require_run_id(run: AgentRun) -> int:
    return require_run_id(run)


def _shot_read(shot: Shot) -> dict[str, Any]:
    return ShotRead.model_validate(shot).model_dump(mode="json")


def _validate_shot_approval_ready(shot: Shot) -> None:
    missing = []
    if not shot.description:
        missing.append("description")
    if not shot.prompt:
        missing.append("prompt")
    if not shot.image_prompt:
        missing.append("image_prompt")
    if shot.duration is None:
        missing.append("duration")
    if not shot.camera:
        missing.append("camera")
    if not shot.motion_note:
        missing.append("motion_note")
    if not shot.character_ids:
        missing.append("character_ids")

    if missing:
        raise HTTPException(
            status_code=400,
            detail="Shot approval requires structured intent, duration, camera, motion note, and bound cast",
        )


async def _sync_shot_character_bindings(session: AsyncSession, shot: Shot) -> None:
    shot_id_col = cast(InstrumentedAttribute[int], cast(object, ShotCharacterBinding.shot_id))
    await session.execute(delete(ShotCharacterBinding).where(shot_id_col == shot.id))
    shot_id = shot.id
    if shot.character_ids:
        if shot_id is None:
            raise RuntimeError("Shot binding sync requires a persisted shot id")
        session.add_all(
            [
                ShotCharacterBinding(shot_id=shot_id, character_id=character_id)
                for character_id in shot.character_ids
            ]
        )


async def _validate_shot_character_ids(
    session: AsyncSession, project_id: int, character_ids: list[int]
) -> None:
    if not character_ids:
        return

    character_id_col = cast(InstrumentedAttribute[int | None], cast(object, Character.id))
    character_project_id_col = cast(InstrumentedAttribute[int], cast(object, Character.project_id))
    res = await session.execute(
        select(character_id_col).where(
            character_project_id_col == project_id,
            character_id_col.in_(character_ids),
        )
    )
    found_ids = {character_id for character_id in res.scalars().all() if character_id is not None}
    missing_ids = [character_id for character_id in character_ids if character_id not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown character_ids for project: {missing_ids}",
        )


@router.put("/{shot_id}", response_model=ShotRead)
@router.patch("/{shot_id}", response_model=ShotRead)
async def update_shot(
    shot_id: int,
    payload: ShotUpdate,
    session: AsyncSession = SessionDep,
    ws: ConnectionManager = WsManagerDep,
):
    shot = await get_or_404(session, Shot, shot_id)

    project_id = shot.project_id

    data = payload.model_dump(exclude_unset=True)
    character_ids_updated = False
    if "character_ids" in data:
        character_ids = list(
            dict.fromkeys(int(character_id) for character_id in data.pop("character_ids") or [])
        )
        await _validate_shot_character_ids(session, project_id, character_ids)
        shot.character_ids = character_ids
        character_ids_updated = True
    for k, v in data.items():
        setattr(shot, k, v)

    session.add(shot)
    if character_ids_updated:
        await _sync_shot_character_bindings(session, shot)
    await session.commit()
    await session.refresh(shot)

    await ws.send_event(
        project_id,
        {"type": "shot_updated", "data": {"shot": _shot_read(shot)}},
    )
    return _shot_read(shot)


@router.post("/{shot_id}/approve", response_model=ShotRead)
async def approve_shot(
    shot_id: int,
    session: AsyncSession = SessionDep,
    ws: ConnectionManager = WsManagerDep,
):
    shot = await get_or_404(session, Shot, shot_id)

    _validate_shot_approval_ready(shot)
    await _validate_shot_character_ids(session, shot.project_id, list(shot.character_ids))
    shot.freeze_approval()
    session.add(shot)
    await session.commit()
    await session.refresh(shot)

    payload = _shot_read(shot)
    await ws.send_event(
        shot.project_id,
        {"type": "shot_updated", "data": {"shot": payload}},
    )
    return payload


@router.post(
    "/{shot_id}/regenerate", response_model=AgentRunRead, status_code=status.HTTP_201_CREATED
)
async def regenerate_shot(
    shot_id: int,
    payload: RegenerateRequest | None = None,
    session: AsyncSession = SessionDep,
    settings: Settings = SettingsDep,
    ws: ConnectionManager = WsManagerDep,
):
    if payload is None:
        payload = RegenerateRequest(type="video")

    shot = await get_or_404(session, Shot, shot_id)
    project = await get_or_404(session, Project, shot.project_id)
    project_id = shot.project_id

    # 检查是否有针对该分镜的运行中任务（细粒度锁）
    project_id_col = cast(InstrumentedAttribute[int], cast(object, AgentRun.project_id))
    status_col = cast(InstrumentedAttribute[str], cast(object, AgentRun.status))
    resource_type_col = cast(
        InstrumentedAttribute[str | None], cast(object, AgentRun.resource_type)
    )
    resource_id_col = cast(InstrumentedAttribute[int | None], cast(object, AgentRun.resource_id))
    res = await session.execute(
        select(AgentRun)
        .where(project_id_col == project_id)
        .where(status_col.in_(("queued", "running")))
        .where(resource_type_col == "shot")
        .where(resource_id_col == shot_id)
        .limit(1)
    )
    if res.scalars().first() is not None:
        raise HTTPException(status_code=409, detail="This shot is already being regenerated")

    agent_plan: list[Any]
    target_ids = TargetIds(shot_ids=[shot_id])
    if payload.type == "image":
        await invalidate_shot_storyboard_outputs(session, project, shot)
        await session.commit()
        await session.refresh(shot)
        await session.refresh(project)
        blocking_clips = await collect_project_blocking_clips(session, project)

        await ws.send_event(
            project_id,
            {"type": "shot_updated", "data": {"shot": _shot_read(shot)}},
        )
        await ws.send_event(
            project_id,
            {
                "type": "project_updated",
                "data": {
                    "project": {
                        "id": project_id,
                        "video_url": project.video_url,
                        "status": project.status,
                        "blocking_clips": blocking_clips,
                    }
                },
            },
        )

        agent_plan = [RenderAgent()]
    else:
        await invalidate_shot_clip_output(session, project)
        await session.commit()
        await session.refresh(project)
        blocking_clips = await collect_project_blocking_clips(session, project)

        await ws.send_event(
            project_id,
            {
                "type": "project_updated",
                "data": {
                    "project": {
                        "id": project_id,
                        "video_url": project.video_url,
                        "status": project.status,
                        "blocking_clips": blocking_clips,
                    }
                },
            },
        )

        agent_plan = [ComposeAgent()]

    run = AgentRun(
        project_id=project_id,
        status="running",
        current_agent=getattr(agent_plan[0], "name", None) if agent_plan else None,
        progress=0.0,
        error=None,
        resource_type="shot",  # 设置资源类型
        resource_id=shot_id,  # 设置资源 ID
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    run_id = _require_run_id(run)

    task = asyncio.create_task(
        run_agent_plan(
            project_id=project_id,
            run_id=run_id,
            agent_plan=agent_plan,
            settings=settings,
            ws=ws,
            target_ids=target_ids,
        )
    )
    task_manager.register(project_id, task)
    return AgentRunRead.model_validate(run)


@router.delete("/{shot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shot(
    shot_id: int,
    session: AsyncSession = SessionDep,
    ws: ConnectionManager = WsManagerDep,
):
    shot = await get_or_404(session, Shot, shot_id)

    project_id = shot.project_id

    # 删除分镜相关文件
    delete_file(shot.image_url)
    delete_file(shot.video_url)

    # 删除项目最终视频（因为分镜变化了）
    project = await session.get(Project, project_id)
    cleared_project_video = False
    if project and project.video_url:
        delete_file(project.video_url)
        project.video_url = None
        session.add(project)
        cleared_project_video = True

    # 删除数据库记录
    await session.delete(shot)
    await session.commit()

    # 发送 WebSocket 事件
    await ws.send_event(project_id, {"type": "shot_deleted", "data": {"shot_id": shot_id}})
    if cleared_project_video:
        await ws.send_event(
            project_id,
            {"type": "project_updated", "data": {"project": {"id": project_id, "video_url": None}}},
        )

    return None

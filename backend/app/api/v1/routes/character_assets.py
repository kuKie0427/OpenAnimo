# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""CharacterAsset API — manage multi-angle character assets."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.api.deps import AdminDep, SessionDep, SettingsDep, WsManagerDep, get_or_404, require_run_id
from app.config import Settings
from app.models.agent_run import AgentRun
from app.models.project import Character
from app.services.character_asset_service import (
    generate_matrix,
    list_assets,
    get_matrix,
    delete_asset,
)
from app.services.task_manager import task_manager
from app.ws.manager import ConnectionManager

router = APIRouter()
logger = logging.getLogger(__name__)


def _asset_to_dict(asset: Any) -> dict[str, Any]:
    """Convert CharacterAsset to dict for JSON response."""
    return {
        "id": asset.id,
        "character_id": asset.character_id,
        "angle": asset.angle,
        "emotion": asset.emotion,
        "image_url": asset.image_url,
        "prompt": asset.prompt,
        "seed": asset.seed,
        "is_approved": asset.is_approved,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


async def _generate_assets_task(
    character_id: int,
    project_id: int,
    run_id: int,
    settings: Settings,
    ws: ConnectionManager,
) -> None:
    """Background task: generate 4×4 character assets matrix."""
    from app.db.session import async_session_maker
    from app.services.image_factory import create_image_service

    try:
        image_service = create_image_service(settings)

        async def generate_fn(prompt: str, seed: int | None) -> str:
            url = await image_service.generate_url(prompt=prompt, seed=seed)
            return await image_service.cache_external_image(url)

        async with async_session_maker() as task_session:
            character = await task_session.get(Character, character_id)
            if not character:
                raise ValueError(f"Character {character_id} not found")

            result = await generate_matrix(task_session, character, generate_fn)

        await ws.send_event(project_id, {
            "type": "asset_generation_completed",
            "data": {"character_id": character_id, **result},
        })

        async with async_session_maker() as task_session:
            run = await task_session.get(AgentRun, run_id)
            if run:
                run.status = "succeeded"
                run.progress = 1.0
                await task_session.commit()

        logger.info(
            "Asset generation succeeded for character %d: %d/%d",
            character_id,
            result["succeeded"],
            result["total"],
        )

    except Exception as e:
        logger.exception("Asset generation failed for character %d", character_id)

        try:
            await ws.send_event(project_id, {
                "type": "asset_generation_completed",
                "data": {"character_id": character_id, "error": str(e)},
            })
        except Exception:
            logger.warning("Failed to send WS error event for character %d", character_id)

        async with async_session_maker() as task_session:
            run = await task_session.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.error = str(e)[:500]
                await task_session.commit()


@router.post("/{character_id}/assets/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_character_assets(
    character_id: int,
    session: AsyncSession = SessionDep,
    settings: Settings = SettingsDep,
    ws: ConnectionManager = WsManagerDep,
    _: None = AdminDep,
) -> dict[str, Any]:
    """Trigger background generation of 4 angles × 4 emotions = 16 character assets."""
    character = await get_or_404(session, Character, character_id)
    project_id = character.project_id

    if not character.visual_notes and not character.description:
        raise HTTPException(
            status_code=400,
            detail="Character must have visual_notes or description for asset generation",
        )

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
        .where(resource_type_col == "character_asset")
        .where(resource_id_col == character_id)
        .limit(1)
    )
    if res.scalars().first() is not None:
        raise HTTPException(
            status_code=409, detail="Asset generation is already in progress for this character"
        )

    run = AgentRun(
        project_id=project_id,
        status="running",
        progress=0.0,
        resource_type="character_asset",
        resource_id=character_id,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    run_id = require_run_id(run)

    task = asyncio.create_task(
        _generate_assets_task(
            character_id=character_id,
            project_id=project_id,
            run_id=run_id,
            settings=settings,
            ws=ws,
        )
    )
    task_manager.register(project_id, task)

    return {"generation_id": run_id, "status": "started"}


@router.get("/{character_id}/assets")
async def get_character_assets(
    character_id: int,
    angle: str | None = Query(default=None, description="Filter by angle: front, side, back, three_quarter"),
    emotion: str | None = Query(default=None, description="Filter by emotion: smile, angry, crying, surprised"),
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
) -> list[dict[str, Any]]:
    """List all character assets, optionally filtered by angle/emotion."""
    await get_or_404(session, Character, character_id)
    assets = await list_assets(session, character_id, angle=angle, emotion=emotion)
    return [_asset_to_dict(a) for a in assets]


@router.get("/{character_id}/assets/matrix")
async def get_character_asset_matrix(
    character_id: int,
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
) -> dict[str, dict[str, dict]]:
    """Get the 4×4 asset matrix (angle × emotion)."""
    await get_or_404(session, Character, character_id)
    return await get_matrix(session, character_id)


@router.delete("/{character_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character_asset(
    character_id: int,
    asset_id: int,
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
) -> None:
    """Delete a single character asset by ID."""
    await get_or_404(session, Character, character_id)
    deleted = await delete_asset(session, asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return None

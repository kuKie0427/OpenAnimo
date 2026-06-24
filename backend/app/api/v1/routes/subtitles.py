# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""字幕烧入 API 路由"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.api.deps import AdminDep, SessionDep, get_or_404
from app.models.project import Project, Shot
from app.services.subtitle_service import build_srt, burn_subtitles_into_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/subtitles", tags=["subtitles"])


@router.post("/burn")
async def burn_subtitles(
    project_id: int,
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
):
    """手动触发字幕烧入"""
    # 1. Get project, verify video exists
    project = await get_or_404(session, Project, project_id)
    if not project.video_url:
        raise HTTPException(status_code=400, detail="Project has no final video yet")

    # 2. Get all shots with dialogue
    shot_project_id_col = cast(InstrumentedAttribute[int], cast(object, Shot.project_id))
    shot_order_col = cast(InstrumentedAttribute[int], cast(object, Shot.order))
    res = await session.execute(
        select(Shot)
        .where(shot_project_id_col == project_id)
        .order_by(shot_order_col.asc())
    )
    shots = list(res.scalars().all())

    # 3. Generate SRT
    srt_content = build_srt(shots, include_unapproved=False)

    if srt_content:
        # 4. Write SRT file to static/exports/
        exports_dir = Path("static/exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        srt_filename = f"{project_id}_api_{uuid.uuid4().hex[:8]}.srt"
        srt_path = exports_dir / srt_filename
        srt_path.write_text(srt_content, encoding="utf-8")

        # 5. Burn subtitles into video
        video_output_dir = Path("static/videos")
        video_output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"sub_{uuid.uuid4().hex[:8]}.mp4"
        output_path = str(video_output_dir / output_filename)

        await burn_subtitles_into_video(
            video_path=project.video_url,
            srt_path=str(srt_path),
            output_path=output_path,
        )

        # 6. Update project
        new_video_url = f"/static/videos/{output_filename}"
        project.video_url = new_video_url
        session.add(project)
        await session.commit()

        return {
            "srt_download_url": f"/static/exports/{srt_filename}",
            "video_url": new_video_url,
            "shot_count": len([s for s in shots if s.approved_dialogue or s.dialogue]),
        }
    else:
        return {
            "srt_download_url": None,
            "video_url": project.video_url,
            "shot_count": 0,
            "message": "No dialogue found in any shots, no subtitles generated",
        }


@router.get("/srt")
async def download_srt(
    project_id: int,
    include_unapproved: bool = False,
    session: AsyncSession = SessionDep,
    _: None = AdminDep,
):
    """下载 SRT 字幕文件 (临时生成，不存盘)"""
    await get_or_404(session, Project, project_id)

    shot_project_id_col = cast(InstrumentedAttribute[int], cast(object, Shot.project_id))
    shot_order_col = cast(InstrumentedAttribute[int], cast(object, Shot.order))
    res = await session.execute(
        select(Shot)
        .where(shot_project_id_col == project_id)
        .order_by(shot_order_col.asc())
    )
    shots = list(res.scalars().all())

    srt_content = build_srt(shots, include_unapproved=include_unapproved)

    if not srt_content:
        return PlainTextResponse("", media_type="text/plain")

    return Response(
        content=srt_content.encode("utf-8-sig"),  # BOM for Chinese text editors
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="subtitles_{project_id}.srt"',
            "Content-Type": "text/plain; charset=utf-8",
        },
    )

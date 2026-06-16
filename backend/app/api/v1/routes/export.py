# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""导出 API 路由"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminDep, SessionDep, SettingsDep, WsManagerDep, get_or_404
from app.config import Settings
from app.models.project import Character, Project, Shot
from app.schemas.export import ExportResponse, ExportVerticalRequest
from app.services.export_service import ExportService
from app.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# 内存导出状态缓存（如果 Redis 不可用时的降级方案）
_export_status_cache: dict[str, ExportResponse] = {}

# 全局 ExportService 实例
_export_service = ExportService()


def _get_redis_export_key(export_id: str) -> str:
    return f"openanimo:export:{export_id}"


async def _store_export_status(export_resp: ExportResponse) -> None:
    """存储导出状态到 Redis（降级到内存缓存）"""
    data = export_resp.model_dump_json()
    try:
        from app.orchestration.redis import get_redis
        r = await get_redis()
        await r.set(_get_redis_export_key(export_resp.export_id), data, ex=3600)
    except Exception:
        _export_status_cache[export_resp.export_id] = export_resp


async def _get_export_status(export_id: str) -> ExportResponse | None:
    """从 Redis 获取导出状态（降级到内存缓存）"""
    try:
        from app.orchestration.redis import get_redis
        r = await get_redis()
        data = await r.get(_get_redis_export_key(export_id))
        if data:
            return ExportResponse.model_validate_json(data)
    except Exception:
        pass
    return _export_status_cache.get(export_id)


async def _run_export_task(
    project_id: int,
    export_id: str,
    format: str,
    include_dialogue: bool,
    include_character_info: bool,
    ws: ConnectionManager,
    target_aspect: str = "9:16",
    reframe_mode: str = "smart",
) -> None:
    """后台导出任务"""
    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # 加载分镜和角色
            shot_res = await session.execute(
                select(Shot).where(Shot.project_id == project_id).order_by(Shot.order)
            )
            shots = list(shot_res.scalars().all())

            char_res = await session.execute(
                select(Character).where(Character.project_id == project_id)
            )
            characters = list(char_res.scalars().all())

        # 执行导出
        if format == "pdf":
            download_url = await _export_service.export_pdf(
                project=project,
                shots=shots,
                characters=characters,
                include_dialogue=include_dialogue,
                include_character_info=include_character_info,
            )
        elif format == "vertical":
            if not project.video_url:
                raise ValueError("Project has no video_url to export")
            download_url = await _export_service.export_vertical_video(
                video_url=project.video_url,
                target_aspect=target_aspect,
                reframe_mode=reframe_mode,
            )
        else:
            download_url = await _export_service.export_webtoon(
                project=project,
                shots=shots,
                include_dialogue=include_dialogue,
            )

        # 更新状态
        export_resp = ExportResponse(
            export_id=export_id,
            project_id=project_id,
            format=format,
            status="completed",
            download_url=download_url,
            created_at=datetime.now(),
        )
        await _store_export_status(export_resp)

        # 更新项目 exports 列表
        async with async_session_maker() as session:
            project = await session.get(Project, project_id)
            if project:
                exports = project.exports or []
                exports.append(download_url)
                project.exports = exports
                session.add(project)
                await session.commit()

        # WebSocket 通知
        from app.schemas.export import ExportCompletedEventData

        event_data = ExportCompletedEventData(
            export_id=export_id,
            format=format,
            download_url=download_url,
            status="completed",
        )
        await ws.send_event(project_id, {
            "type": "export_completed",
            "data": event_data.model_dump(),
        })

        logger.info(f"Export {export_id} completed: {download_url}")

    except Exception as e:
        logger.exception(f"Export {export_id} failed")
        export_resp = ExportResponse(
            export_id=export_id,
            project_id=project_id,
            format=format,
            status="failed",
            created_at=datetime.now(),
        )
        await _store_export_status(export_resp)

        # WebSocket 通知失败
        from app.schemas.export import ExportCompletedEventData

        event_data = ExportCompletedEventData(
            export_id=export_id,
            format=format,
            status="failed",
            error=str(e),
        )
        await ws.send_event(project_id, {
            "type": "export_completed",
            "data": event_data.model_dump(),
        })


@router.post(
    "/{project_id}/export/pdf",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_pdf(
    project_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = SessionDep,
    settings: Settings = SettingsDep,
    ws: ConnectionManager = WsManagerDep,
):
    """触发 PDF 导出"""
    await get_or_404(session, Project, project_id)

    export_id = uuid.uuid4().hex[:12]
    export_resp = ExportResponse(
        export_id=export_id,
        project_id=project_id,
        format="pdf",
        status="processing",
        created_at=datetime.now(),
    )
    await _store_export_status(export_resp)

    # 后台执行导出
    asyncio.create_task(
        _run_export_task(
            project_id=project_id,
            export_id=export_id,
            format="pdf",
            include_dialogue=True,
            include_character_info=True,
            ws=ws,
        )
    )

    return export_resp


@router.post(
    "/{project_id}/export/webtoon",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_webtoon(
    project_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = SessionDep,
    settings: Settings = SettingsDep,
    ws: ConnectionManager = WsManagerDep,
):
    """触发 Webtoon 导出"""
    await get_or_404(session, Project, project_id)

    export_id = uuid.uuid4().hex[:12]
    export_resp = ExportResponse(
        export_id=export_id,
        project_id=project_id,
        format="webtoon",
        status="processing",
        created_at=datetime.now(),
    )
    await _store_export_status(export_resp)

    # 后台执行导出
    asyncio.create_task(
        _run_export_task(
            project_id=project_id,
            export_id=export_id,
            format="webtoon",
            include_dialogue=True,
            include_character_info=True,
            ws=ws,
        )
    )

    return export_resp


@router.post(
    "/{project_id}/export/vertical",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_vertical(
    project_id: int,
    body: ExportVerticalRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = SessionDep,
    settings: Settings = SettingsDep,
    ws: ConnectionManager = WsManagerDep,
    _: None = AdminDep,
):
    """触发竖屏视频导出"""
    await get_or_404(session, Project, project_id)

    export_id = uuid.uuid4().hex[:12]
    export_resp = ExportResponse(
        export_id=export_id,
        project_id=project_id,
        format="vertical",
        status="processing",
        created_at=datetime.now(),
    )
    await _store_export_status(export_resp)

    asyncio.create_task(
        _run_export_task(
            project_id=project_id,
            export_id=export_id,
            format="vertical",
            include_dialogue=True,
            include_character_info=True,
            ws=ws,
            target_aspect=body.target_aspect,
            reframe_mode=body.reframe_mode,
        )
    )

    return export_resp


@router.get(
    "/{project_id}/export/{export_id}/status",
    response_model=ExportResponse,
)
async def get_export_status(
    project_id: int,
    export_id: str,
):
    """查询导出状态"""
    export_resp = await _get_export_status(export_id)
    if not export_resp:
        raise HTTPException(status_code=404, detail="Export task not found")
    if export_resp.project_id != project_id:
        raise HTTPException(status_code=404, detail="Export task not found")
    return export_resp

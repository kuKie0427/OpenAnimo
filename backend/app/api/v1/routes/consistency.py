# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
"""角色一致性评估 API 路由"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.api.deps import SessionDep, get_or_404
from app.models.consistency_report import ConsistencyReport
from app.models.project import Project
from app.schemas.consistency import (
    ConsistencyEvalResponse,
    ConsistencyReportRead,
    ProjectConsistencyRead,
)
from app.services.consistency_eval import get_consistency_eval_service

router = APIRouter()


@router.post(
    "/{project_id}/consistency-eval",
    response_model=ConsistencyEvalResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_consistency_eval(
    project_id: int,
    session: AsyncSession = SessionDep,
):
    """触发角色一致性评估（异步执行）"""
    project = await get_or_404(session, Project, project_id)
    service = get_consistency_eval_service()

    # 立即返回，后台执行评估
    import asyncio

    async def _run_eval() -> None:
        from app.db.session import get_session

        async for sess in get_session():
            try:
                report = await service.evaluate_project_consistency(
                    project, sess, run_id=None
                )
                # 发送 WebSocket 事件
                from app.ws.manager import ws_manager

                await ws_manager.send_event(
                    project.id,
                    {
                        "type": "consistency_eval_completed",
                        "data": {
                            "project_id": project.id,
                            "overall_score": report["overall_score"],
                            "character_count": len(report["character_reports"]),
                        },
                    },
                )
            except (RuntimeError, ValueError) as exc:
                import logging

                logging.getLogger(__name__).error(
                    "Consistency eval failed for project %d: %s", project.id, exc
                )

    # 在后台启动
    asyncio.create_task(_run_eval())

    return ConsistencyEvalResponse(eval_id=0, status="processing")


@router.get(
    "/{project_id}/consistency-report",
    response_model=ConsistencyReportRead,
)
async def get_latest_consistency_report(
    project_id: int,
    session: AsyncSession = SessionDep,
):
    """获取最新的评估报告"""
    await get_or_404(session, Project, project_id)

    stmt = (
        select(ConsistencyReport)
        .where(ConsistencyReport.project_id == project_id)
        .order_by(ConsistencyReport.created_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    report = res.scalar_one_or_none()

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No consistency report found. Trigger an evaluation first.",
        )

    report_data = None
    if report.report_data:
        try:
            report_data = ProjectConsistencyRead.model_validate(report.report_data)
        except ValidationError:
            report_data = None

    return ConsistencyReportRead(
        id=report.id,
        project_id=report.project_id,
        overall_score=report.overall_score,
        created_at=report.created_at,
        report_data=report_data,
    )


@router.get(
    "/{project_id}/consistency-report/history",
    response_model=list[ConsistencyReportRead],
)
async def get_consistency_report_history(
    project_id: int,
    session: AsyncSession = SessionDep,
    limit: int = 20,
):
    """获取历史评估报告列表"""
    await get_or_404(session, Project, project_id)

    stmt = (
        select(ConsistencyReport)
        .where(ConsistencyReport.project_id == project_id)
        .order_by(ConsistencyReport.created_at.desc())
        .limit(min(limit, 100))
    )
    res = await session.execute(stmt)
    reports = res.scalars().all()

    result = []
    for r in reports:
        report_data = None
        if r.report_data:
            try:
                report_data = ProjectConsistencyRead.model_validate(r.report_data)
            except ValidationError:
                report_data = None
        result.append(
            ConsistencyReportRead(
                id=r.id,
                project_id=r.project_id,
                overall_score=r.overall_score,
                created_at=r.created_at,
                report_data=report_data,
            )
        )
    return result

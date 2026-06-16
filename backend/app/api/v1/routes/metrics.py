from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import SessionDep, SettingsDep
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/runs")
async def get_run_summaries(
    project_id: int | None = Query(default=None, description="Filter by project"),
    limit: int = Query(default=20, ge=1, le=100),
    session=SessionDep,
    settings=SettingsDep,
):
    service = MetricsService(session)
    return await service.get_run_summaries(project_id=project_id, limit=limit)


@router.get("/costs")
async def get_cost_aggregates(
    project_id: int | None = Query(default=None, description="Filter by project"),
    session=SessionDep,
    settings=SettingsDep,
):
    service = MetricsService(session)
    return await service.get_cost_aggregates(project_id=project_id)


@router.get("/cost-breakdown")
async def get_cost_breakdown(
    project_id: int | None = Query(default=None, description="Filter by project"),
    run_id: int | None = Query(default=None, description="Filter by run"),
    session=SessionDep,
    settings=SettingsDep,
):
    service = MetricsService(session)
    return await service.get_cost_breakdown(project_id=project_id, run_id=run_id)


@router.get("/quality")
async def get_quality_by_stage(
    project_id: int | None = Query(default=None, description="Filter by project"),
    session=SessionDep,
    settings=SettingsDep,
):
    service = MetricsService(session)
    return await service.get_quality_by_stage(project_id=project_id)

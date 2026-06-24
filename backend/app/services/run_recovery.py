from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, Literal, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.agent_run import AgentRun
from app.models.artifact import Artifact
from app.models.stage import Stage
from app.orchestration import build_phase2_graph, get_checkpoint_history
from app.orchestration.state import PRODUCTION_STAGE_SEQUENCE
from app.orchestration.persistence import build_postgres_checkpointer
from app.schemas.project import (
    AgentRunRead,
    RecoveryControlRead,
    RecoveryStageRead,
    RecoverySummaryRead,
)


PHASE2_STAGE_ORDER: tuple[str, ...] = (
    "plan_outline",
    "outline_approval",
    "plan_characters",
    "characters_approval",
    "plan_shots",
    "shots_approval",
    "render_characters",
    "character_images_approval",
    "critique_character_images",
    "render_shots",
    "shot_images_approval",
    "critique_shot_images",
    "compose_videos",
    "compose_merge",
    "add_audio",
    "compose_approval",
    "review",
)

AGENT_TO_STAGE: dict[str, str] = {
    "outline": "plan_outline",
    "plan": "plan_characters",
    "render": "render_characters",
    "compose": "compose_videos",
    "review": "review",
}


def _thread_id_for_run(run: AgentRun) -> str:
    return f"agent-run-{run.id}" if run.id is not None else "agent-run-pending"


def _stage_index(stage: str | None) -> int:
    if not isinstance(stage, str) or stage not in PHASE2_STAGE_ORDER:
        return 0
    return PHASE2_STAGE_ORDER.index(stage)


def _next_stage(stage: str | None) -> str | None:
    index = _stage_index(stage)
    next_index = index + 1
    if next_index >= len(PHASE2_STAGE_ORDER):
        return None
    return PHASE2_STAGE_ORDER[next_index]


def _safe_stage_name(value: Any) -> str | None:
    if isinstance(value, str) and value in PHASE2_STAGE_ORDER:
        return value
    return None


def _stage_from_snapshot(snapshot: Any) -> str | None:
    values = getattr(snapshot, "values", None)
    if not isinstance(values, dict):
        return None
    current_stage = _safe_stage_name(values.get("current_stage"))
    if current_stage is not None:
        return current_stage
    route_stage = _safe_stage_name(values.get("route_stage"))
    if route_stage is not None:
        return route_stage
    stage_history = values.get("stage_history")
    if isinstance(stage_history, list):
        for entry in reversed(stage_history):
            stage_name = _safe_stage_name(entry)
            if stage_name is not None:
                return stage_name
    return None


def _snapshot_values(snapshots: Sequence[Any]) -> dict[str, Any]:
    for snapshot in snapshots:
        values = getattr(snapshot, "values", None)
        if isinstance(values, dict):
            return values
    return {}


def _snapshot_next_stage(snapshots: Sequence[Any]) -> str | None:
    for snapshot in snapshots:
        next_nodes = getattr(snapshot, "next", ())
        if isinstance(next_nodes, (list, tuple)) and next_nodes:
            next_stage = _safe_stage_name(next_nodes[0])
            if next_stage is not None:
                return next_stage
    return None


def _normalize_stage_history(values: dict[str, Any]) -> list[str]:
    raw_history = values.get("stage_history")
    if not isinstance(raw_history, list):
        return []

    completed: list[str] = []
    for entry in raw_history:
        if isinstance(entry, str) and entry in PRODUCTION_STAGE_SEQUENCE and entry not in completed:
            completed.append(entry)
    return completed


_APPROVAL_TO_PRODUCED_STAGE: dict[str, str] = {
    "outline_approval": "plan_outline",
    "characters_approval": "plan_characters",
    "shots_approval": "plan_shots",
    "character_images_approval": "render_characters",
    "shot_images_approval": "render_shots",
    "compose_approval": "compose_merge",
}


def _production_stage_for_approval(stage: str | None) -> str | None:
    if not isinstance(stage, str):
        return None
    return _APPROVAL_TO_PRODUCED_STAGE.get(stage)


def _resume_target_stage(
    current_stage: str, *, values: dict[str, Any], completed_stages: Sequence[str]
) -> str | None:
    route_stage = _safe_stage_name(values.get("route_stage"))

    if current_stage == "review":
        return route_stage or current_stage

    if current_stage.endswith("_approval"):
        return current_stage

    if current_stage in completed_stages:
        return route_stage or _next_stage(current_stage)

    return current_stage


async def _checkpoint_history(database_url: str, run: AgentRun) -> list[Any]:
    if run.id is None:
        return []
    try:
        async with build_postgres_checkpointer(database_url) as checkpointer:
            compiled_graph = build_phase2_graph().compile(checkpointer=cast(Any, checkpointer))
            graph_run = cast(Any, SimpleNamespace(id=run.id, thread_id=_thread_id_for_run(run)))
            return await get_checkpoint_history(compiled_graph, graph_run, limit=8)
    except (RuntimeError, ValueError):
        return []


async def _stage_artifact_counts(session: AsyncSession, run_id: int | None) -> dict[str, int]:
    if run_id is None:
        return {}
    stage_name_col = cast(InstrumentedAttribute[str], cast(object, Stage.name))
    stage_id_col = cast(InstrumentedAttribute[int], cast(object, Stage.id))
    stage_run_id_col = cast(InstrumentedAttribute[int], cast(object, Stage.run_id))
    artifact_stage_id_col = cast(InstrumentedAttribute[int], cast(object, Artifact.stage_id))
    artifact_count = func.count(artifact_stage_id_col)
    result = await session.execute(
        select(stage_name_col, artifact_count)
        .select_from(Stage)
        .join(Artifact, artifact_stage_id_col == stage_id_col, isouter=True)
        .where(stage_run_id_col == run_id)
        .group_by(stage_name_col)
    )
    return {name: int(count or 0) for name, count in result.tuples().all()}


def _infer_current_stage(run: AgentRun, snapshots: Sequence[Any]) -> str:
    latest_stage = None
    for snapshot in snapshots:
        latest_stage = _stage_from_snapshot(snapshot)
        if latest_stage is not None:
            break

    if latest_stage is not None:
        return latest_stage

    mapped_stage = AGENT_TO_STAGE.get(run.current_agent or "")
    if mapped_stage is not None:
        return mapped_stage

    return "plan_outline"


async def build_recovery_summary(
    *,
    session: AsyncSession,
    database_url: str,
    run: AgentRun,
) -> RecoverySummaryRead:
    run_id = run.id
    run_pk = run_id if run_id is not None else 0
    snapshots = await _checkpoint_history(database_url, run)
    latest_values = _snapshot_values(snapshots)
    pending_stage = _snapshot_next_stage(snapshots)
    current_stage = pending_stage or _infer_current_stage(run, snapshots)
    completed_stages = _normalize_stage_history(latest_values)
    approval_parent = _production_stage_for_approval(current_stage)
    if approval_parent is not None and approval_parent not in completed_stages:
        completed_stages.append(approval_parent)
    next_stage = _resume_target_stage(
        current_stage,
        values=latest_values,
        completed_stages=completed_stages,
    )
    artifact_counts = await _stage_artifact_counts(session, run_pk)

    stage_history = [
        RecoveryStageRead(
            name=stage,
            status="current"
            if stage == current_stage
            else "completed"
            if stage in completed_stages
            else "pending",
            artifact_count=artifact_counts.get(stage, 0),
        )
        for stage in PHASE2_STAGE_ORDER
    ]

    preserved_stages = [stage.name for stage in stage_history if stage.status == "completed"]

    return RecoverySummaryRead(
        project_id=run.project_id,
        run_id=run_pk,
        thread_id=_thread_id_for_run(run),
        current_stage=current_stage,
        next_stage=next_stage,
        preserved_stages=preserved_stages,
        stage_history=stage_history,
        resumable=run.status in {"queued", "running", "failed", "cancelled"},
    )


async def build_recovery_control_surface(
    *,
    session: AsyncSession,
    database_url: str,
    run: AgentRun,
    state: Literal["active", "recoverable"],
) -> RecoveryControlRead:
    summary = await build_recovery_summary(session=session, database_url=database_url, run=run)
    detail = (
        "Project already has an active run" if state == "active" else "Project has a resumable run"
    )
    return RecoveryControlRead(
        state=state,
        detail=detail,
        thread_id=summary.thread_id,
        active_run=AgentRunRead.model_validate(run),
        recovery_summary=summary,
    )

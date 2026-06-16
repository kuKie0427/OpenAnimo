# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false
from __future__ import annotations

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.agent_trace import AgentTrace


class MetricsService:
    """Aggregation queries over AgentTrace for project observability."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_run_summaries(
        self,
        project_id: int | None = None,
        limit: int = 20,
        pricing_overrides: dict | None = None,
    ) -> list[dict]:
        """Return recent N runs with per-run aggregates.

        Fields: run_id, agent_count, total_llm_calls, total_tokens,
                total_images, total_video_seconds, avg_duration_seconds,
                success_rate, total_cost_usd.
        """
        from app.services.pricing import estimate_cost
        run_stmt = select(AgentRun.id)
        if project_id is not None:
            run_stmt = run_stmt.where(AgentRun.project_id == project_id)
        run_stmt = run_stmt.order_by(AgentRun.id.desc()).limit(limit)

        run_result = await self.session.execute(run_stmt)
        run_ids = [row[0] for row in run_result.all()]

        if not run_ids:
            return []

        trace_stmt = select(AgentTrace).where(AgentTrace.run_id.in_(run_ids))
        trace_result = await self.session.execute(trace_stmt)
        traces = trace_result.scalars().all()

        run_traces: dict[int, list[AgentTrace]] = {}
        for t in traces:
            run_traces.setdefault(t.run_id, []).append(t)

        summaries = []
        for run_id in run_ids:
            entries = run_traces.get(run_id, [])
            if not entries:
                continue

            agent_names = {e.agent_name for e in entries}
            total_llm_calls = sum(e.llm_calls for e in entries)
            total_input_tokens = sum(e.tokens_input or 0 for e in entries)
            total_output_tokens = sum(e.tokens_output or 0 for e in entries)
            total_tokens = total_input_tokens + total_output_tokens
            total_images = sum(e.images_generated for e in entries)
            total_video_seconds = sum(e.video_seconds or 0.0 for e in entries)

            run_cost = estimate_cost(
                model_name="",
                tokens_input=total_input_tokens,
                tokens_output=total_output_tokens,
                images=total_images,
                video_seconds=total_video_seconds,
                pricing_overrides=pricing_overrides,
            )

            deltas = []
            for e in entries:
                if e.start_time and e.end_time:
                    deltas.append((e.end_time - e.start_time).total_seconds())
            avg_duration_seconds = (
                round(sum(deltas) / len(deltas), 2) if deltas else None
            )

            completed = sum(1 for e in entries if e.status == "completed")
            success_rate = round(completed / len(entries), 4) if entries else 0.0

            summaries.append({
                "run_id": run_id,
                "agent_count": len(agent_names),
                "total_llm_calls": total_llm_calls,
                "total_tokens": total_tokens,
                "total_images": total_images,
                "total_video_seconds": total_video_seconds,
                "avg_duration_seconds": avg_duration_seconds,
                "success_rate": success_rate,
                "total_cost_usd": str(run_cost),
            })

        return summaries

    async def get_cost_aggregates(
        self, project_id: int | None = None
    ) -> list[dict]:
        """Aggregate token/image costs grouped by agent_name.

        Fields: agent_name, total_tokens_input, total_tokens_output,
                total_images_generated, total_runs.
        """
        stmt = (
            select(
                AgentTrace.agent_name,
                func.sum(AgentTrace.tokens_input).label("total_tokens_input"),
                func.sum(AgentTrace.tokens_output).label("total_tokens_output"),
                func.sum(AgentTrace.images_generated).label("total_images_generated"),
                func.count(func.distinct(AgentTrace.run_id)).label("total_runs"),
            )
        )

        if project_id is not None:
            stmt = stmt.join(AgentRun, AgentTrace.run_id == AgentRun.id).where(
                AgentRun.project_id == project_id
            )

        stmt = stmt.group_by(AgentTrace.agent_name).order_by(AgentTrace.agent_name)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "agent_name": row.agent_name,
                "total_tokens_input": row.total_tokens_input or 0,
                "total_tokens_output": row.total_tokens_output or 0,
                "total_images_generated": row.total_images_generated or 0,
                "total_runs": row.total_runs or 0,
            }
            for row in rows
        ]

    async def get_cost_breakdown(
        self, project_id: int | None = None, run_id: int | None = None,
        pricing_overrides: dict | None = None,
    ) -> list[dict]:
        """Cost breakdown grouped by (agent_name, model_name).

        Fields: agent_name, model_name, total_input_tokens, total_output_tokens,
                total_images, total_video_seconds, total_cost_usd.
        """
        from app.services.pricing import estimate_cost

        stmt = select(
            AgentTrace.agent_name,
            AgentTrace.model_name,
            func.sum(AgentTrace.tokens_input).label("total_tokens_input"),
            func.sum(AgentTrace.tokens_output).label("total_tokens_output"),
            func.sum(AgentTrace.images_generated).label("total_images"),
            func.coalesce(func.sum(AgentTrace.video_seconds), 0.0).label(
                "total_video_seconds"
            ),
        )

        if project_id is not None:
            stmt = stmt.join(AgentRun, AgentTrace.run_id == AgentRun.id).where(
                AgentRun.project_id == project_id
            )
        if run_id is not None:
            stmt = stmt.where(AgentTrace.run_id == run_id)

        stmt = stmt.group_by(AgentTrace.agent_name, AgentTrace.model_name)

        result = await self.session.execute(stmt)
        rows = result.all()

        breakdown = []
        for row in rows:
            cost = estimate_cost(
                model_name=row.model_name or "",
                tokens_input=row.total_tokens_input or 0,
                tokens_output=row.total_tokens_output or 0,
                images=row.total_images or 0,
                video_seconds=row.total_video_seconds or 0.0,
                pricing_overrides=pricing_overrides,
            )
            breakdown.append({
                "agent_name": row.agent_name,
                "model_name": row.model_name or "",
                "total_input_tokens": row.total_tokens_input or 0,
                "total_output_tokens": row.total_tokens_output or 0,
                "total_images": row.total_images or 0,
                "total_video_seconds": float(row.total_video_seconds or 0.0),
                "total_cost_usd": str(cost),
            })

        return breakdown

    async def get_quality_by_stage(
        self, project_id: int | None = None
    ) -> list[dict]:
        """Group by stage, count status distribution.

        Fields: stage, total_count, completed_count, failed_count,
                running_count, error_rate.
        """
        stmt = (
            select(
                AgentTrace.stage,
                func.count().label("total_count"),
                func.sum(
                    case((AgentTrace.status == "completed", 1), else_=0)
                ).label("completed_count"),
                func.sum(
                    case((AgentTrace.status == "failed", 1), else_=0)
                ).label("failed_count"),
                func.sum(
                    case((AgentTrace.status == "running", 1), else_=0)
                ).label("running_count"),
            )
        )

        if project_id is not None:
            stmt = stmt.join(AgentRun, AgentTrace.run_id == AgentRun.id).where(
                AgentRun.project_id == project_id
            )

        stmt = stmt.group_by(AgentTrace.stage).order_by(AgentTrace.stage)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "stage": row.stage,
                "total_count": row.total_count,
                "completed_count": row.completed_count or 0,
                "failed_count": row.failed_count or 0,
                "running_count": row.running_count or 0,
                "error_rate": (
                    round((row.failed_count or 0) / row.total_count, 4)
                    if row.total_count
                    else 0.0
                ),
            }
            for row in rows
        ]

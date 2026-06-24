# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false
from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from langgraph.types import Command
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.utils import utcnow
from app.agents.base import AgentContext, BaseAgent
from app.agents.outline import OutlineAgent
from app.agents.plan import PlanAgent
from app.agents.render import RenderAgent
from app.agents.compose import ComposeAgent
from app.agents.critic import CriticAgent
from app.agents.review_rules import ReviewRuleEngine
from app.config import Settings
from app.models.agent_run import AgentMessage, AgentRun
from app.models.project import Character, Project, Shot
from app.schemas.project import GenerateRequest
from app.orchestration.graph import build_phase2_graph
from app.orchestration.persistence import build_postgres_checkpointer
from app.orchestration.runtime import (
    build_graph_config,
    build_phase2_runtime_context,
    build_stage_recovery_config,
)
from app.orchestration.state import Phase2Stage, next_production_stage, workflow_progress_for_stage
from app.services.creative_control import collect_project_blocking_clips
from app.services.file_cleaner import delete_files
from app.services.image_factory import create_image_service
from app.services.provider_resolution import settings_with_provider_snapshot
from app.services.run_recovery import PHASE2_STAGE_ORDER, build_recovery_summary
from app.services.text_factory import create_text_service
from app.services.video_factory import create_video_service
from app.ws.manager import ConnectionManager
from app.orchestration.redis import (
    clear_awaiting_payload,
    clear_confirm_event_redis,
    get_awaiting_payload,  # noqa: F401 - re-export for external consumers
    get_awaiting_payload_key,  # noqa: F401 - re-export for external consumers
    get_confirm_channel,  # noqa: F401 - re-export for external consumers
    get_confirm_event_key,  # noqa: F401 - re-export for external consumers
    get_redis,  # noqa: F401 - re-export for external consumers
    store_awaiting_payload,
    trigger_confirm_redis,  # noqa: F401 - re-export for external consumers
    wait_for_confirm_redis,
)

logger = logging.getLogger(__name__)


def _next_phase2_stage(stage: str | None) -> str | None:
    if not isinstance(stage, str) or stage not in PHASE2_STAGE_ORDER:
        return None
    next_index = PHASE2_STAGE_ORDER.index(stage) + 1
    if next_index >= len(PHASE2_STAGE_ORDER):
        return None
    return PHASE2_STAGE_ORDER[next_index]


STAGE_AGENT_MAP = {
    "plan_outline": "outline",
    "outline_approval": "outline",
    "plan_characters": "plan",
    "characters_approval": "plan",
    "plan_shots": "plan",
    "shots_approval": "plan",
    "render_characters": "render",
    "character_images_approval": "render",
    "critique_character_images": "critic",
    "render_shots": "render",
    "shot_images_approval": "render",
    "critique_shot_images": "critic",
    "compose_videos": "compose",
    "compose_merge": "compose",
    "add_audio": "compose",
    "compose_approval": "compose",
    "review": "review",
}

GRAPH_STAGE_FOR_AGENT = {
    "outline": "plan_outline",
    "plan": "plan_characters",
    "characters": "plan_characters",
    "shots": "plan_characters",
    "render": "render_characters",
    "character_images": "render_characters",
    "shot_images": "render_characters",
    "compose": "compose_videos",
    "review": "review",
    "critic": "critique_character_images",
}
AGENT_STAGE_MAP = STAGE_AGENT_MAP
RESUME_AGENT_FOR_STAGE = STAGE_AGENT_MAP


def _resume_agent_for_stage(stage: str | None) -> str:
    if not isinstance(stage, str):
        return "plan"
    return RESUME_AGENT_FOR_STAGE.get(stage, "plan")


def _video_generation_skipped_in_result(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return bool(result.get("video_generation_skipped"))


# Agent 完成后的描述信息
AGENT_COMPLETION_INFO = {
    "outline": {
        "completed": "已完成故事大纲",
        "details": "生成了三幕结构和视觉方向",
        "next": "确认后将进入角色设计",
        "question": "故事大纲方向是否满意？",
    },
    "plan": {
        "completed": "已完成创作方案规划",
        "details": "生成了角色设定和分镜脚本",
        "next": "接下来将为角色和分镜生成参考图片",
        "question": "创作方案是否符合您的预期？如果需要修改，请告诉我具体的调整意见。",
    },
    "characters": {
        "completed": "已完成角色设定",
        "details": "角色设定已生成",
        "next": "确认后将进入分镜设计",
        "question": "角色设定是否满意？",
    },
    "shots": {
        "completed": "已完成分镜脚本",
        "details": "分镜脚本已生成",
        "next": "确认后将进入渲染阶段",
        "question": "分镜脚本是否满意？",
    },
    "render": {
        "completed": "已完成角色形象和分镜画面渲染",
        "details": "角色形象和分镜画面均已渲染完成",
        "next": "接下来将根据分镜生成视频片段并合成",
        "question": "角色形象和分镜画面是否满意？如果需要重新生成，请告诉我。",
    },
    "character_images": {
        "completed": "已完成角色形象渲染",
        "details": "角色形象图已渲染完成",
        "next": "确认后将渲染分镜画面",
        "question": "角色形象图是否满意？",
    },
    "shot_images": {
        "completed": "已完成分镜画面渲染",
        "details": "分镜画面均已渲染完成",
        "next": "确认后将进入视频合成",
        "question": "分镜画面是否满意？",
    },
    "critic": {
        "completed": "已完成质量审查",
        "details": "已对生成的图像进行一致性、质量和构图审查",
        "next": "审查通过，继续下一步",
        "question": "审查结果是否满意？",
    },
    "compose": {
        "completed": "已完成视频合成",
        "next": "您的漫剧已经准备就绪！可以下载或分享了。",
        "question": "最终视频效果满意吗？",
    },
}


class GenerationOrchestrator:
    def __init__(self, *, settings: Settings, ws: ConnectionManager, session: AsyncSession):
        self.settings = settings
        self.ws = ws
        self.session = session
        self._last_user_feedback_id: int | None = None
        self.agents = [
            OutlineAgent(),
            PlanAgent(),
            RenderAgent(),
            ComposeAgent(),
            CriticAgent(),
            ReviewRuleEngine(),  # 处理用户反馈并路由重新生成（不会参与正常生成流程）
        ]

    def _agent_index(self, agent_name: str) -> int:
        for idx, agent in enumerate(self.agents):
            if agent.name == agent_name:
                return idx
        raise ValueError(f"Unknown agent: {agent_name}")

    async def set_run_state(self, run: AgentRun, **fields) -> AgentRun:
        """Public wrapper for _set_run."""
        return await self._set_run(run, **fields)

    def get_agent(self, name: str) -> BaseAgent:
        """Return agent instance by name. Raises ValueError if not found."""
        return self.agents[self._agent_index(name)]

    async def cleanup_for_rerun(
        self, project_id: int, start_agent: str, mode: str = "full",
        target_ids: Any = None,
    ) -> None:
        """Public wrapper for _cleanup_for_rerun."""
        kwargs: dict[str, Any] = {}
        if target_ids is not None:
            kwargs["target_ids"] = target_ids
        return await self._cleanup_for_rerun(project_id, start_agent, mode, **kwargs)

    async def _delete_project_shots(self, project_id: int) -> None:
        await self.session.execute(delete(Shot).where(Shot.project_id == project_id))

    async def _delete_project_characters(self, project_id: int) -> None:
        await self.session.execute(delete(Character).where(Character.project_id == project_id))

    async def _clear_character_images(
        self, project_id: int, character_ids: list[int] | None = None
    ) -> None:
        """清空角色图片（先删除文件再清空 URL）"""
        query = select(Character).where(Character.project_id == project_id)
        if character_ids:
            query = query.where(Character.id.in_(character_ids))
        res = await self.session.execute(query)
        chars = res.scalars().all()
        if chars:
            # 先删除文件
            delete_files([char.image_url for char in chars])
            # 再清空 URL
            for char in chars:
                char.image_url = None
                self.session.add(char)

    async def _clear_shot_images(
        self, project_id: int, shot_ids: list[int] | None = None
    ) -> None:
        """清空分镜首帧图片（先删除文件再清空 URL）"""
        query = select(Shot).where(Shot.project_id == project_id)
        if shot_ids:
            query = query.where(Shot.id.in_(shot_ids))
        res = await self.session.execute(query)
        shots = res.scalars().all()
        if shots:
            # 先删除文件
            delete_files([shot.image_url for shot in shots])
            # 再清空 URL
            for shot in shots:
                shot.image_url = None
                self.session.add(shot)

    async def _clear_shot_videos(
        self, project_id: int, shot_ids: list[int] | None = None
    ) -> None:
        """清空分镜视频（先删除文件再清空 URL）"""
        query = select(Shot).where(Shot.project_id == project_id)
        if shot_ids:
            query = query.where(Shot.id.in_(shot_ids))
        res = await self.session.execute(query)
        shots = res.scalars().all()
        if shots:
            # 先删除文件
            delete_files([shot.video_url for shot in shots])
            # 再清空 URL
            for shot in shots:
                shot.video_url = None
                self.session.add(shot)

    async def _cleanup_for_rerun(
        self, project_id: int, start_agent: str, mode: str = "full",
        target_ids: Any = None,
    ) -> None:
        """清理逻辑：根据重新运行的 agent 和模式清理数据

        Args:
            project_id: 项目 ID
            start_agent: 从哪个 agent 开始重新运行
            mode: "full" 全量清理，"incremental" 增量清理（只清理下游产物，保留数据）
            target_ids: 精细化控制的目标 ID（None 表示全量清理）
        """
        character_ids: list[int] | None = None
        shot_ids: list[int] | None = None
        if target_ids is not None:
            char_ids = getattr(target_ids, "character_ids", None)
            shot_ids_val = getattr(target_ids, "shot_ids", None)
            character_ids = char_ids if char_ids else None
            shot_ids = shot_ids_val if shot_ids_val else None

        char_kwargs: dict[str, Any] = {}
        shot_kwargs: dict[str, Any] = {}
        if character_ids is not None:
            char_kwargs["character_ids"] = character_ids
        if shot_ids is not None:
            shot_kwargs["shot_ids"] = shot_ids

        cleared_types: list[str] = []

        if mode == "incremental":
            if start_agent in {"outline"}:
                await self._clear_character_images(project_id, **char_kwargs)
                await self._clear_shot_images(project_id, **shot_kwargs)
                await self._clear_shot_videos(project_id, **shot_kwargs)
                project = await self.session.get(Project, project_id)
                if project is not None:
                    project.outline_approved = False
                    self.session.add(project)
            elif start_agent in {"plan"}:
                await self._clear_character_images(project_id, **char_kwargs)
                await self._clear_shot_images(project_id, **shot_kwargs)
                await self._clear_shot_videos(project_id, **shot_kwargs)
            elif start_agent == "render":
                await self._clear_character_images(project_id, **char_kwargs)
                await self._clear_shot_images(project_id, **shot_kwargs)
                await self._clear_shot_videos(project_id, **shot_kwargs)
            elif start_agent == "compose":
                await self._clear_shot_videos(project_id, **shot_kwargs)
            else:
                raise ValueError(f"Unsupported start_agent for cleanup: {start_agent}")
        else:
            if start_agent in {"outline"}:
                await self._delete_project_shots(project_id)
                await self._delete_project_characters(project_id)
                project = await self.session.get(Project, project_id)
                if project is not None:
                    project.story_outline = {}
                    project.visual_bible = None
                    project.outline_approved = False
                    self.session.add(project)
                cleared_types = ["characters", "shots", "outline"]
            elif start_agent in {"plan"}:
                await self._delete_project_shots(project_id)
                await self._delete_project_characters(project_id)
                cleared_types = ["characters", "shots"]
            elif start_agent == "render":
                await self._clear_character_images(project_id, **char_kwargs)
                await self._clear_shot_images(project_id, **shot_kwargs)
                await self._clear_shot_videos(project_id, **shot_kwargs)
            elif start_agent == "compose":
                await self._clear_shot_videos(project_id, **shot_kwargs)
            else:
                raise ValueError(f"Unsupported start_agent for cleanup: {start_agent}")

        await self.session.commit()

        # 通知前端数据已清理（仅全量模式）
        if cleared_types:
            await self.ws.send_event(
                project_id,
                {
                    "type": "data_cleared",
                    "data": {
                        "cleared_types": cleared_types,
                        "start_agent": start_agent,
                        "mode": mode,
                    },
                },
            )

    async def _set_run(self, run: AgentRun, **fields) -> AgentRun:
        for k, v in fields.items():
            setattr(run, k, v)
        run.updated_at = utcnow()
        if self.session:
            self.session.add(run)
            await self.session.commit()
            await self.session.refresh(run)
        return run

    async def _log(self, run_id: int, *, agent: str, role: str, content: str) -> None:
        msg = AgentMessage(run_id=run_id, agent=agent, role=role, content=content)
        self.session.add(msg)
        await self.session.commit()

    async def _handle_run_failure(
        self, project_id: int, run: AgentRun, run_id: int, error: Exception, context: str = "Run"
    ) -> None:
        await self.session.rollback()
        try:
            await self._log(
                run_id, agent="orchestrator", role="system", content=f"{context} failed: {error!r}"
            )
            await self._set_run(run, status="failed", error=str(error))

            project = await self.session.get(Project, project_id)
            if project is not None:
                project.status = "failed"
                self.session.add(project)
                await self.session.commit()
                blocking_clips = await collect_project_blocking_clips(self.session, project)
                await self.ws.send_event(
                    project_id,
                    {
                        "type": "project_updated",
                        "data": {
                            "project": {
                                "id": project_id,
                                "status": project.status,
                                "video_url": getattr(project, "video_url", None),
                                "blocking_clips": blocking_clips,
                            }
                        },
                    },
                )
        except (RuntimeError, OSError):
            pass
        await self.ws.send_event(
            project_id,
            {
                "type": "run_failed",
                "data": {"run_id": run_id, "project_id": project_id, "error": str(error)},
            },
        )

    async def _complete_run(
        self,
        project_id: int,
        run: AgentRun,
        run_id: int,
        final_stage: str,
        video_generation_skipped: bool,
    ) -> None:
        completed_agent = getattr(run, "current_agent", None)
        await self._set_run(run, status="succeeded", current_agent=None, progress=1.0)
        completed_data: dict = {
            "run_id": run_id,
            "project_id": project_id,
            "current_stage": final_stage,
            "current_agent": completed_agent,
        }
        if video_generation_skipped:
            completed_data["message"] = "视频未配置，已完成文本和图片生成"
            completed_data["video_generation_pending"] = True
        await self.ws.send_event(project_id, {"type": "run_completed", "data": completed_data})

    async def _cleanup_run(self, run_id: int) -> None:
        await clear_confirm_event_redis(run_id)
        await clear_awaiting_payload(run_id)

    async def _wait_for_confirm(
        self, project_id: int, run: AgentRun, agent_name: str,
        agent_ctx: AgentContext | None = None,
        interrupt_data: dict[str, Any] | None = None,
    ) -> str | None:
        current_stage = GRAPH_STAGE_FOR_AGENT.get(agent_name, "plan")
        next_stage = _next_phase2_stage(current_stage)
        recovery_summary = await build_recovery_summary(
            session=self.session,
            database_url=self.settings.database_url,
            run=run,
        )
        run_pk = run.id or 0

        if agent_ctx and agent_ctx.completion_info:
            completed = agent_ctx.completion_info.completed or f"「{agent_name}」已完成"
            details = agent_ctx.completion_info.details
            next_step = agent_ctx.completion_info.next or "继续下一步"
            question = agent_ctx.completion_info.question or "是否继续？"
        else:
            info = AGENT_COMPLETION_INFO.get(agent_name, {})
            completed = info.get("completed", f"「{agent_name}」已完成")
            details = info.get("details", "")
            next_step = info.get("next", "继续下一步")
            question = info.get("question", "是否继续？")

        # 构建详细消息
        message_parts = [completed]
        if details:
            message_parts.append(f"{details}")
        message_parts.append(next_step)
        message_parts.append(question)

        full_message = "\n".join(message_parts)

        # 清理上一轮遗留的 confirm（避免误触导致直接跳过等待）
        await clear_confirm_event_redis(run_pk)

        awaiting_payload = {
            "run_id": run_pk,
            "project_id": project_id,
            "agent": agent_name,
            "gate": agent_name,
            "current_stage": current_stage,
            "stage": current_stage,
            "next_stage": next_stage,
            "recovery_summary": recovery_summary.model_dump(mode="json"),
            "preserved_stages": recovery_summary.preserved_stages,
            "message": full_message,
            "completed": completed,
            "next_step": next_step,
            "question": question,
        }
        if agent_name == "outline" and agent_ctx is not None:
            outline = getattr(agent_ctx.project, "story_outline", None)
            if isinstance(outline, dict):
                awaiting_payload["story_outline"] = outline
                awaiting_payload["visual_bible"] = getattr(agent_ctx.project, "visual_bible", None)

        # 传递 entity 上下文（entity_type/entity_ids/entity_summaries）到前端
        if interrupt_data:
            for field in ("entity_type", "entity_ids", "entity_summaries"):
                if field in interrupt_data:
                    awaiting_payload[field] = interrupt_data[field]

        # 缓存 payload 以便 WS 重连补发（事件本身可能在客户端未连接时丢失）
        await store_awaiting_payload(run_pk, awaiting_payload)

        await self.ws.send_event(
            project_id,
            {
                "type": "run_awaiting_confirm",
                "data": awaiting_payload,
            },
        )

        try:
            ok = await wait_for_confirm_redis(run_pk, timeout=1800)
            if not ok:
                raise asyncio.TimeoutError()
        except asyncio.TimeoutError:
            await clear_awaiting_payload(run_pk)
            raise RuntimeError(f"等待确认超时（agent: {agent_name}）")

        await clear_awaiting_payload(run_pk)

        confirmed_recovery = await build_recovery_summary(
            session=self.session,
            database_url=self.settings.database_url,
            run=run,
        )

        post_approval_stage = _next_phase2_stage(next_stage)

        await self.ws.send_event(
            project_id,
            {
                "type": "run_confirmed",
                "data": {
                    "run_id": run_pk,
                    "project_id": project_id,
                    "agent": agent_name,
                    "gate": agent_name,
                    "current_stage": post_approval_stage,
                    "stage": post_approval_stage,
                    "next_stage": _next_phase2_stage(post_approval_stage)
                    if post_approval_stage
                    else None,
                    "recovery_summary": confirmed_recovery.model_dump(mode="json"),
                },
            },
        )

        # 刷新 session 以确保能读取到其他 session 提交的新数据
        await self.session.commit()  # 提交当前事务

        # 读取本次确认携带的最新用户反馈（若有）
        res = await self.session.execute(
            select(AgentMessage)
            .where(AgentMessage.run_id == run_pk)
            .where(AgentMessage.role == "user")
            .order_by(AgentMessage.created_at.desc())
            .limit(1)
        )
        msg = res.scalars().first()
        if msg and msg.id != self._last_user_feedback_id and msg.content.strip():
            self._last_user_feedback_id = msg.id
            return msg.content.strip()

        return None

    async def _send_auto_approval_events(
        self, project_id: int, run: AgentRun, agent_name: str, agent_ctx: AgentContext | None = None
    ) -> None:
        current_stage = GRAPH_STAGE_FOR_AGENT.get(agent_name, "plan")
        approval_stage = _next_phase2_stage(current_stage)
        post_approval_stage = _next_phase2_stage(approval_stage) if approval_stage else None
        recovery_summary = await build_recovery_summary(
            session=self.session,
            database_url=self.settings.database_url,
            run=run,
        )
        run_pk = run.id or 0

        if agent_ctx and agent_ctx.completion_info:
            completed = agent_ctx.completion_info.completed or f"「{agent_name}」已完成"
            next_step = agent_ctx.completion_info.next or "继续下一步"
            question = agent_ctx.completion_info.question or "是否继续？"
        else:
            info = AGENT_COMPLETION_INFO.get(agent_name, {})
            completed = info.get("completed", f"「{agent_name}」已完成")
            next_step = info.get("next", "继续下一步")
            question = info.get("question", "是否继续？")

        message_parts = [completed, next_step, question, "[auto]"]
        full_message = "\n".join(message_parts)

        await self.ws.send_event(
            project_id,
            {
                "type": "run_awaiting_confirm",
                "data": {
                    "run_id": run_pk,
                    "project_id": project_id,
                    "agent": agent_name,
                    "gate": agent_name,
                    "current_stage": current_stage,
                    "stage": current_stage,
                    "next_stage": approval_stage,
                    "recovery_summary": recovery_summary.model_dump(mode="json"),
                    "preserved_stages": recovery_summary.preserved_stages,
                    "message": full_message,
                    "completed": completed,
                    "next_step": next_step,
                    "question": question,
                    "auto_mode": True,
                    "story_outline": getattr(agent_ctx.project, "story_outline", None)
                    if agent_name == "outline" and agent_ctx is not None
                    else None,
                    "visual_bible": getattr(agent_ctx.project, "visual_bible", None)
                    if agent_name == "outline" and agent_ctx is not None
                    else None,
                },
            },
        )

        confirmed_recovery = await build_recovery_summary(
            session=self.session,
            database_url=self.settings.database_url,
            run=run,
        )

        await self.ws.send_event(
            project_id,
            {
                "type": "run_confirmed",
                "data": {
                    "run_id": run_pk,
                    "project_id": project_id,
                    "agent": agent_name,
                    "gate": agent_name,
                    "current_stage": post_approval_stage,
                    "stage": post_approval_stage,
                    "next_stage": _next_phase2_stage(post_approval_stage)
                    if post_approval_stage
                    else None,
                    "recovery_summary": confirmed_recovery.model_dump(mode="json"),
                    "auto_mode": True,
                },
            },
        )

    def _build_agent_context(
        self,
        *,
        project: Project,
        run: AgentRun,
        request: GenerateRequest,
    ) -> AgentContext:
        context_settings = settings_with_provider_snapshot(
            self.settings,
            run.provider_snapshot,
        )
        return AgentContext(
            settings=context_settings,
            session=self.session,
            ws=self.ws,
            project=project,
            run=run,
            llm=cast(Any, create_text_service(context_settings)),
            image=create_image_service(context_settings),
            video=cast(Any, create_video_service(context_settings)),
        )

    def _build_phase2_state(
        self,
        *,
        project_id: int,
        run_id: int,
        thread_id: str,
        start_stage: str,
    ) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "run_id": run_id,
            "thread_id": thread_id,
            "current_stage": start_stage,
            "stage_history": [],
            "approval_history": [],
            "artifact_lineage": [],
            "review_requested": False,
            "approval_feedback": "",
            "route_stage": start_stage,
            "route_mode": "full",
            "video_generation_skipped": False,
        }

    async def _invoke_phase2_graph(
        self,
        *,
        project: Project,
        run: AgentRun,
        ctx: AgentContext,
        compiled_graph: Any,
        graph_config: dict[str, dict[str, str]],
        runtime_context: Any,
        initial_payload: Any,
        auto_mode: bool,
    ) -> tuple[bool, str]:
        if project.id is None or run.id is None:
            raise RuntimeError("Project and run must be persisted before graph execution")
        project_pk = int(project.id)
        run_pk = int(run.id)

        payload: Any = initial_payload
        video_generation_skipped = False
        final_stage = "compose"
        saw_compose_stage = False
        while True:
            logger.debug(
                "[graph] run=%s ainvoke start payload_type=%s", run_pk, type(payload).__name__
            )
            result = await compiled_graph.ainvoke(payload, graph_config, context=runtime_context)
            logger.debug(
                "[graph] run=%s ainvoke returned result_type=%s", run_pk, type(result).__name__
            )
            if not isinstance(result, dict):
                logger.warning("[graph] run=%s result not dict, breaking", run_pk)
                break

            result_stage = result.get("current_stage")
            if isinstance(result_stage, str) and result_stage:
                final_stage = result_stage
                if result_stage.startswith("compose"):
                    saw_compose_stage = True

            if _video_generation_skipped_in_result(result):
                video_generation_skipped = True

            interrupts = result.get("__interrupt__") or []
            logger.debug(
                "[graph] run=%s interrupts_count=%s keys=%s",
                run_pk,
                len(interrupts),
                list(result.keys()),
            )
            if not interrupts:
                logger.debug("[graph] run=%s no interrupts, breaking", run_pk)
                break

            interrupt_value = getattr(interrupts[0], "value", None)
            gate_agent = None
            if isinstance(interrupt_value, dict):
                gate_agent = interrupt_value.get("gate")

            if not isinstance(gate_agent, str) or not gate_agent.strip():
                raise RuntimeError("LangGraph approval gate did not include a valid gate name")

            logger.debug(
                "[graph] run=%s interrupt gate=%s auto_mode=%s", run_pk, gate_agent, auto_mode
            )
            feedback = ""
            action = "approve"
            gate_name = gate_agent.strip()
            gate_modes = getattr(runtime_context, "gate_modes", set())
            if not auto_mode and gate_name not in gate_modes:
                feedback = (
                    await self._wait_for_confirm(
                        project_pk, run, gate_name,
                        agent_ctx=ctx, interrupt_data=interrupt_value,
                    )
                    or ""
                )
            else:
                await self._send_auto_approval_events(
                    project_pk, run, gate_name, agent_ctx=ctx
                )
            logger.debug(
                "[graph] run=%s resume with feedback=%r action=%s", run_pk, feedback, action
            )
            if feedback:
                action = "feedback"
            payload = Command(resume={"action": action, "feedback": feedback})

        await self.session.refresh(ctx.project)

        if saw_compose_stage and not video_generation_skipped and final_stage.startswith("compose"):
            blocking_clips = await collect_project_blocking_clips(self.session, ctx.project)
            project_video_url = getattr(ctx.project, "video_url", None)
            if not project_video_url or blocking_clips:
                reasons: list[str] = []
                if not project_video_url:
                    reasons.append("final project video_url is empty")
                if blocking_clips:
                    reasons.append(f"{len(blocking_clips)} blocking clips remain")
                raise RuntimeError(
                    "Compose finished without a usable final video: " + "; ".join(reasons)
                )

        ctx.project.status = "ready"
        self.session.add(ctx.project)
        await self.session.commit()

        return video_generation_skipped, final_stage

    async def _run_phase2_graph(
        self,
        *,
        project: Project,
        run: AgentRun,
        request: GenerateRequest,
        ctx: AgentContext,
        agent_name: str,
        auto_mode: bool,
        gate_modes: set[str] | None = None,
    ) -> tuple[bool, str]:
        if agent_name not in GRAPH_STAGE_FOR_AGENT:
            raise ValueError(f"Unsupported agent for graph execution: {agent_name}")
        if agent_name == "outline" and not self.settings.outline_enabled:
            agent_name = "plan"

        if agent_name == "review":
            latest_feedback = (ctx.user_feedback or request.notes or "").strip()
            if latest_feedback:
                ctx.user_feedback = latest_feedback

        start_stage = cast(Phase2Stage, GRAPH_STAGE_FOR_AGENT[agent_name])
        if agent_name == "outline" and (not self.settings.outline_enabled or project.outline_approved):
            start_stage = "plan_characters"
            agent_name = "plan"
        if project.id is None or run.id is None:
            raise RuntimeError("Project and run must be persisted before graph execution")
        graph_config = cast(Any, build_graph_config(run))
        thread_id = graph_config["configurable"]["thread_id"]
        if not run.thread_id:
            await self._set_run(run, thread_id=thread_id)
        runtime_context = build_phase2_runtime_context(
            orchestrator=self,
            agent_context=ctx,
            start_stage=start_stage,
            auto_mode=auto_mode,
            gate_modes=gate_modes,
        )
        initial_state = self._build_phase2_state(
            project_id=int(project.id),
            run_id=int(run.id),
            thread_id=graph_config["configurable"]["thread_id"],
            start_stage=start_stage,
        )

        async with build_postgres_checkpointer(self.settings.database_url) as checkpointer:
            compiled_graph = build_phase2_graph().compile(checkpointer=cast(Any, checkpointer))
            return await self._invoke_phase2_graph(
                project=project,
                run=run,
                ctx=ctx,
                compiled_graph=compiled_graph,
                graph_config=graph_config,
                runtime_context=runtime_context,
                initial_payload=initial_state,
                auto_mode=auto_mode,
            )

    async def resume_from_recovery(
        self,
        *,
        project_id: int,
        run_id: int,
        auto_mode: bool = False,
        gate_modes: set[str] | None = None,
    ) -> None:
        project = await self.session.get(Project, project_id)
        run = await self.session.get(AgentRun, run_id)
        if not project or not run:
            return

        recovery = await build_recovery_summary(
            session=self.session,
            database_url=self.settings.database_url,
            run=run,
        )
        resume_stage = cast(Phase2Stage, recovery.next_stage or recovery.current_stage)
        resume_agent = _resume_agent_for_stage(resume_stage)

        graph_config = cast(Any, build_graph_config(run))
        thread_id = graph_config["configurable"]["thread_id"]
        if not run.thread_id:
            await self._set_run(run, thread_id=thread_id)

        try:
            self._agent_index(resume_agent)
            await self._set_run(
                run,
                status="running",
                current_agent=_resume_agent_for_stage(resume_stage),
                progress=workflow_progress_for_stage(resume_stage),
                error=None,
            )

            ctx = self._build_agent_context(
                project=project,
                run=run,
                request=GenerateRequest(),
            )
            ctx.user_feedback = None

            await self.ws.send_event(
                project_id,
                {
                    "type": "run_started",
                    "data": {
                        "run_id": run_id,
                        "project_id": project_id,
                        "provider_snapshot": run.provider_snapshot,
                        "current_stage": resume_stage,
                        "stage": resume_stage,
                        "next_stage": recovery.next_stage,
                        "progress": workflow_progress_for_stage(resume_stage),
                        "current_agent": _resume_agent_for_stage(resume_stage),
                        "recovery_summary": recovery.model_dump(mode="json"),
                    },
                },
            )
            await self._log(
                run_id,
                agent="orchestrator",
                role="system",
                content=f"Resuming from checkpoint at {resume_stage}: {recovery!r}",
            )

            async with build_postgres_checkpointer(self.settings.database_url) as checkpointer:
                compiled_graph = build_phase2_graph().compile(checkpointer=cast(Any, checkpointer))
                resume_config = cast(
                    Any,
                    await build_stage_recovery_config(
                        compiled_graph,
                        run,
                        before_stage=recovery.next_stage or recovery.current_stage,
                    ),
                )
                runtime_context = build_phase2_runtime_context(
                    orchestrator=self,
                    agent_context=ctx,
                    start_stage=resume_stage,
                    auto_mode=auto_mode,
                    gate_modes=gate_modes or set(),
                )
                video_generation_skipped, final_stage = await self._invoke_phase2_graph(
                    project=project,
                    run=run,
                    ctx=ctx,
                    compiled_graph=compiled_graph,
                    graph_config=resume_config,
                    runtime_context=runtime_context,
                    initial_payload=None,
                    auto_mode=auto_mode,
                )

            await self._complete_run(project_id, run, run_id, final_stage, video_generation_skipped)
        except (RuntimeError, ValueError) as e:
            await self._handle_run_failure(project_id, run, run_id, e, context="Resume")
        finally:
            await self._cleanup_run(run_id)

    async def run_from_agent(
        self,
        *,
        project_id: int,
        run_id: int,
        request: GenerateRequest,
        agent_name: str,
        auto_mode: bool = False,
        gate_modes: set[str] | None = None,
        feedback_type: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> None:
        project = await self.session.get(Project, project_id)
        run = await self.session.get(AgentRun, run_id)
        if not project or not run:
            return

        try:
            if agent_name == "outline" and not self.settings.outline_enabled:
                agent_name = "plan"
            self._agent_index(agent_name)

            initial_stage = GRAPH_STAGE_FOR_AGENT[agent_name]
            if agent_name == "outline" and project.outline_approved:
                agent_name = "plan"
                initial_stage = GRAPH_STAGE_FOR_AGENT[agent_name]

            await self._set_run(
                run,
                status="running",
                current_agent=agent_name,
                progress=workflow_progress_for_stage(initial_stage),
                error=None,
            )
            await self.ws.send_event(
                project_id,
                {
                    "type": "run_started",
                    "data": {
                        "run_id": run_id,
                        "project_id": project_id,
                        "provider_snapshot": run.provider_snapshot,
                        "current_stage": initial_stage,
                        "stage": initial_stage,
                        "next_stage": next_production_stage(initial_stage),
                        "progress": workflow_progress_for_stage(initial_stage),
                        "current_agent": agent_name,
                    },
                },
            )
            await self._log(
                run_id,
                agent="orchestrator",
                role="system",
                content=f"Generate started from {agent_name}: {request!r}",
            )

            ctx = self._build_agent_context(project=project, run=run, request=request)

            # 初始化当前 run 已存在的用户反馈消息（避免后续确认不带反馈时误读历史反馈）
            res = await ctx.session.execute(
                select(AgentMessage.id)
                .where(AgentMessage.run_id == run.id)
                .where(AgentMessage.role == "user")
                .order_by(AgentMessage.created_at.desc())
                .limit(1)
            )
            self._last_user_feedback_id = res.scalar_one_or_none()

            if agent_name == "review":
                # 让后续 agent 能直接读取用户反馈（例如编剧需要遵循数量限制等）
                res = await ctx.session.execute(
                    select(AgentMessage)
                    .where(AgentMessage.run_id == run.id)
                    .where(AgentMessage.role == "user")
                    .order_by(AgentMessage.created_at.desc())
                    .limit(1)
                )
                msg = res.scalars().first()
                if msg and msg.content.strip():
                    ctx.user_feedback = msg.content.strip()
                elif request.notes and request.notes.strip():
                    ctx.user_feedback = request.notes.strip()

                ctx.feedback_type = feedback_type
                ctx.entity_type = entity_type
                ctx.entity_id = entity_id

                review_agent = self.agents[self._agent_index("review")]

                await self._set_run(run, current_agent=review_agent.name, progress=0.0)
                await self.ws.send_event(
                    project_id,
                    {
                        "type": "run_progress",
                        "data": {
                            "run_id": run_id,
                            "current_agent": review_agent.name,
                            "current_stage": GRAPH_STAGE_FOR_AGENT.get(review_agent.name, "review"),
                            "stage": GRAPH_STAGE_FOR_AGENT.get(review_agent.name, "review"),
                            "next_stage": _next_phase2_stage(
                                GRAPH_STAGE_FOR_AGENT.get(review_agent.name, "review")
                            ),
                            "progress": 0.0,
                        },
                    },
                )

                routing = await review_agent.run(ctx)
                start_agent = routing.get("start_agent") if isinstance(routing, dict) else None
                # 直接从 routing 读取 mode（review.py 已经解析好了）
                mode = "full"
                if isinstance(routing, dict):
                    m = routing.get("mode")
                    if isinstance(m, str) and m.strip() in ("incremental", "full"):
                        mode = m.strip()
                if not (isinstance(start_agent, str) and start_agent.strip()):
                    start_agent = "plan"
                agent_name = start_agent.strip()
                if agent_name == "outline" and not self.settings.outline_enabled:
                    agent_name = "plan"
                self._agent_index(agent_name)  # validate
                ctx.rerun_mode = mode
                await self._log(
                    run_id,
                    agent="orchestrator",
                    role="system",
                    content=f"Review routed to {agent_name} (mode={mode}): {routing!r}",
                )

            await self._cleanup_for_rerun(
                project_id, agent_name, mode=getattr(ctx, "rerun_mode", "full"),
                target_ids=getattr(ctx, "target_ids", None),
            )

            # 刷新 project 对象，因为 cleanup 可能修改了它
            await self.session.refresh(ctx.project)

            video_generation_skipped, final_stage = await self._run_phase2_graph(
                project=project,
                run=run,
                request=request,
                ctx=ctx,
                agent_name=agent_name,
                auto_mode=auto_mode,
                gate_modes=gate_modes,
            )

            await self._complete_run(project_id, run, run_id, final_stage, video_generation_skipped)
        except (RuntimeError, KeyError, ValueError) as e:
            await self._handle_run_failure(project_id, run, run_id, e, context="Run")
        finally:
            await self._cleanup_run(run_id)

    async def run(
        self, *, project_id: int, run_id: int, request: GenerateRequest, auto_mode: bool = False
    ) -> None:
        gate_modes = set(request.gate_modes) if request.gate_modes else None
        await self.run_from_agent(
            project_id=project_id,
            run_id=run_id,
            request=request,
            agent_name="outline" if self.settings.outline_enabled else "plan",
            auto_mode=auto_mode,
            gate_modes=gate_modes,
        )

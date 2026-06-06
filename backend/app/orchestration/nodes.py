from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import Send, interrupt

from app.agents.critic import CriticAgent
from app.agents.review_rules import ALLOWED_START_AGENTS
from .state import (
    Phase2RuntimeContext,
    Phase2State,
    next_production_stage,
    workflow_progress_for_stage,
)


_STAGE_ARTIFACT_KEYS: dict[str, str] = {
    "plan_outline": "stage:plan_outline",
    "plan_characters": "stage:plan_characters",
    "plan_shots": "stage:plan_shots",
    "render_characters": "stage:render_characters",
    "render_shots": "stage:render_shots",
    "compose_videos": "stage:compose_videos",
    "compose_merge": "stage:compose_merge",
    "add_audio": "stage:add_audio",
    "critique_character_images": "stage:critique_character_images",
    "critique_shot_images": "stage:critique_shot_images",
}

# Approval gate → the production stage it guards
_APPROVAL_FOR: dict[str, str] = {
    "outline_approval": "plan_outline",
    "characters_approval": "plan_characters",
    "shots_approval": "plan_shots",
    "character_images_approval": "render_characters",
    "shot_images_approval": "render_shots",
    "compose_approval": "compose_merge",
}

_START_AGENT_TO_STAGE: dict[str, str] = {
    "outline": "plan_outline",
    "plan": "plan_characters",
    "render": "render_characters",
    "compose": "compose_videos",
}

_STAGE_TO_AGENT: dict[str, str] = {
    "plan_outline": "outline",
    "plan_characters": "plan",
    "plan_shots": "plan",
    "render_characters": "render",
    "render_shots": "render",
    "compose_videos": "compose",
    "compose_merge": "compose",
    "add_audio": "compose",
}

_parallel_mode: bool = False


def set_parallel_mode(enabled: bool) -> None:
    global _parallel_mode
    _parallel_mode = enabled


def _agent_name_for_stage(stage: str) -> str:
    return _STAGE_TO_AGENT.get(stage, stage.split("_")[0])


def _stage_key(stage: str) -> str:
    return _STAGE_ARTIFACT_KEYS.get(stage, f"stage:{stage}")


def _completeness_stages() -> set[str]:
    """Production stages that require artifact completeness validation."""
    return {"render_characters", "render_shots", "compose_videos"}


def _should_skip_stage(state: Phase2State, stage: str) -> bool:
    artifact_lineage = state.get("artifact_lineage") or []
    return _stage_key(stage) in artifact_lineage


async def _check_stage_completeness(
    stage: str,
    state: Phase2State,
    runtime: Runtime[Phase2RuntimeContext],
) -> dict[str, Any] | None:
    """Verify all entities have required artifacts for this stage.

    Queries the database to count entities missing required artifacts.
    Returns a warning dict if incomplete, or None if all complete.

    Checked artifacts per stage:
      - render_characters -> Character.image_url
      - render_shots      -> Shot.image_url
      - compose_videos    -> Shot.video_url
    """
    if stage not in _completeness_stages():
        return None

    from sqlmodel import func, select

    from app.models.project import Character, Shot

    session = runtime.context.orchestrator.session
    project_id = state["project_id"]

    if stage == "render_characters":
        entity_label = "characters"
        artifact_label = "image_url"
        total_q = select(func.count()).select_from(Character).where(
            Character.project_id == project_id
        )
        missing_q = select(func.count()).select_from(Character).where(
            Character.project_id == project_id,
            Character.image_url.is_(None),
        )
    elif stage == "render_shots":
        entity_label = "shots"
        artifact_label = "image_url"
        total_q = select(func.count()).select_from(Shot).where(
            Shot.project_id == project_id
        )
        missing_q = select(func.count()).select_from(Shot).where(
            Shot.project_id == project_id,
            Shot.image_url.is_(None),
        )
    elif stage == "compose_videos":
        entity_label = "shots"
        artifact_label = "video_url"
        total_q = select(func.count()).select_from(Shot).where(
            Shot.project_id == project_id
        )
        missing_q = select(func.count()).select_from(Shot).where(
            Shot.project_id == project_id,
            Shot.video_url.is_(None),
        )
    else:
        return None

    total = (await session.execute(total_q)).scalar_one()
    missing = (await session.execute(missing_q)).scalar_one()

    if total == 0:
        return None

    if missing == 0:
        return None

    detail = f"{missing}/{total} {entity_label} missing {artifact_label}"
    return {
        "stage": stage,
        "missing_count": missing,
        "total": total,
        "detail": detail,
    }


def _is_video_provider_invalid(run_snapshot: dict[str, Any] | None) -> bool:
    if not isinstance(run_snapshot, dict):
        return False
    video_snapshot = run_snapshot.get("video")
    if not isinstance(video_snapshot, dict):
        return False
    return video_snapshot.get("valid") is False


def _get_run_provider_snapshot(agent_ctx: Any) -> dict[str, Any] | None:
    if not hasattr(agent_ctx, "run"):
        return None
    run = getattr(agent_ctx, "run")
    return getattr(run, "provider_snapshot", None)


async def _run_sub_stage(
    state: Phase2State,
    runtime: Runtime[Phase2RuntimeContext],
    *,
    stage: str,
    method_name: str,
) -> dict[str, Any]:
    """Run a sub-stage of an agent and emit progress."""
    agent_ctx = runtime.context.agent_context
    if stage == "compose_videos" and _is_video_provider_invalid(
        _get_run_provider_snapshot(agent_ctx)
    ):
        return {
            "current_stage": stage,
            "stage_history": [stage],
            "artifact_lineage": [_stage_key(stage), _stage_key("compose_merge")],
            "video_generation_skipped": True,
            "route_stage": "__end__",
        }

    if stage == "compose_merge" and state.get("video_generation_skipped"):
        return {
            "current_stage": stage,
            "stage_history": [stage],
            "artifact_lineage": [_stage_key(stage)],
            "video_generation_skipped": True,
            "route_stage": "__end__",
        }

    if stage == "add_audio" and state.get("video_generation_skipped"):
        return {
            "current_stage": stage,
            "stage_history": [stage],
            "artifact_lineage": [_stage_key(stage)],
            "video_generation_skipped": True,
            "route_stage": "__end__",
        }

    if _should_skip_stage(state, stage):
        return {"current_stage": stage}

    orchestrator = runtime.context.orchestrator
    progress = workflow_progress_for_stage(stage, within_stage=0.0)
    agent_name = _agent_name_for_stage(stage)
    if stage == "plan_outline" and state.get("approval_feedback"):
        agent_ctx.user_feedback = state.get("approval_feedback")
    await orchestrator.set_run_state(
        agent_ctx.run,
        current_agent=agent_name,
        progress=progress,
    )
    await orchestrator.ws.send_event(
        agent_ctx.project.id,
        {
            "type": "run_progress",
            "data": {
                "run_id": agent_ctx.run.id,
                "current_agent": agent_name,
                "current_stage": stage,
                "stage": stage,
                "next_stage": next_production_stage(stage),
                "progress": progress,
            },
        },
    )

    agent = orchestrator.get_agent(agent_name)
    method = getattr(agent, method_name)
    await method(agent_ctx)

    # --- Stage completeness assertion ---
    completeness_warning = await _check_stage_completeness(stage, state, runtime)
    if completeness_warning is not None:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "Stage %s incomplete: %s",
            stage,
            completeness_warning["detail"],
        )
        await orchestrator.ws.send_event(
            agent_ctx.project.id,
            {
                "type": "stage_completeness_warning",
                "data": completeness_warning,
            },
        )

    initial_return = {
        "current_stage": stage,
        "stage_history": [stage],
        "artifact_lineage": [_stage_key(stage)],
    }
    if completeness_warning is not None:
        initial_return["completeness_warnings"] = [completeness_warning]
    return initial_return


# ---------------------------------------------------------------------------
# Approval helpers
# ---------------------------------------------------------------------------


def _approval_result(
    *,
    approval_stage: str,
    history_key: str,
    next_stage: str,
    feedback: str,
) -> dict[str, Any]:
    review_requested = bool(feedback)
    return {
        "current_stage": approval_stage,
        "approval_history": [history_key],
        "approval_feedback": feedback,
        "review_requested": review_requested,
        "route_stage": "review" if review_requested else next_stage,
    }


def _auto_approval_result(
    *, approval_stage: str, history_key: str, next_stage: str
) -> dict[str, Any]:
    return {
        "current_stage": approval_stage,
        "approval_history": [history_key],
        "approval_feedback": "",
        "review_requested": False,
        "route_stage": next_stage,
    }


async def _manual_approval_node(
    runtime: Runtime[Phase2RuntimeContext],
    *,
    approval_stage: str,
    history_key: str,
    gate: str,
    message: str,
    next_stage: str,
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    orchestrator = runtime.context.orchestrator

    approval_progress = workflow_progress_for_stage(approval_stage)

    await orchestrator.set_run_state(
        agent_ctx.run,
        current_agent=gate,
        progress=approval_progress,
    )
    await orchestrator.ws.send_event(
        agent_ctx.project.id,
        {
            "type": "run_progress",
            "data": {
                "run_id": agent_ctx.run.id,
                "current_agent": gate,
                "current_stage": approval_stage,
                "stage": approval_stage,
                "next_stage": next_stage,
                "progress": approval_progress,
            },
        },
    )

    if runtime.context.auto_mode:
        return _auto_approval_result(
            approval_stage=approval_stage,
            history_key=history_key,
            next_stage=next_stage,
        )

    resume_value = interrupt({"gate": gate, "message": message})
    feedback = _normalize_resume_value(resume_value)
    return _approval_result(
        approval_stage=approval_stage,
        history_key=history_key,
        next_stage=next_stage,
        feedback=feedback,
    )


def _build_approval_message(agent_ctx: Any, fallback: str) -> str:
    ci = agent_ctx.completion_info
    if ci:
        parts = [ci.completed]
        if ci.details:
            parts.append(ci.details)
        if ci.next:
            parts.append(ci.next)
        if ci.question:
            parts.append(ci.question)
        return "\n".join(parts)
    return fallback


# ---------------------------------------------------------------------------
# Production nodes
# ---------------------------------------------------------------------------


async def plan_outline_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(state, runtime, stage="plan_outline", method_name="run_outline")


async def plan_characters_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(
        state, runtime, stage="plan_characters", method_name="run_characters"
    )


async def plan_shots_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(state, runtime, stage="plan_shots", method_name="run_shots")


async def render_characters_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(
        state, runtime, stage="render_characters", method_name="run_characters"
    )


async def render_shots_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(state, runtime, stage="render_shots", method_name="run_shots")


async def compose_videos_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(state, runtime, stage="compose_videos", method_name="run_videos")


async def compose_merge_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    return await _run_sub_stage(state, runtime, stage="compose_merge", method_name="run_merge")


async def add_audio_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    """Add TTS dubbing and BGM to shot videos and final merged video."""
    return await _run_sub_stage(state, runtime, stage="add_audio", method_name="run_add_audio")


# ---------------------------------------------------------------------------
# Approval nodes
# ---------------------------------------------------------------------------


async def outline_approval_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    message = _build_approval_message(agent_ctx, "故事大纲已生成，请确认是否继续角色设计。")
    result = await _manual_approval_node(
        runtime,
        approval_stage="outline_approval",
        history_key="plan_outline",
        gate="outline",
        message=message,
        next_stage="plan_characters",
    )
    if result.get("review_requested"):
        result["route_stage"] = "plan_outline"
        result["review_requested"] = False
        return result

    await agent_ctx.session.refresh(agent_ctx.project)
    agent_ctx.project.outline_approved = True
    agent_ctx.session.add(agent_ctx.project)
    await agent_ctx.session.commit()
    await agent_ctx.ws.send_event(
        agent_ctx.project.id,
        {
            "type": "project_updated",
            "data": {
                "project": {
                    "id": agent_ctx.project.id,
                    "outline_approved": True,
                }
            },
        },
    )
    return result


async def characters_approval_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    message = _build_approval_message(agent_ctx, "角色设定已生成，请确认是否继续创建分镜。")
    return await _manual_approval_node(
        runtime,
        approval_stage="characters_approval",
        history_key="plan_characters",
        gate="plan",
        message=message,
        next_stage="plan_shots",
    )


async def shots_approval_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    message = _build_approval_message(agent_ctx, "分镜脚本已生成，请确认是否继续进入渲染阶段。")
    return await _manual_approval_node(
        runtime,
        approval_stage="shots_approval",
        history_key="plan_shots",
        gate="plan",
        message=message,
        next_stage="render_characters",
    )


async def character_images_approval_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    message = _build_approval_message(
        agent_ctx, "角色形象图已渲染完成，请确认是否继续渲染分镜画面。"
    )
    return await _manual_approval_node(
        runtime,
        approval_stage="character_images_approval",
        history_key="render_characters",
        gate="render",
        message=message,
        next_stage="critique_character_images",
    )


async def shot_images_approval_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    if _is_video_provider_invalid(_get_run_provider_snapshot(agent_ctx)):
        return _auto_approval_result(
            approval_stage="shot_images_approval",
            history_key="render_shots",
            next_stage="critique_shot_images",
        )

    message = _build_approval_message(
        agent_ctx, "分镜画面已渲染完成，请确认是否继续进入视频合成阶段。"
    )
    return await _manual_approval_node(
        runtime,
        approval_stage="shot_images_approval",
        history_key="render_shots",
        gate="render",
        message=message,
        next_stage="critique_shot_images",
    )


async def compose_approval_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    agent_ctx = runtime.context.agent_context
    message = _build_approval_message(agent_ctx, "视频合成已完成，请确认最终效果。")
    return await _manual_approval_node(
        runtime,
        approval_stage="compose_approval",
        history_key="compose_merge",
        gate="compose",
        message=message,
        next_stage="__end__",
    )


# ======================================================================
# Critique nodes
# ======================================================================


async def critique_character_images_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    """Run critic review on character images after approval."""
    agent_ctx = runtime.context.agent_context
    settings = agent_ctx.settings

    # If critique is disabled, skip straight to the next stage
    if not settings.critique_enabled:
        return {
            "current_stage": "critique_character_images",
            "stage_history": ["critique_character_images"],
            "artifact_lineage": [_stage_key("critique_character_images")],
            "critique_scores": {},
            "route_stage": "render_shots",
        }

    # Check max rounds
    critique_round = state.get("critique_round", 0)
    if isinstance(critique_round, int) and critique_round >= settings.critique_max_rounds:
        return {
            "current_stage": "critique_character_images",
            "stage_history": ["critique_character_images"],
            "artifact_lineage": [_stage_key("critique_character_images")],
            "critique_scores": state.get("critique_scores", {}),
            "route_stage": "render_shots",
        }

    orchestrator = runtime.context.orchestrator
    progress = workflow_progress_for_stage("critique_character_images", within_stage=0.0)
    await orchestrator.set_run_state(
        agent_ctx.run,
        current_agent="critic",
        progress=progress,
    )
    await orchestrator.ws.send_event(
        agent_ctx.project.id,
        {
            "type": "run_progress",
            "data": {
                "run_id": agent_ctx.run.id,
                "current_agent": "critic",
                "current_stage": "critique_character_images",
                "stage": "critique_character_images",
                "next_stage": "render_shots",
                "progress": progress,
            },
        },
    )

    critic = CriticAgent()
    result = await critic.run_character_review(agent_ctx)

    should_regenerate = result.get("should_regenerate", False)

    # Determine route: if score below threshold and within max rounds, regenerate
    if should_regenerate and critique_round < settings.critique_max_rounds - 1:
        # Route back to render_characters for regeneration
        next_route = "render_characters"
        new_round = critique_round + 1
    else:
        # Either quality is OK or we've hit max rounds
        next_route = "render_shots"
        new_round = critique_round

    return {
        "current_stage": "critique_character_images",
        "stage_history": ["critique_character_images"],
        "artifact_lineage": [_stage_key("critique_character_images")],
        "critique_scores": result.get("scores", {}),
        "critique_round": new_round,
        "route_stage": next_route,
    }


async def critique_shot_images_node(
    state: Phase2State, runtime: Runtime[Phase2RuntimeContext]
) -> dict[str, Any]:
    """Run critic review on shot images after approval."""
    agent_ctx = runtime.context.agent_context
    settings = agent_ctx.settings

    # If critique is disabled, skip straight to the next stage
    if not settings.critique_enabled:
        return {
            "current_stage": "critique_shot_images",
            "stage_history": ["critique_shot_images"],
            "artifact_lineage": [_stage_key("critique_shot_images")],
            "critique_scores": {},
            "route_stage": "compose_videos",
        }

    # Check max rounds
    critique_round = state.get("critique_round", 0)
    if isinstance(critique_round, int) and critique_round >= settings.critique_max_rounds:
        return {
            "current_stage": "critique_shot_images",
            "stage_history": ["critique_shot_images"],
            "artifact_lineage": [_stage_key("critique_shot_images")],
            "critique_scores": state.get("critique_scores", {}),
            "route_stage": "compose_videos",
        }

    orchestrator = runtime.context.orchestrator
    progress = workflow_progress_for_stage("critique_shot_images", within_stage=0.0)
    await orchestrator.set_run_state(
        agent_ctx.run,
        current_agent="critic",
        progress=progress,
    )
    await orchestrator.ws.send_event(
        agent_ctx.project.id,
        {
            "type": "run_progress",
            "data": {
                "run_id": agent_ctx.run.id,
                "current_agent": "critic",
                "current_stage": "critique_shot_images",
                "stage": "critique_shot_images",
                "next_stage": "compose_videos",
                "progress": progress,
            },
        },
    )

    critic = CriticAgent()
    result = await critic.run_shot_review(agent_ctx)

    should_regenerate = result.get("should_regenerate", False)

    # Determine route: if score below threshold and within max rounds, regenerate
    if should_regenerate and critique_round < settings.critique_max_rounds - 1:
        next_route = "render_shots"
        new_round = critique_round + 1
    else:
        next_route = "compose_videos"
        new_round = critique_round

    return {
        "current_stage": "critique_shot_images",
        "stage_history": ["critique_shot_images"],
        "artifact_lineage": [_stage_key("critique_shot_images")],
        "critique_scores": result.get("scores", {}),
        "critique_round": new_round,
        "route_stage": next_route,
    }


def route_after_critique_character_images(state: Phase2State) -> str:
    """Route after character image critique.

    Uses route_stage set by the critique node:
    - 'render_characters' if score < threshold and within max rounds
    - 'render_shots' if quality OK or max rounds exceeded (serial)
    - 'compose_videos' if quality OK or max rounds exceeded (parallel)
    """
    route = state.get("route_stage")
    if route:
        return route
    if _parallel_mode:
        return "compose_videos"
    return "render_shots"


def route_after_critique_shot_images(state: Phase2State) -> str:
    """Route after shot image critique.

    Uses route_stage set by the critique node:
    - 'render_shots' if score < threshold and within max rounds
    - 'compose_videos' if quality OK or max rounds exceeded
    """
    route = state.get("route_stage")
    if route:
        return route
    return "compose_videos"


# ---------------------------------------------------------------------------
# Review node
# ---------------------------------------------------------------------------


async def review_node(state: Phase2State, runtime: Runtime[Phase2RuntimeContext]) -> dict[str, Any]:
    orchestrator = runtime.context.orchestrator
    agent_ctx = runtime.context.agent_context

    review_agent = orchestrator.get_agent("review")

    approval_feedback = state.get("approval_feedback", "")
    if approval_feedback:
        agent_ctx.user_feedback = approval_feedback

    routing = await review_agent.run(agent_ctx)
    start_agent = routing.get("start_agent") if isinstance(routing, dict) else None
    mode = "full"
    target_ids = None
    if isinstance(routing, dict):
        maybe_mode = routing.get("mode")
        if isinstance(maybe_mode, str) and maybe_mode.strip() in {"incremental", "full"}:
            mode = maybe_mode.strip()
        target_ids = routing.get("target_ids")

    if not (isinstance(start_agent, str) and start_agent.strip()):
        start_agent = "plan"
    start_agent = start_agent.strip()
    if start_agent not in ALLOWED_START_AGENTS:
        start_agent = "plan"

    agent_ctx.rerun_mode = mode
    if target_ids is not None:
        agent_ctx.target_ids = target_ids

    await orchestrator.cleanup_for_rerun(
        agent_ctx.project.id,
        start_agent,
        mode=mode,
    )
    await orchestrator.session.refresh(agent_ctx.project)

    return {
        "current_stage": "review",
        "route_stage": _START_AGENT_TO_STAGE.get(start_agent, "plan_characters"),
        "route_mode": mode,
        "review_requested": False,
        "approval_history": [f"review:{start_agent}:{mode}"],
    }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def route_from_start(state: Phase2State) -> str:
    return state.get("current_stage") or "plan_outline"


def _route_after_approval(state: Phase2State, *, default_next: str) -> str:
    route = state.get("route_stage")
    if route:
        return route
    if state.get("review_requested"):
        return "review"
    return default_next


def route_after_outline_approval(state: Phase2State) -> str:
    return _route_after_approval(state, default_next="plan_characters")


def route_after_characters_approval(state: Phase2State) -> str:
    return _route_after_approval(state, default_next="plan_shots")


def route_after_shots_approval(state: Phase2State) -> str:
    return _route_after_approval(state, default_next="render_characters")


def route_shots_approval_parallel(state: Phase2State) -> str | list[Send]:
    route = state.get("route_stage")
    if route:
        return route
    if state.get("review_requested"):
        return "review"
    return [
        Send("render_characters", state),
        Send("render_shots_parallel", state),
    ]


def route_after_character_images_approval(state: Phase2State) -> str:
    return _route_after_approval(state, default_next="critique_character_images")


def route_after_shot_images_approval(state: Phase2State) -> str:
    return _route_after_approval(state, default_next="critique_shot_images")


def route_after_compose_videos(state: Phase2State) -> str:
    if state.get("video_generation_skipped") or state.get("route_stage") == "__end__":
        return "__end__"
    return "compose_merge"


def route_after_compose_merge(state: Phase2State) -> str:
    if state.get("video_generation_skipped") or state.get("route_stage") == "__end__":
        return "__end__"
    return "add_audio"


def route_after_compose_approval(state: Phase2State) -> str:
    return _route_after_approval(state, default_next="__end__")


def route_after_review(state: Phase2State) -> str:
    return state.get("route_stage") or "plan_characters"


def _normalize_resume_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        maybe_action = value.get("action")
        maybe_feedback = value.get("feedback")
        if isinstance(maybe_feedback, str) and maybe_feedback.strip():
            return maybe_feedback.strip()
        if isinstance(maybe_action, str) and maybe_action == "approve":
            return ""
        if isinstance(maybe_action, str) and maybe_action == "reject":
            return value.get("reason", "") if isinstance(value.get("reason"), str) else ""
        maybe_text = value.get("text")
        if isinstance(maybe_text, str):
            return maybe_text.strip()
    return str(value).strip()

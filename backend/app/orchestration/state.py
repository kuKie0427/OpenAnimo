from __future__ import annotations

from dataclasses import dataclass, field
from operator import add
from typing import Annotated, Any, Literal, TypedDict


Phase2Stage = Literal[
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
]

# Ordered sequence of production stages (excludes approval gates).
PRODUCTION_STAGE_SEQUENCE: tuple[str, ...] = (
    "plan_outline",
    "plan_characters",
    "plan_shots",
    "render_characters",
    "render_shots",
    "compose_videos",
    "compose_merge",
    "add_audio",
)


# Approval gate → the production stage it comes right after
_APPROVAL_TO_PRODUCED_STAGE: dict[str, str] = {
    "outline_approval": "plan_outline",
    "characters_approval": "plan_characters",
    "shots_approval": "plan_shots",
    "character_images_approval": "render_characters",
    "shot_images_approval": "render_shots",
    "compose_approval": "add_audio",
}

_CRITIQUE_TO_PRODUCED_STAGE: dict[str, str] = {
    "critique_character_images": "render_characters",
    "critique_shot_images": "render_shots",
}


def _resolve_base_stage(stage: str) -> str | None:
    """Map any stage (production or approval or critique) to its production stage."""
    if stage in PRODUCTION_STAGE_SEQUENCE:
        return stage
    base = _APPROVAL_TO_PRODUCED_STAGE.get(stage)
    if base is not None:
        return base
    return _CRITIQUE_TO_PRODUCED_STAGE.get(stage)


def next_production_stage(stage: str | None) -> str | None:
    if not isinstance(stage, str):
        return None
    base = _resolve_base_stage(stage)
    if base is None:
        return None
    next_index = PRODUCTION_STAGE_SEQUENCE.index(base) + 1
    if next_index >= len(PRODUCTION_STAGE_SEQUENCE):
        return None
    return PRODUCTION_STAGE_SEQUENCE[next_index]


def workflow_progress_for_stage(stage: str, *, within_stage: float = 0.0) -> float:
    base = _resolve_base_stage(stage)
    if base is None:
        return 0.0

    clamped_within = max(0.0, min(within_stage, 1.0))
    stage_index = PRODUCTION_STAGE_SEQUENCE.index(base)
    total = len(PRODUCTION_STAGE_SEQUENCE)
    return min((stage_index + clamped_within) / total, 1.0)


class Phase2State(TypedDict, total=False):
    project_id: int
    run_id: int
    thread_id: str
    current_stage: str
    next_stage: str
    stage_history: Annotated[list[str], add]
    approval_history: Annotated[list[str], add]
    artifact_lineage: Annotated[list[str], add]
    approval_feedback: str
    review_requested: bool
    route_stage: str
    route_mode: str
    video_generation_skipped: bool
    critique_scores: dict
    critique_round: int
    completeness_warnings: Annotated[list[dict[str, Any]], add]


ALL_GATES = frozenset({
    "outline", "characters", "shots",
    "character_images", "shot_images", "compose",
    "critique_characters", "critique_shots",
})


@dataclass(slots=True)
class Phase2RuntimeContext:
    orchestrator: Any
    agent_context: Any
    start_stage: Phase2Stage = "plan_outline"
    auto_mode: bool = False       # 保留向后兼容（老 API 不传 gate_modes 时使用）
    gate_modes: set[str] = field(default_factory=set)  # 应自动通过的闸门名称集合

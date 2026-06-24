from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.agent_run import AgentRun
from app.schemas.project import ProviderResolution

INITIAL_GENERATION_BLOCKING_MODALITIES = ("text", "image")


@dataclass(frozen=True)
class GenerationEntryDecision:
    kind: Literal["active_conflict", "recoverable_conflict", "provider_blocked", "start"]
    run: AgentRun | None = None


def has_initial_generation_blockers(provider_resolution: ProviderResolution) -> bool:
    return any(
        not getattr(provider_resolution, modality).valid
        for modality in INITIAL_GENERATION_BLOCKING_MODALITIES
    )


def decide_generation_entry(
    *,
    active_run: AgentRun | None,
    resumable_run: AgentRun | None,
    provider_resolution: ProviderResolution,
) -> GenerationEntryDecision:
    if active_run is not None:
        return GenerationEntryDecision(kind="active_conflict", run=active_run)

    if resumable_run is not None:
        return GenerationEntryDecision(kind="recoverable_conflict", run=resumable_run)

    if has_initial_generation_blockers(provider_resolution):
        return GenerationEntryDecision(kind="provider_blocked")

    return GenerationEntryDecision(kind="start")

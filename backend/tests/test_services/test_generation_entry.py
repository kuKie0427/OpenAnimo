from __future__ import annotations

from app.schemas.project import ProjectProviderEntry, ProviderResolution
from app.services.generation_entry import decide_generation_entry, has_initial_generation_blockers


def _provider_entry(*, valid: bool) -> ProjectProviderEntry:
    return ProjectProviderEntry(
        selected_key="openai",
        source="default",
        resolved_key="openai" if valid else None,
        valid=valid,
        reason_code=None if valid else "provider_missing_credentials",
        reason_message=None if valid else "missing credentials",
    )


def _provider_resolution(*, text_valid: bool = True, image_valid: bool = True, video_valid: bool = True) -> ProviderResolution:
    return ProviderResolution(
        valid=text_valid and image_valid and video_valid,
        text=_provider_entry(valid=text_valid),
        image=_provider_entry(valid=image_valid),
        video=_provider_entry(valid=video_valid),
    )


def test_has_initial_generation_blockers_ignores_video_only_failure() -> None:
    resolution = _provider_resolution(video_valid=False)

    assert has_initial_generation_blockers(resolution) is False


def test_has_initial_generation_blockers_when_text_invalid() -> None:
    resolution = _provider_resolution(text_valid=False)

    assert has_initial_generation_blockers(resolution) is True


def test_decide_generation_entry_prefers_active_conflict() -> None:
    active_run = object()
    decision = decide_generation_entry(
        active_run=active_run,
        resumable_run=object(),
        provider_resolution=_provider_resolution(text_valid=False),
    )

    assert decision.kind == "active_conflict"
    assert decision.run is active_run


def test_decide_generation_entry_returns_recoverable_conflict() -> None:
    resumable_run = object()
    decision = decide_generation_entry(
        active_run=None,
        resumable_run=resumable_run,
        provider_resolution=_provider_resolution(text_valid=False),
    )

    assert decision.kind == "recoverable_conflict"
    assert decision.run is resumable_run


def test_decide_generation_entry_returns_provider_blocked_without_conflict() -> None:
    decision = decide_generation_entry(
        active_run=None,
        resumable_run=None,
        provider_resolution=_provider_resolution(image_valid=False),
    )

    assert decision.kind == "provider_blocked"
    assert decision.run is None


def test_decide_generation_entry_allows_start_when_required_modalities_are_valid() -> None:
    decision = decide_generation_entry(
        active_run=None,
        resumable_run=None,
        provider_resolution=_provider_resolution(video_valid=False),
    )

    assert decision.kind == "start"
    assert decision.run is None

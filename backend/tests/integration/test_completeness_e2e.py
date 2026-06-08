"""E2E tests for _check_stage_completeness with real database entities.

Unlike test_stage_completeness.py (unit tests with MagicMock'd sessions),
these tests create real DB entities via factories and run SQL queries against
an actual SQLite test database.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.orchestration.nodes import _check_stage_completeness
from tests.factories import create_project, create_character, create_shot


@pytest.mark.asyncio
async def test_e2e_sc01_all_characters_have_image_url(test_session):
    """E2E-SC-01: All characters have image_url → no warning."""
    project = await create_project(test_session, title="E2E-SC-01")
    assert project.id is not None

    # Create 5 characters, all with image_url
    for i in range(5):
        await create_character(
            test_session,
            project_id=project.id,
            name=f"Char-{i}",
            image_url=f"http://test.com/char-{i}.png",
        )

    runtime = MagicMock()
    runtime.context.orchestrator.session = test_session
    state = {"project_id": project.id}

    result = await _check_stage_completeness(
        "render_characters", state, runtime  # type: ignore[arg-type]
    )
    assert result is None


@pytest.mark.asyncio
async def test_e2e_sc02_partial_characters_missing_image_url(test_session):
    """E2E-SC-02: 2/5 characters missing image_url → warning dict."""
    project = await create_project(test_session, title="E2E-SC-02")
    assert project.id is not None

    # Create 5 characters: 3 with image_url, 2 without
    for i in range(3):
        await create_character(
            test_session,
            project_id=project.id,
            name=f"Char-{i}",
            image_url=f"http://test.com/char-{i}.png",
        )
    for i in range(3, 5):
        await create_character(
            test_session,
            project_id=project.id,
            name=f"Char-{i}",
            image_url=None,
        )

    runtime = MagicMock()
    runtime.context.orchestrator.session = test_session
    state = {"project_id": project.id}

    result = await _check_stage_completeness(
        "render_characters", state, runtime  # type: ignore[arg-type]
    )
    assert result is not None
    assert result["stage"] == "render_characters"
    assert result["missing_count"] == 2
    assert result["total"] == 5


@pytest.mark.asyncio
async def test_e2e_sc03_partial_shots_missing_video_url(test_session):
    """E2E-SC-03: 3/5 shots missing video_url → warning dict."""
    project = await create_project(test_session, title="E2E-SC-03")
    assert project.id is not None

    # Create 5 shots: 2 with video_url, 3 without
    for i in range(2):
        await create_shot(
            test_session,
            project_id=project.id,
            order=i + 1,
            image_url=f"http://test.com/shot-{i}.png",
            video_url=f"http://test.com/shot-{i}.mp4",
        )
    for i in range(2, 5):
        await create_shot(
            test_session,
            project_id=project.id,
            order=i + 1,
            image_url=f"http://test.com/shot-{i}.png",
            video_url=None,
        )

    runtime = MagicMock()
    runtime.context.orchestrator.session = test_session
    state = {"project_id": project.id}

    result = await _check_stage_completeness(
        "compose_videos", state, runtime  # type: ignore[arg-type]
    )
    assert result is not None
    assert result["stage"] == "compose_videos"
    assert result["missing_count"] == 3
    assert result["total"] == 5

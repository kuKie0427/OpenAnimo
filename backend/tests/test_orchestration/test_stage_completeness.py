"""Tests for stage-level completeness assertions in nodes.py."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.orchestration.nodes import _check_stage_completeness, _completeness_stages


class TestCompletenessStages:
    def test_render_and_compose_stages_are_checked(self):
        stages = _completeness_stages()
        assert "render_characters" in stages
        assert "render_shots" in stages
        assert "compose_videos" in stages

    def test_plan_stages_are_not_checked(self):
        stages = _completeness_stages()
        assert "plan_outline" not in stages
        assert "plan_characters" not in stages
        assert "plan_shots" not in stages


class TestCheckStageCompleteness:
    @pytest.fixture
    def mock_runtime(self):
        """Create a mock runtime with orchestrator.session for DB access."""
        runtime = MagicMock()
        runtime.context.orchestrator.session = AsyncMock()
        return runtime

    @pytest.fixture
    def state(self):
        return {"project_id": 1}

    @pytest.mark.asyncio
    async def test_all_characters_have_images_returns_none(self, mock_runtime, state):
        """When all characters have image_url, no warning."""
        session = mock_runtime.context.orchestrator.session
        session.execute = AsyncMock()
        session.execute.side_effect = [
            MagicMock(scalar_one=MagicMock(return_value=5)),
            MagicMock(scalar_one=MagicMock(return_value=0)),
        ]
        result = await _check_stage_completeness("render_characters", state, mock_runtime)
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_character_images_returns_warning(self, mock_runtime, state):
        """When 2/5 characters missing image_url, return warning dict."""
        session = mock_runtime.context.orchestrator.session
        session.execute = AsyncMock()
        session.execute.side_effect = [
            MagicMock(scalar_one=MagicMock(return_value=5)),
            MagicMock(scalar_one=MagicMock(return_value=2)),
        ]
        result = await _check_stage_completeness("render_characters", state, mock_runtime)
        assert result is not None
        assert result["stage"] == "render_characters"
        assert result["missing_count"] == 2
        assert result["total"] == 5
        assert "2/5" in result["detail"]

    @pytest.mark.asyncio
    async def test_all_shots_have_images_returns_none(self, mock_runtime, state):
        session = mock_runtime.context.orchestrator.session
        session.execute = AsyncMock()
        session.execute.side_effect = [
            MagicMock(scalar_one=MagicMock(return_value=10)),
            MagicMock(scalar_one=MagicMock(return_value=0)),
        ]
        result = await _check_stage_completeness("render_shots", state, mock_runtime)
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_shot_videos_returns_warning(self, mock_runtime, state):
        session = mock_runtime.context.orchestrator.session
        session.execute = AsyncMock()
        session.execute.side_effect = [
            MagicMock(scalar_one=MagicMock(return_value=10)),
            MagicMock(scalar_one=MagicMock(return_value=1)),
        ]
        result = await _check_stage_completeness("compose_videos", state, mock_runtime)
        assert result is not None
        assert result["stage"] == "compose_videos"
        assert result["missing_count"] == 1
        assert "video_url" in result["detail"]

    @pytest.mark.asyncio
    async def test_non_production_stage_returns_none(self, mock_runtime, state):
        """plan_outline is not a production stage — always returns None."""
        result = await _check_stage_completeness("plan_outline", state, mock_runtime)
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_entities_returns_none(self, mock_runtime, state):
        """Project with no characters yet should not trigger warning."""
        session = mock_runtime.context.orchestrator.session
        session.execute = AsyncMock()
        session.execute.side_effect = [
            MagicMock(scalar_one=MagicMock(return_value=0)),
            MagicMock(scalar_one=MagicMock(return_value=0)),
        ]
        result = await _check_stage_completeness("render_characters", state, mock_runtime)
        assert result is None

    @pytest.mark.asyncio
    async def test_edge_case_all_shots_videos_missing(self, mock_runtime, state):
        """All 10 shots missing video_url — full warning."""
        session = mock_runtime.context.orchestrator.session
        session.execute = AsyncMock()
        session.execute.side_effect = [
            MagicMock(scalar_one=MagicMock(return_value=10)),
            MagicMock(scalar_one=MagicMock(return_value=10)),
        ]
        result = await _check_stage_completeness("compose_videos", state, mock_runtime)
        assert result is not None
        assert result["missing_count"] == 10
        assert "10/10" in result["detail"]

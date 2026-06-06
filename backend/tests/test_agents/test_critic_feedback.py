"""Tests for critique feedback injection into render prompts."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.orchestration.nodes import _compile_critique_feedback
from app.agents.render import RenderAgent
from app.agents.base import AgentContext


class TestCompileCritiqueFeedback:
    def test_compile_character_feedback(self):
        scores = {
            "1": {"issues": ["面部比例不对"], "suggestions": ["调大眼睛间距", "缩小嘴巴"]},
            "2": {"issues": [], "suggestions": ["加光影"]},
        }
        result = _compile_critique_feedback(scores, "character")
        assert "character" in result
        assert result["character"]["1"]["issues"] == ["面部比例不对"]
        assert result["character"]["1"]["suggestions"] == ["调大眼睛间距", "缩小嘴巴"]
        assert result["character"]["2"]["suggestions"] == ["加光影"]
        assert result["character"]["2"]["issues"] == []

    def test_compile_shot_feedback(self):
        scores = {
            "5": {"issues": ["光线不匹配"], "suggestions": ["降低亮度", "暖色调"]},
        }
        result = _compile_critique_feedback(scores, "shot")
        assert "shot" in result
        assert result["shot"]["5"]["suggestions"] == ["降低亮度", "暖色调"]

    def test_empty_scores_returns_empty_feedback(self):
        result = _compile_critique_feedback({}, "character")
        assert result == {"character": {}}

    def test_missing_fields_default_to_empty(self):
        scores = {"1": {}}  # No issues/suggestions at all
        result = _compile_critique_feedback(scores, "character")
        assert result["character"]["1"]["issues"] == []
        assert result["character"]["1"]["suggestions"] == []


class TestCharacterPromptWithFeedback:
    """Tests _build_character_prompt with critique_feedback injection."""

    @pytest.fixture
    def agent(self):
        agent = RenderAgent()
        agent._style_descriptor_async = AsyncMock(
            return_value=("anime style, vibrant colors", "blurry, low quality")
        )
        return agent

    @pytest.fixture
    def character(self):
        char = MagicMock()
        char.id = 1
        char.description = "warrior girl"
        char.visual_notes = "red armor, short hair"
        return char

    @pytest.fixture
    def ctx_without_feedback(self):
        ctx = MagicMock(spec=AgentContext)
        ctx.critique_feedback = None
        return ctx

    @pytest.fixture
    def ctx_with_feedback(self):
        ctx = MagicMock(spec=AgentContext)
        ctx.critique_feedback = {
            "character": {
                "1": {"issues": ["面部不对"], "suggestions": ["调大眼睛间距"]}
            }
        }
        return ctx

    @pytest.mark.asyncio
    async def test_no_feedback_no_injection(self, agent, character, ctx_without_feedback):
        prompt = await agent._build_character_prompt(
            character, style="anime", session=AsyncMock(), ctx=ctx_without_feedback
        )
        assert "改进建议" not in prompt
        assert "warrior girl" in prompt

    @pytest.mark.asyncio
    async def test_feedback_appended_to_prompt(self, agent, character, ctx_with_feedback):
        prompt = await agent._build_character_prompt(
            character, style="anime", session=AsyncMock(), ctx=ctx_with_feedback
        )
        assert "改进建议: 调大眼睛间距" in prompt
        assert prompt.endswith("调大眼睛间距")  # Suggestion at end

    @pytest.mark.asyncio
    async def test_feedback_not_appended_for_different_character(self, agent, ctx_with_feedback):
        other_char = MagicMock()
        other_char.id = 99  # Feedback is for char 1, not 99
        other_char.description = "mage"
        other_char.visual_notes = None
        prompt = await agent._build_character_prompt(
            other_char, style="anime", session=AsyncMock(), ctx=ctx_with_feedback
        )
        assert "改进建议" not in prompt

    @pytest.mark.asyncio
    async def test_ctx_none_backward_compatible(self, agent, character):
        """Without ctx parameter (backward compat), prompt still builds."""
        prompt = await agent._build_character_prompt(
            character, style="anime", session=AsyncMock()
        )
        assert "warrior girl" in prompt
        assert "改进建议" not in prompt

    @pytest.mark.asyncio
    async def test_empty_suggestions_no_injection(self, agent, character):
        ctx = MagicMock(spec=AgentContext)
        ctx.critique_feedback = {
            "character": {"1": {"issues": ["问题"], "suggestions": []}}
        }
        prompt = await agent._build_character_prompt(
            character, style="anime", session=AsyncMock(), ctx=ctx
        )
        assert "改进建议" not in prompt  # Empty suggestions → skip


class TestShotPromptWithFeedback:
    """Tests _build_shot_prompt with critique_feedback injection."""

    @pytest.fixture
    def agent(self):
        agent = RenderAgent()
        agent._style_descriptor_async = AsyncMock(
            return_value=("cinematic lighting", None)
        )
        return agent

    @pytest.fixture
    def shot(self):
        s = MagicMock()
        s.id = 5
        s.image_prompt = "forest scene"
        s.description = "A dark forest"
        return s

    @pytest.mark.asyncio
    async def test_shot_feedback_injected(self, agent, shot):
        ctx = MagicMock(spec=AgentContext)
        ctx.critique_feedback = {
            "shot": {"5": {"issues": ["光线太暗"], "suggestions": ["提高亮度", "加雾气"]}}
        }
        prompt = await agent._build_shot_prompt(
            shot, [], style="cinematic", session=AsyncMock(), ctx=ctx
        )
        assert "改进建议: 提高亮度；加雾气" in prompt

    @pytest.mark.asyncio
    async def test_shot_no_feedback_normal_prompt(self, agent, shot):
        ctx = MagicMock(spec=AgentContext)
        ctx.critique_feedback = None
        prompt = await agent._build_shot_prompt(
            shot, [], style="cinematic", session=AsyncMock(), ctx=ctx
        )
        assert "改进建议" not in prompt
        assert "forest scene" in prompt

    @pytest.mark.asyncio
    async def test_shot_feedback_wrong_id_not_injected(self, agent, shot):
        ctx = MagicMock(spec=AgentContext)
        ctx.critique_feedback = {
            "shot": {"99": {"suggestions": ["改背景"]}}  # Shot 5, feedback for 99
        }
        prompt = await agent._build_shot_prompt(
            shot, [], style="cinematic", session=AsyncMock(), ctx=ctx
        )
        assert "改进建议" not in prompt

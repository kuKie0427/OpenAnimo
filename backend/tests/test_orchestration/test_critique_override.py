"""Tests for critique override feature: _critic_interrupt, _apply_critique_overrides,
_build_critique_review_results, _resolve_entity_name, and node behaviors.

Covers 8 scenarios:
1. critique_enabled=False → node routes normally, no interrupt
2. auto_mode=True → node routes by AI decision, no interrupt
3. auto_mode=False + AI passes → interrupt fires, resume={} → forward
4. auto_mode=False + AI says regenerate → interrupt fires, override skip → forward
5. auto_mode=False + AI passes → interrupt fires, override entity → routes render
6. _apply_critique_overrides → merge logic correct
7. character batch → _build_critique_review_results correct structure
8. shot batch → same as #7
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.orchestration.nodes import (
    _apply_critique_overrides,
    _build_critique_review_results,
    _compile_critique_feedback,
    _critic_interrupt,
    _resolve_entity_name,
    critique_character_images_node,
    critique_shot_images_node,
)
from app.orchestration.runtime import build_phase2_runtime_context
from tests.agent_fixtures import DummyWsManager, make_context
from tests.factories import create_character, create_shot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _eager_load_project(session, ctx):
    """Reload ctx.project with eagerly-loaded relationships to avoid MissingGreenlet."""
    await session.refresh(ctx.project, ["characters", "shots"])


class FakeOrchestrator:
    """Minimal orchestrator stub for node tests."""

    def __init__(self):
        self.ws = DummyWsManager()
        self.session = MagicMock()

    async def set_run_state(self, run, **fields):
        pass


def _review_result(
    scores: dict | None = None,
    *,
    should_regenerate: bool = False,
    min_score: float = 5.0,
) -> dict:
    """Build a CriticAgent result dict matching run_character_review / run_shot_review."""
    return {
        "scores": scores or {},
        "min_score": min_score,
        "should_regenerate": should_regenerate,
    }


def _entity_review(
    *,
    score: float = 7.0,
    will_regenerate: bool = False,
    issues: list[str] | None = None,
    suggestions: list[str] | None = None,
    failed_checks: list[str] | None = None,
) -> dict:
    """Build a single-entity review dict."""
    return {
        "score": score,
        "dimensions": {"consistency": int(score), "quality": int(score), "composition": int(score)},
        "issues": issues or [],
        "suggestions": suggestions or [],
        "will_regenerate": will_regenerate,
        "failed_checks": failed_checks or [],
    }


def _make_runtime(
    agent_ctx,
    *,
    orchestrator: FakeOrchestrator | None = None,
    start_stage: str = "critique_character_images",
    auto_mode: bool = False,
) -> MagicMock:
    """Build a LangGraph Runtime mock wrapping a Phase2RuntimeContext."""
    orch = orchestrator or FakeOrchestrator()
    ctx = build_phase2_runtime_context(
        orchestrator=orch,
        agent_context=agent_ctx,
        start_stage=start_stage,  # type: ignore[arg-type]
        auto_mode=auto_mode,
    )
    runtime = MagicMock()
    runtime.context = ctx
    return runtime


async def _prepare_node_test(test_session, ctx):
    await _eager_load_project(test_session, ctx)


# ---------------------------------------------------------------------------
# Scenario 6: _apply_critique_overrides unit tests
# ---------------------------------------------------------------------------


class TestApplyCritiqueOverrides:
    """Scenario 6: Verify merge logic correctness, _human_overridden flag."""

    def test_empty_overrides_does_nothing(self):
        result = {
            "scores": {
                "1": {"will_regenerate": True, "score": 3.0},
            },
            "should_regenerate": True,
        }
        _apply_critique_overrides(result, {})
        assert result["scores"]["1"]["will_regenerate"] is True
        assert "_human_overridden" not in result["scores"]["1"]
        assert result["should_regenerate"] is True

    def test_override_flip_false_to_true(self):
        result = {
            "scores": {
                "1": {"will_regenerate": False, "score": 8.0},
            },
            "should_regenerate": False,
        }
        _apply_critique_overrides(result, {1: True})
        assert result["scores"]["1"]["will_regenerate"] is True
        assert result["scores"]["1"]["_human_overridden"] is True
        assert result["should_regenerate"] is True

    def test_override_flip_true_to_false(self):
        result = {
            "scores": {
                "2": {"will_regenerate": True, "score": 3.0},
            },
            "should_regenerate": True,
        }
        _apply_critique_overrides(result, {2: False})
        assert result["scores"]["2"]["will_regenerate"] is False
        assert result["scores"]["2"]["_human_overridden"] is True
        assert result["should_regenerate"] is False

    def test_partial_overrides_only_affected_entities(self):
        result = {
            "scores": {
                "1": {"will_regenerate": False, "score": 8.0},
                "2": {"will_regenerate": False, "score": 7.0},
                "3": {"will_regenerate": False, "score": 9.0},
            },
            "should_regenerate": False,
        }
        _apply_critique_overrides(result, {2: True})
        # Entity 2 overridden
        assert result["scores"]["2"]["will_regenerate"] is True
        assert result["scores"]["2"]["_human_overridden"] is True
        # Entity 1 unchanged
        assert result["scores"]["1"]["will_regenerate"] is False
        assert "_human_overridden" not in result["scores"]["1"]
        # Entity 3 unchanged
        assert result["scores"]["3"]["will_regenerate"] is False
        assert "_human_overridden" not in result["scores"]["3"]
        # should_regenerate recomputed
        assert result["should_regenerate"] is True

    def test_full_overrides_all_entities(self):
        result = {
            "scores": {
                "1": {"will_regenerate": True, "score": 3.0},
                "2": {"will_regenerate": False, "score": 8.0},
            },
            "should_regenerate": True,
        }
        _apply_critique_overrides(result, {1: False, 2: True})
        assert result["scores"]["1"]["will_regenerate"] is False
        assert result["scores"]["1"]["_human_overridden"] is True
        assert result["scores"]["2"]["will_regenerate"] is True
        assert result["scores"]["2"]["_human_overridden"] is True
        assert result["should_regenerate"] is True  # entity 2 now needs regen

    def test_override_entity_not_in_scores_is_ignored(self):
        result = {
            "scores": {
                "1": {"will_regenerate": False, "score": 8.0},
            },
            "should_regenerate": False,
        }
        _apply_critique_overrides(result, {999: True})
        assert result["scores"]["1"]["will_regenerate"] is False
        assert "_human_overridden" not in result["scores"]["1"]
        assert result["should_regenerate"] is False

    def test_empty_scores_with_overrides_is_handled(self):
        result: dict = {"scores": {}, "should_regenerate": False}
        _apply_critique_overrides(result, {1: True})
        assert result["scores"] == {}
        assert result["should_regenerate"] is False

    def test_all_entities_overridden_to_false_zero_regenerations(self):
        result = {
            "scores": {
                "1": {"will_regenerate": True, "score": 3.0},
                "2": {"will_regenerate": True, "score": 3.0},
            },
            "should_regenerate": True,
        }
        _apply_critique_overrides(result, {1: False, 2: False})
        assert result["should_regenerate"] is False


# ---------------------------------------------------------------------------
# Scenario 7 & 8: _build_critique_review_results
# ---------------------------------------------------------------------------


class TestBuildCritiqueReviewResults:
    """Scenarios 7 & 8: Verify _build_critique_review_results produces correct structure
    for character and shot entity types."""

    @pytest.mark.asyncio
    async def test_character_batch_structure(self, test_session, test_settings):
        """Scenario 7: entity_type='character' produces correct review results."""
        ctx = await make_context(test_session, test_settings)
        char_a = await create_character(test_session, ctx.project.id, name="Alice")
        char_b = await create_character(test_session, ctx.project.id, name="Bob")

        from types import SimpleNamespace
        mock_ctx = SimpleNamespace()
        mock_ctx.project = SimpleNamespace()
        mock_ctx.project.characters = [char_a, char_b]
        mock_ctx.project.shots = []

        result = {
            "scores": {
                str(char_a.id): _entity_review(score=8.5, will_regenerate=False),
                str(char_b.id): _entity_review(
                    score=4.0, will_regenerate=True,
                    issues=["面部不一致"],
                    suggestions=["参考角色描述调整"],
                    failed_checks=["consistency"],
                ),
            },
            "should_regenerate": True,
        }

        review_results = _build_critique_review_results(result, mock_ctx, "character")
        assert len(review_results) == 2

        alice = next(r for r in review_results if r["entity_id"] == char_a.id)
        assert alice["entity_name"] == "Alice"
        assert alice["score"] == 8.5
        assert alice["will_regenerate"] is False
        assert alice["issues"] == []
        assert alice["suggestions"] == []
        assert alice["failed_checks"] == []
        assert "dimensions" in alice

        bob = next(r for r in review_results if r["entity_id"] == char_b.id)
        assert bob["entity_name"] == "Bob"
        assert bob["score"] == 4.0
        assert bob["will_regenerate"] is True
        assert "面部不一致" in bob["issues"]
        assert "consistency" in bob["failed_checks"]

    @pytest.mark.asyncio
    async def test_shot_batch_structure(self, test_session, test_settings):
        """Scenario 8: entity_type='shot' produces correct review results."""
        ctx = await make_context(test_session, test_settings)
        shot_a = await create_shot(test_session, ctx.project.id, order=1, description="Opening shot")
        shot_b = await create_shot(test_session, ctx.project.id, order=2, description="Close-up")

        from types import SimpleNamespace
        mock_ctx = SimpleNamespace()
        mock_ctx.project = SimpleNamespace()
        mock_ctx.project.characters = []
        mock_ctx.project.shots = [shot_a, shot_b]

        result = {
            "scores": {
                str(shot_a.id): _entity_review(score=9.0, will_regenerate=False),
                str(shot_b.id): _entity_review(
                    score=3.5, will_regenerate=True,
                    issues=["构图失衡"],
                    suggestions=["调整镜头角度"],
                    failed_checks=["composition"],
                ),
            },
            "should_regenerate": True,
        }

        review_results = _build_critique_review_results(result, mock_ctx, "shot")
        assert len(review_results) == 2

        sa = next(r for r in review_results if r["entity_id"] == shot_a.id)
        assert sa["entity_name"] == "Opening shot"
        assert sa["score"] == 9.0
        assert sa["will_regenerate"] is False

        sb = next(r for r in review_results if r["entity_id"] == shot_b.id)
        assert sb["entity_name"] == "Close-up"
        assert sb["score"] == 3.5
        assert sb["will_regenerate"] is True
        assert "构图失衡" in sb["issues"]
        assert "composition" in sb["failed_checks"]

    @pytest.mark.asyncio
    async def test_shot_fallback_name(self, test_session, test_settings):
        """Shot with only order uses '镜头 {order}' fallback name."""
        ctx = await make_context(test_session, test_settings)
        shot = await create_shot(
            test_session, ctx.project.id, order=3,
            description="",
            prompt="test prompt",
        )

        from types import SimpleNamespace
        mock_ctx = SimpleNamespace()
        mock_ctx.project = SimpleNamespace()
        mock_ctx.project.characters = []
        mock_ctx.project.shots = [shot]

        result = {
            "scores": {str(shot.id): _entity_review(score=7.0)},
            "should_regenerate": False,
        }
        review_results = _build_critique_review_results(result, mock_ctx, "shot")
        assert len(review_results) == 1
        assert review_results[0]["entity_name"] == "镜头 3"

    def test_empty_scores_returns_empty_list(self, test_session, test_settings):
        from types import SimpleNamespace
        mock_ctx = SimpleNamespace()
        mock_ctx.project = SimpleNamespace()
        mock_ctx.project.characters = []
        mock_ctx.project.shots = []
        result = {"scores": {}, "should_regenerate": False}
        review_results = _build_critique_review_results(result, mock_ctx, "character")
        assert review_results == []

    def test_unknown_entity_name(self):
        """Entity not in project returns 'unknown'."""
        from types import SimpleNamespace
        mock_ctx = SimpleNamespace()
        mock_ctx.project = SimpleNamespace()
        mock_ctx.project.characters = []
        mock_ctx.project.shots = []
        name = _resolve_entity_name(mock_ctx, "character", 99999)
        assert name == "unknown"
        name = _resolve_entity_name(mock_ctx, "shot", 99999)
        assert name == "unknown"

    @pytest.mark.asyncio
    async def test_image_url_present_in_results(self, test_session, test_settings):
        """+1: _build_critique_review_results includes image_url for character/shot."""
        ctx = await make_context(test_session, test_settings)
        char = await create_character(test_session, ctx.project.id, name="Alice")
        char.image_url = "/static/characters/alice.png"
        shot = await create_shot(test_session, ctx.project.id, order=1, description="Test shot")
        shot.image_url = "/static/shots/shot_001.png"

        from types import SimpleNamespace
        mock_ctx = SimpleNamespace()
        mock_ctx.project = SimpleNamespace()
        mock_ctx.project.characters = [char]
        mock_ctx.project.shots = [shot]

        # Test character
        char_result = {"scores": {str(char.id): _entity_review(score=8.0)}, "should_regenerate": False}
        char_reviews = _build_critique_review_results(char_result, mock_ctx, "character")
        assert len(char_reviews) == 1
        assert char_reviews[0]["image_url"] == "/static/characters/alice.png"

        # Test shot
        shot_result = {"scores": {str(shot.id): _entity_review(score=7.0)}, "should_regenerate": False}
        shot_reviews = _build_critique_review_results(shot_result, mock_ctx, "shot")
        assert len(shot_reviews) == 1
        assert shot_reviews[0]["image_url"] == "/static/shots/shot_001.png"

        # Test entity without image_url
        char_no_img = await create_character(test_session, ctx.project.id, name="Bob")
        char_no_img.image_url = None
        mock_ctx.project.characters.append(char_no_img)
        bob_result = {"scores": {str(char_no_img.id): _entity_review(score=6.0)}, "should_regenerate": False}
        bob_reviews = _build_critique_review_results(bob_result, mock_ctx, "character")
        assert len(bob_reviews) == 1
        assert bob_reviews[0]["image_url"] is None


# ---------------------------------------------------------------------------
# _compile_critique_feedback
# ---------------------------------------------------------------------------


class TestCompileCritiqueFeedback:
    def test_character_feedback_structure(self):
        scores = {
            "1": {
                "issues": ["颜色过暗"],
                "suggestions": ["提高亮度", "增加对比度"],
            },
            "2": {
                "issues": [],
                "suggestions": [],
            },
        }
        feedback = _compile_critique_feedback(scores, "character")
        assert "character" in feedback
        assert feedback["character"]["1"]["issues"] == ["颜色过暗"]
        assert feedback["character"]["1"]["suggestions"] == ["提高亮度", "增加对比度"]
        assert feedback["character"]["2"]["issues"] == []
        assert feedback["character"]["2"]["suggestions"] == []

    def test_shot_feedback_structure(self):
        scores = {
            "3": {"issues": ["构图失衡"], "suggestions": ["调整角度"]},
        }
        feedback = _compile_critique_feedback(scores, "shot")
        assert "shot" in feedback
        assert feedback["shot"]["3"]["issues"] == ["构图失衡"]


# ---------------------------------------------------------------------------
# Scenario 1: critique_enabled=False → node routes normally, no interrupt
# ---------------------------------------------------------------------------


class TestCritiqueDisabledNode:
    """Scenario 1: When critique_enabled is False, node returns immediately
    without calling CriticAgent or interrupt."""

    @pytest.mark.asyncio
    async def test_character_node_skips_when_disabled(
        self, test_session, test_settings, monkeypatch
    ):
        test_settings.critique_enabled = False
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx)

        critic_called = False

        class SpyCriticAgent:
            async def run_character_review(self, ctx):
                nonlocal critic_called
                critic_called = True
                return {"scores": {}, "should_regenerate": False}

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", SpyCriticAgent)

        interrupt_captured = []

        def _spy_interrupt(payload):
            interrupt_captured.append(payload)
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_character_images_node(state, runtime)

        test_settings.critique_enabled = True

        assert critic_called is False, "CriticAgent should not be called"
        assert len(interrupt_captured) == 0, "interrupt should not be called"
        assert result["current_stage"] == "critique_character_images"
        assert result["critique_scores"] == {}
        assert result["route_stage"] == "render_shots"

    @pytest.mark.asyncio
    async def test_shot_node_skips_when_disabled(
        self, test_session, test_settings, monkeypatch
    ):
        test_settings.critique_enabled = False
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, start_stage="critique_shot_images")

        critic_called = False

        class SpyCriticAgent:
            async def run_shot_review(self, ctx):
                nonlocal critic_called
                critic_called = True
                return {"scores": {}, "should_regenerate": False}

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", SpyCriticAgent)

        interrupt_captured = []

        def _spy_interrupt(payload):
            interrupt_captured.append(payload)
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_shot_images_node(state, runtime)

        test_settings.critique_enabled = True

        assert critic_called is False
        assert len(interrupt_captured) == 0
        assert result["current_stage"] == "critique_shot_images"
        assert result["critique_scores"] == {}
        assert result["route_stage"] == "compose_videos"


# ---------------------------------------------------------------------------
# Scenario 2: auto_mode=True → node routes by AI decision, no interrupt
# ---------------------------------------------------------------------------


class TestAutoModeNode:
    """Scenario 2: With auto_mode=True, _critic_interrupt returns {} early,
    so the node uses the AI's should_regenerate decision without human pause."""

    @pytest.mark.asyncio
    async def test_character_node_auto_mode_no_regenerate(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=True)

        mock_result = _review_result(
            scores={
                "1": _entity_review(score=8.5, will_regenerate=False),
            },
            should_regenerate=False,
            min_score=8.5,
        )

        class FakeCritic:
            async def run_character_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        interrupt_captured = []

        def _spy_interrupt(payload):
            interrupt_captured.append(payload)
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_character_images_node(state, runtime)

        assert len(interrupt_captured) == 0, "interrupt should NOT fire in auto_mode"
        assert result["route_stage"] == "render_shots"
        assert result["critique_round"] == 0

    @pytest.mark.asyncio
    async def test_character_node_auto_mode_with_regenerate(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=True)

        # AI says some characters need regen
        mock_result = _review_result(
            scores={
                "1": _entity_review(score=3.0, will_regenerate=True, issues=["模糊"]),
            },
            should_regenerate=True,
            min_score=3.0,
        )

        class FakeCritic:
            async def run_character_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        interrupt_captured = []

        def _spy_interrupt(payload):
            interrupt_captured.append(payload)
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_character_images_node(state, runtime)

        assert len(interrupt_captured) == 0, "interrupt should NOT fire in auto_mode"
        assert result["route_stage"] == "render_characters"
        assert result["critique_round"] == 1

    @pytest.mark.asyncio
    async def test_shot_node_auto_mode_no_regenerate(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, start_stage="critique_shot_images", auto_mode=True)

        mock_result = _review_result(
            scores={
                "10": _entity_review(score=9.0, will_regenerate=False),
            },
            should_regenerate=False,
        )

        class FakeCritic:
            async def run_shot_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        interrupt_captured = []

        def _spy_interrupt(payload):
            interrupt_captured.append(payload)
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_shot_images_node(state, runtime)

        assert len(interrupt_captured) == 0
        assert result["route_stage"] == "compose_videos"
        assert result["critique_round"] == 0


# ---------------------------------------------------------------------------
# Scenario 3: auto_mode=False + AI passes → interrupt fires, resume={} → forward
# ---------------------------------------------------------------------------


class TestInterruptAIPasses:
    """Scenario 3: AI says all pass. interrupt fires, human resumes with {}.
    Node continues forward (no regen)."""

    @pytest.mark.asyncio
    async def test_character_node_interrupt_passes_forward(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        runtime = _make_runtime(ctx, orchestrator=orch, auto_mode=False)

        # AI says all pass
        mock_result = _review_result(
            scores={
                "1": _entity_review(score=8.5, will_regenerate=False),
                "2": _entity_review(score=9.0, will_regenerate=False),
            },
            should_regenerate=False,
            min_score=8.5,
        )

        class FakeCritic:
            async def run_character_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        captured = {}

        def _capture_interrupt(payload):
            captured["payload"] = payload
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_character_images_node(state, runtime)

        assert "payload" in captured
        payload = captured["payload"]
        assert payload["gate"] == "critique_character_images"
        assert payload["results"]

        ws_types = {e["type"] for pid, e in orch.ws.events if pid == ctx.project.id}
        assert "run_progress" in ws_types

        ctx_ws_types = {e["type"] for pid, e in ctx.ws.events if pid == ctx.project.id}
        assert "critique_review" in ctx_ws_types

        assert result["route_stage"] == "render_shots"
        assert result["critique_round"] == 0

    @pytest.mark.asyncio
    async def test_shot_node_interrupt_passes_forward(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        runtime = _make_runtime(
            ctx, orchestrator=orch,
            start_stage="critique_shot_images", auto_mode=False,
        )

        mock_result = _review_result(
            scores={
                "10": _entity_review(score=9.0, will_regenerate=False),
            },
            should_regenerate=False,
        )

        class FakeCritic:
            async def run_shot_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        captured = {}

        def _capture_interrupt(payload):
            captured["payload"] = payload
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_shot_images_node(state, runtime)

        assert "payload" in captured
        assert captured["payload"]["gate"] == "critique_shot_images"
        assert result["route_stage"] == "compose_videos"
        assert result["critique_round"] == 0


# ---------------------------------------------------------------------------
# Scenario 4: auto_mode=False + AI says regenerate → override skip → forward
# ---------------------------------------------------------------------------


class TestInterruptOverrideSkip:
    """Scenario 4: AI says regenerate, but human overrides to skip all.
    Node continues forward (no regen)."""

    @pytest.mark.asyncio
    async def test_character_node_override_skip_regeneration(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        runtime = _make_runtime(ctx, orchestrator=orch, auto_mode=False)

        # AI says entity 1 needs regen
        mock_result = _review_result(
            scores={
                "1": _entity_review(
                    score=3.0, will_regenerate=True,
                    issues=["面部模糊"],
                    failed_checks=["quality"],
                ),
            },
            should_regenerate=True,
            min_score=3.0,
        )

        class FakeCritic:
            async def run_character_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        captured = {}

        def _capture_interrupt(payload):
            captured["payload"] = payload
            # Human overrides: skip regeneration for entity 1
            return {"overrides": {1: False}}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_character_images_node(state, runtime)

        # interrupt fired with override
        assert "payload" in captured

        # After override, should_regenerate becomes False → forward
        assert result["route_stage"] == "render_shots"
        assert result["critique_round"] == 0

        # Verify the override was applied to the result
        assert mock_result["scores"]["1"]["will_regenerate"] is False
        assert mock_result["scores"]["1"]["_human_overridden"] is True

    @pytest.mark.asyncio
    async def test_shot_node_override_skip_regeneration(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        runtime = _make_runtime(
            ctx, orchestrator=orch,
            start_stage="critique_shot_images", auto_mode=False,
        )

        mock_result = _review_result(
            scores={
                "5": _entity_review(
                    score=2.5, will_regenerate=True,
                    issues=["严重模糊"],
                    failed_checks=["quality", "composition"],
                ),
            },
            should_regenerate=True,
            min_score=2.5,
        )

        class FakeCritic:
            async def run_shot_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        def _capture_interrupt(payload):
            return {"overrides": {5: False}}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_shot_images_node(state, runtime)

        assert result["route_stage"] == "compose_videos"
        assert mock_result["scores"]["5"]["will_regenerate"] is False
        assert mock_result["scores"]["5"]["_human_overridden"] is True


# ---------------------------------------------------------------------------
# Scenario 5: auto_mode=False + AI passes → override entity_3 → routes render
# ---------------------------------------------------------------------------


class TestInterruptOverrideToRegenerate:
    """Scenario 5: AI says all pass, but human overrides entity_3 to regenerate.
    Node routes to render_characters for regeneration."""

    @pytest.mark.asyncio
    async def test_character_node_override_entity_to_regenerate(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        runtime = _make_runtime(ctx, orchestrator=orch, auto_mode=False)

        # AI says all 3 entities pass
        mock_result = _review_result(
            scores={
                "1": _entity_review(score=8.0, will_regenerate=False),
                "2": _entity_review(score=7.5, will_regenerate=False),
                "3": _entity_review(score=7.0, will_regenerate=False),
            },
            should_regenerate=False,
            min_score=7.0,
        )

        class FakeCritic:
            async def run_character_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        captured = {}

        def _capture_interrupt(payload):
            captured["payload"] = payload
            # Human overrides entity 3 to force regeneration
            return {"overrides": {3: True}}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_character_images_node(state, runtime)

        assert "payload" in captured

        # After override, should_regenerate=True → route to render_characters
        assert result["route_stage"] == "render_characters"
        assert result["critique_round"] == 1

        # Verify override applied
        assert mock_result["scores"]["3"]["will_regenerate"] is True
        assert mock_result["scores"]["3"]["_human_overridden"] is True
        # Entity 1 unchanged
        assert mock_result["scores"]["1"]["will_regenerate"] is False
        assert "_human_overridden" not in mock_result["scores"]["1"]

    @pytest.mark.asyncio
    async def test_shot_node_override_entity_to_regenerate(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        runtime = _make_runtime(
            ctx, orchestrator=orch,
            start_stage="critique_shot_images", auto_mode=False,
        )

        mock_result = _review_result(
            scores={
                "1": _entity_review(score=9.0, will_regenerate=False),
                "2": _entity_review(score=8.0, will_regenerate=False),
            },
            should_regenerate=False,
            min_score=8.0,
        )

        class FakeCritic:
            async def run_shot_review(self, ctx):
                return mock_result

        monkeypatch.setattr("app.orchestration.nodes.CriticAgent", FakeCritic)

        def _capture_interrupt(payload):
            return {"overrides": {2: True}}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _capture_interrupt)

        state: dict = {
            "project_id": ctx.project.id,
            "run_id": ctx.run.id,
            "thread_id": "test-thread",
            "critique_round": 0,
        }
        result = await critique_shot_images_node(state, runtime)

        assert result["route_stage"] == "render_shots"
        assert result["critique_round"] == 1
        assert mock_result["scores"]["2"]["will_regenerate"] is True


# ---------------------------------------------------------------------------
# _critic_interrupt direct tests (edge cases)
# ---------------------------------------------------------------------------


class TestCriticInterruptDirect:
    """Direct tests for _critic_interrupt edge cases."""

    @pytest.mark.asyncio
    async def test_auto_mode_returns_empty(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=True)

        interrupt_called = False

        def _spy(payload):
            nonlocal interrupt_called
            interrupt_called = True
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy)

        overrides = await _critic_interrupt(
            runtime, ctx, "critique_character_images",
            {"entity_type": "character", "total": 3, "results": []},
        )
        assert overrides == {}
        assert interrupt_called is False

    @pytest.mark.asyncio
    async def test_critique_disabled_returns_empty(
        self, test_session, test_settings, monkeypatch
    ):
        test_settings.critique_enabled = False
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=False)

        interrupt_called = False

        def _spy(payload):
            nonlocal interrupt_called
            interrupt_called = True
            return {}

        monkeypatch.setattr("app.orchestration.nodes.interrupt", _spy)

        overrides = await _critic_interrupt(
            runtime, ctx, "critique_character_images",
            {"entity_type": "character", "total": 1, "results": []},
        )

        test_settings.critique_enabled = True

        assert overrides == {}
        assert interrupt_called is False

    @pytest.mark.asyncio
    async def test_resume_non_dict_returns_empty(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=False)

        monkeypatch.setattr("app.orchestration.nodes.interrupt", lambda p: "approve")

        overrides = await _critic_interrupt(
            runtime, ctx, "critique_character_images",
            {"entity_type": "character", "total": 1, "results": []},
        )
        assert overrides == {}

    @pytest.mark.asyncio
    async def test_resume_with_overrides_parsed_correctly(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=False)

        monkeypatch.setattr(
            "app.orchestration.nodes.interrupt",
            lambda p: {"overrides": {3: True, 5: False}},
        )

        overrides = await _critic_interrupt(
            runtime, ctx, "critique_character_images",
            {"entity_type": "character", "total": 2, "results": []},
        )
        assert overrides == {3: True, 5: False}

    @pytest.mark.asyncio
    async def test_ws_event_emitted_before_interrupt(
        self, test_session, test_settings, monkeypatch
    ):
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        orch = FakeOrchestrator()
        # Force ctx.ws to the orchestrator's WS so we can capture events
        ctx.ws = orch.ws
        runtime = _make_runtime(ctx, orchestrator=orch, auto_mode=False)

        monkeypatch.setattr("app.orchestration.nodes.interrupt", lambda p: {})

        review_data = {
            "entity_type": "character",
            "total": 2,
            "results": [
                {"entity_id": 1, "entity_name": "Alice", "score": 8.0, "will_regenerate": False},
            ],
        }
        await _critic_interrupt(runtime, ctx, "critique_character_images", review_data)

        # Verify WS event
        ws_events = [e for pid, e in orch.ws.events if pid == ctx.project.id]
        review_events = [e for e in ws_events if e["type"] == "critique_review"]
        assert len(review_events) == 1
        assert review_events[0]["data"] == review_data

    @pytest.mark.asyncio
    async def test_resume_with_feedback_sets_critique_feedback(
        self, test_session, test_settings, monkeypatch
    ):
        """+2: _critic_interrupt resume with feedback sets agent_ctx.critique_feedback."""
        ctx = await make_context(test_session, test_settings)
        await _eager_load_project(test_session, ctx)
        runtime = _make_runtime(ctx, auto_mode=False)

        monkeypatch.setattr(
            "app.orchestration.nodes.interrupt",
            lambda p: {"overrides": {}, "feedback": "角色面部表情需要更自然"},
        )

        await _critic_interrupt(
            runtime, ctx, "critique_character_images",
            {"entity_type": "character", "total": 1, "results": []},
        )
        assert ctx.critique_feedback == {"human_feedback": "角色面部表情需要更自然"}

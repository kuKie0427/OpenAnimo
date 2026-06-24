from __future__ import annotations


import pytest

from app.orchestration.nodes import (
    _approval_result,
    _auto_approval_result,
    _is_video_provider_invalid,
    _normalize_resume_value,
    _should_skip_stage,
    _stage_key,
    route_after_characters_approval,
    route_after_shots_approval,
    route_after_shot_images_approval,
    route_after_compose_approval,
    route_after_review,
    route_from_start,
)
from app.orchestration.state import (
    PRODUCTION_STAGE_SEQUENCE,
    next_production_stage,
    workflow_progress_for_stage,
)


class TestStateHelpers:
    def test_next_production_stage_plan_characters(self):
        assert next_production_stage("plan_characters") == "plan_shots"

    def test_next_production_stage_plan_shots(self):
        assert next_production_stage("plan_shots") == "render_characters"

    def test_next_production_stage_render_characters(self):
        assert next_production_stage("render_characters") == "render_shots"

    def test_next_production_stage_render_shots(self):
        assert next_production_stage("render_shots") == "compose_videos"

    def test_next_production_stage_compose_merge(self):
        assert next_production_stage("compose_merge") == "add_audio"

    def test_next_production_stage_approval_suffix(self):
        assert next_production_stage("characters_approval") == "plan_shots"

    def test_next_production_stage_none(self):
        assert next_production_stage(None) is None

    def test_next_production_stage_invalid(self):
        assert next_production_stage("review") is None

    def test_workflow_progress_plan_characters_start(self):
        assert workflow_progress_for_stage("plan_outline") == 0.0

    def test_workflow_progress_plan_characters_half(self):
        # plan_characters is at index 1 of 8 production stages
        assert workflow_progress_for_stage("plan_characters", within_stage=0.5) == pytest.approx(
            1.5 / 8
        )

    def test_workflow_progress_render_characters_start(self):
        assert workflow_progress_for_stage("render_characters") == pytest.approx(3 / 8)

    def test_workflow_progress_compose_videos(self):
        assert workflow_progress_for_stage("compose_videos") == pytest.approx(5 / 8)

    def test_workflow_progress_compose_merge_full(self):
        assert workflow_progress_for_stage("add_audio", within_stage=1.0) == 1.0

    def test_workflow_progress_clamps(self):
        assert workflow_progress_for_stage("plan_outline", within_stage=2.0) == pytest.approx(
            1 / 8
        )

    def test_workflow_progress_unknown(self):
        assert workflow_progress_for_stage("unknown") == 0.0

    def test_production_stage_sequence(self):
        assert PRODUCTION_STAGE_SEQUENCE == (
            "plan_outline",
            "plan_characters",
            "plan_shots",
            "render_characters",
            "render_shots",
            "compose_videos",
            "compose_merge",
            "add_audio",
        )


class TestNodeHelpers:
    def test_stage_key(self):
        assert _stage_key("plan_characters") == "stage:plan_characters"
        assert _stage_key("render_characters") == "stage:render_characters"
        assert _stage_key("compose_videos") == "stage:compose_videos"

    def test_should_skip_stage_no_lineage(self):
        assert _should_skip_stage({}, "plan_characters") is False

    def test_should_skip_stage_with_lineage(self):
        assert (
            _should_skip_stage({"artifact_lineage": ["stage:plan_characters"]}, "plan_characters")
            is True
        )

    def test_should_skip_stage_different_stage(self):
        assert (
            _should_skip_stage({"artifact_lineage": ["stage:plan_characters"]}, "render_characters")
            is False
        )

    def test_is_video_provider_invalid_none(self):
        assert _is_video_provider_invalid(None) is False

    def test_is_video_provider_invalid_not_dict(self):
        assert _is_video_provider_invalid("string") is False

    def test_is_video_provider_invalid_valid(self):
        assert _is_video_provider_invalid({"video": {"valid": True}}) is False

    def test_is_video_provider_invalid_false(self):
        assert _is_video_provider_invalid({"video": {"valid": False}}) is True

    def test_is_video_provider_invalid_no_valid_key(self):
        assert _is_video_provider_invalid({"video": {}}) is False


class TestApprovalResults:
    def test_approval_result_no_feedback(self):
        result = _approval_result(
            approval_stage="characters_approval",
            history_key="plan_characters",
            next_stage="plan_shots",
            feedback="",
        )
        assert result["review_requested"] is False
        assert result["route_stage"] == "plan_shots"

    def test_approval_result_with_feedback(self):
        result = _approval_result(
            approval_stage="characters_approval",
            history_key="plan_characters",
            next_stage="plan_shots",
            feedback="fix the story",
        )
        assert result["review_requested"] is True
        assert result["route_stage"] == "review"
        assert result["approval_feedback"] == "fix the story"

    def test_auto_approval_result(self):
        result = _auto_approval_result(
            approval_stage="shot_images_approval",
            history_key="render_shots",
            next_stage="compose_videos",
        )
        assert result["review_requested"] is False
        assert result["route_stage"] == "compose_videos"
        assert result["approval_feedback"] == ""


class TestRouteFunctions:
    def test_route_from_start_plan_characters(self):
        assert route_from_start({"current_stage": "plan_characters"}) == "plan_characters"

    def test_route_from_start_render_characters(self):
        assert route_from_start({"current_stage": "render_characters"}) == "render_characters"

    def test_route_from_start_default(self):
        assert route_from_start({}) == "plan_outline"

    def test_route_after_characters_approval_no_review(self):
        assert route_after_characters_approval({}) == "plan_shots"

    def test_route_after_characters_approval_with_review(self):
        assert route_after_characters_approval({"review_requested": True}) == "review"

    def test_route_after_characters_approval_route_stage_overrides(self):
        assert route_after_characters_approval({"route_stage": "plan_shots"}) == "plan_shots"

    def test_route_after_shots_approval_no_review(self):
        assert route_after_shots_approval({}) == "render_characters"

    def test_route_after_shot_images_approval_no_review(self):
        assert route_after_shot_images_approval({}) == "critique_shot_images"

    def test_route_after_compose_approval_no_review(self):
        from langgraph.graph import END

        assert route_after_compose_approval({}) == END

    def test_route_after_review_default(self):
        assert route_after_review({}) == "plan_characters"

    def test_route_after_review_render(self):
        assert route_after_review({"route_stage": "render_characters"}) == "render_characters"

    def test_route_after_review_compose(self):
        assert route_after_review({"route_stage": "compose_videos"}) == "compose_videos"


class TestNormalizeResumeValue:
    def test_none(self):
        assert _normalize_resume_value(None) == ""

    def test_string(self):
        assert _normalize_resume_value("  hello  ") == "hello"

    def test_dict_with_feedback(self):
        assert _normalize_resume_value({"feedback": "fix it"}) == "fix it"

    def test_dict_with_text(self):
        assert _normalize_resume_value({"text": "ok"}) == "ok"

    def test_dict_no_known_key(self):
        result = _normalize_resume_value({"random": 42})
        assert result == str({"random": 42}).strip()

    def test_integer(self):
        assert _normalize_resume_value(42) == "42"

    def test_empty_dict(self):
        assert _normalize_resume_value({}) == "{}"

    def test_dict_feedback_over_text(self):
        assert _normalize_resume_value({"feedback": "a", "text": "b"}) == "a"

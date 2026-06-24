from __future__ import annotations

from types import SimpleNamespace

from app.services.run_recovery import (
    AGENT_TO_STAGE,
    PHASE2_STAGE_ORDER,
    _infer_current_stage,
    _next_stage,
    _normalize_stage_history,
    _production_stage_for_approval,
    _resume_target_stage,
    _safe_stage_name,
    _snapshot_next_stage,
    _snapshot_values,
    _stage_from_snapshot,
    _stage_index,
    _thread_id_for_run,
)


class FakeRun:
    def __init__(self, id=None, current_agent=None):
        self.id = id
        self.current_agent = current_agent


# --- _thread_id_for_run ---


def test_thread_id_with_id():
    run = FakeRun(id=42)
    assert _thread_id_for_run(run) == "agent-run-42"


def test_thread_id_pending():
    run = FakeRun(id=None)
    assert _thread_id_for_run(run) == "agent-run-pending"


# --- _stage_index ---


def test_stage_index_valid():
    assert _stage_index("plan_outline") == 0
    assert _stage_index("render_characters") == 6
    assert _stage_index("review") == 16


def test_stage_index_unknown_returns_zero():
    assert _stage_index("unknown") == 0
    assert _stage_index(None) == 0
    assert _stage_index(123) == 0


# --- _next_stage ---


def test_next_stage_valid():
    assert _next_stage("plan_characters") == "characters_approval"
    assert _next_stage("render_characters") == "character_images_approval"
    assert _next_stage("review") is None


def test_next_stage_unknown_returns_first():
    assert _next_stage("unknown") == "outline_approval"


def test_next_stage_last_stage_returns_none():
    assert _next_stage("review") is None


# --- _safe_stage_name ---


def test_safe_stage_name_valid():
    assert _safe_stage_name("plan_characters") == "plan_characters"
    assert _safe_stage_name("review") == "review"


def test_safe_stage_name_invalid():
    assert _safe_stage_name("not_a_stage") is None
    assert _safe_stage_name(None) is None
    assert _safe_stage_name(123) is None


# --- _stage_from_snapshot ---


def test_stage_from_snapshot_current_stage():
    snapshot = SimpleNamespace(values={"current_stage": "plan_characters"})
    assert _stage_from_snapshot(snapshot) == "plan_characters"


def test_stage_from_snapshot_route_stage_fallback():
    snapshot = SimpleNamespace(values={"route_stage": "render_characters"})
    assert _stage_from_snapshot(snapshot) == "render_characters"


def test_stage_from_snapshot_stage_history_fallback():
    snapshot = SimpleNamespace(values={"stage_history": ["plan_characters", "render_characters"]})
    assert _stage_from_snapshot(snapshot) == "render_characters"


def test_stage_from_snapshot_no_values():
    snapshot = SimpleNamespace(values=None)
    assert _stage_from_snapshot(snapshot) is None


def test_stage_from_snapshot_non_dict_values():
    snapshot = SimpleNamespace(values="not a dict")
    assert _stage_from_snapshot(snapshot) is None


def test_stage_from_snapshot_empty_history():
    snapshot = SimpleNamespace(values={"stage_history": []})
    assert _stage_from_snapshot(snapshot) is None


def test_stage_from_snapshot_current_overrides_route():
    snapshot = SimpleNamespace(
        values={"current_stage": "plan_characters", "route_stage": "render_characters"}
    )
    assert _stage_from_snapshot(snapshot) == "plan_characters"


# --- _snapshot_values ---


def test_snapshot_values_returns_first_valid():
    s1 = SimpleNamespace(values={"a": 1})
    s2 = SimpleNamespace(values={"b": 2})
    assert _snapshot_values([s1, s2]) == {"a": 1}


def test_snapshot_values_skips_none():
    s1 = SimpleNamespace(values=None)
    s2 = SimpleNamespace(values={"b": 2})
    assert _snapshot_values([s1, s2]) == {"b": 2}


def test_snapshot_values_empty():
    assert _snapshot_values([]) == {}


# --- _normalize_stage_history ---


def test_normalize_stage_history_filters_valid():
    values = {"stage_history": ["plan_characters", "render_characters", "bogus"]}
    result = _normalize_stage_history(values)
    assert "plan_characters" in result
    assert "render_characters" in result
    assert "bogus" not in result


def test_normalize_stage_history_empty():
    assert _normalize_stage_history({}) == []


def test_normalize_stage_history_non_list():
    assert _normalize_stage_history({"stage_history": "not a list"}) == []


# --- _production_stage_for_approval ---


def test_production_stage_for_approval_valid():
    assert _production_stage_for_approval("characters_approval") == "plan_characters"
    assert _production_stage_for_approval("shot_images_approval") == "render_shots"


def test_production_stage_for_approval_non_approval():
    assert _production_stage_for_approval("plan_characters") is None
    assert _production_stage_for_approval("xyz") is None


# --- _resume_target_stage ---


def test_resume_target_review_returns_route_stage():
    values = {"route_stage": "render_characters"}
    assert (
        _resume_target_stage("review", values=values, completed_stages=["plan_characters"])
        == "render_characters"
    )


def test_resume_target_review_fallback_to_current():
    values = {}
    assert _resume_target_stage("review", values=values, completed_stages=[]) == "review"


def test_resume_target_approval_returns_current():
    assert (
        _resume_target_stage("characters_approval", values={}, completed_stages=[])
        == "characters_approval"
    )


def test_resume_target_completed_returns_next():
    assert (
        _resume_target_stage("plan_characters", values={}, completed_stages=["plan_characters"])
        == "characters_approval"
    )


def test_resume_target_not_completed_returns_current():
    assert (
        _resume_target_stage("plan_characters", values={}, completed_stages=[]) == "plan_characters"
    )


# --- _infer_current_stage ---


def test_infer_from_snapshot():
    snapshot = SimpleNamespace(values={"current_stage": "render_characters"})
    assert _infer_current_stage(FakeRun(), [snapshot]) == "render_characters"


def test_infer_from_agent():
    assert _infer_current_stage(FakeRun(current_agent="plan"), []) == "plan_characters"


def test_infer_default_plan():
    assert _infer_current_stage(FakeRun(), []) == "plan_outline"


# --- AGENT_TO_STAGE mapping ---


def test_agent_to_stage_coverage():
    assert AGENT_TO_STAGE["plan"] == "plan_characters"
    assert AGENT_TO_STAGE["render"] == "render_characters"
    assert AGENT_TO_STAGE["compose"] == "compose_videos"
    assert AGENT_TO_STAGE["review"] == "review"


def test_phase2_stage_order_length():
    assert len(PHASE2_STAGE_ORDER) == 17
    assert PHASE2_STAGE_ORDER[0] == "plan_outline"
    assert PHASE2_STAGE_ORDER[-1] == "review"


# --- _snapshot_next_stage ---


def test_snapshot_next_stage_returns_first():
    snapshot = SimpleNamespace(next=("plan_characters", "render_characters"))
    assert _snapshot_next_stage([snapshot]) == "plan_characters"


def test_snapshot_next_stage_skips_invalid():
    snapshot = SimpleNamespace(next=("bogus",))
    assert _snapshot_next_stage([snapshot]) is None


def test_snapshot_next_stage_empty():
    assert _snapshot_next_stage([]) is None


def test_snapshot_next_stage_none_attr():
    snapshot = SimpleNamespace(next=())
    assert _snapshot_next_stage([snapshot]) is None

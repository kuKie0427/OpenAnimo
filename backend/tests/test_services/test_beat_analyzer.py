"""Tests for BeatAnalyzer narrative beat distribution."""
from app.services.beat_analyzer import (
    analyze_beats,
    format_beat_schedule,
    BeatAssignment,
    ACT_RATIOS,
    BEAT_TEMPLATES,
)


class TestBeatAnalyzer:
    def test_ten_shot_distribution(self):
        """10 shots should spread across 3 acts with correct ratios."""
        result = analyze_beats(10)
        assert len(result) == 10

        act1_shots = [b for b in result if b.act == 1]
        act2_shots = [b for b in result if b.act == 2]
        act3_shots = [b for b in result if b.act == 3]

        assert len(act1_shots) == 2
        assert len(act2_shots) == 5
        assert len(act3_shots) == 3

    def test_small_shot_count_each_act_gets_at_least_one(self):
        """Even with 3 shots, each act gets at least 1."""
        result = analyze_beats(3)
        acts = {b.act for b in result}
        assert acts == {1, 2, 3}

    def test_one_shot_goes_to_act1(self):
        """1 shot should go to Act 1."""
        result = analyze_beats(1)
        assert len(result) == 1
        assert result[0].act == 1

    def test_two_shots_go_to_act1_and_act2(self):
        """2 shots should go to Act 1 and Act 2."""
        result = analyze_beats(2)
        assert len(result) == 2
        assert result[0].act == 1
        assert result[1].act == 2

    def test_shot_index_sequential(self):
        result = analyze_beats(8)
        indices = [b.shot_index for b in result]
        assert indices == list(range(1, 9))

    def test_intensity_curve_has_climax(self):
        """Act 2 should contain peak intensity."""
        result = analyze_beats(12)
        intensities = [b.intensity for b in result]
        assert max(intensities) == 5
        assert intensities[0] <= 3

    def test_last_shot_is_low_intensity(self):
        """Final shot should be resolution (low intensity)."""
        result = analyze_beats(10)
        assert result[-1].intensity <= 2
        assert result[-1].beat_name == "余韵落幕"

    def test_single_shot_edge_case(self):
        result = analyze_beats(1)
        assert len(result) == 1
        assert result[0].act == 1

    def test_zero_shots_returns_empty(self):
        result = analyze_beats(0)
        assert result == []

    def test_large_shot_count_cycling(self):
        """50 shots should cycle through beat templates without error."""
        result = analyze_beats(50)
        assert len(result) == 50
        beat_names = {b.beat_name for b in result}
        assert len(beat_names) >= 7

    def test_act_ratios_sum_to_one(self):
        total = sum(ACT_RATIOS.values())
        assert abs(total - 1.0) < 0.01

    def test_both_acts_have_templates(self):
        assert len(BEAT_TEMPLATES[1]) == 3
        assert len(BEAT_TEMPLATES[2]) == 4
        assert len(BEAT_TEMPLATES[3]) == 3


class TestFormatBeatSchedule:
    def test_format_includes_all_shots(self):
        result = analyze_beats(5)
        schedule = format_beat_schedule(result)
        for i in range(1, 6):
            assert f"#{i:2d}" in schedule or f"# {i}" in schedule

    def test_format_has_act_labels(self):
        result = analyze_beats(8)
        schedule = format_beat_schedule(result)
        assert "起" in schedule
        assert "承转" in schedule
        assert "合" in schedule

    def test_format_has_instructions(self):
        result = analyze_beats(3)
        schedule = format_beat_schedule(result)
        assert "强度" in schedule
        assert "时长" in schedule
        assert "运镜" in schedule

    def test_empty_format_returns_empty_string(self):
        assert format_beat_schedule([]) == ""


class TestBeatAssignmentDataclass:
    def test_beat_assignment_fields(self):
        b = BeatAssignment(
            shot_index=5, act=2, act_label="承转",
            beat_name="高潮对决", intensity=5,
            suggested_camera="特写·快速推拉", suggested_duration=2.0,
        )
        assert b.shot_index == 5
        assert b.act == 2
        assert b.intensity == 5

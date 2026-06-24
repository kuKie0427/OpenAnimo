"""Tests for CriticAgent dimension-level threshold behavior."""
import pytest
from unittest.mock import MagicMock
from app.agents.critic import CriticAgent


class TestCritiqueDecision:
    """Unit tests for _critique_decision() static method."""

    @pytest.fixture
    def thresholds(self):
        settings = MagicMock()
        settings.critique_score_threshold = 6.0
        settings.critique_consistency_threshold = 4
        settings.critique_quality_threshold = 4
        settings.critique_composition_threshold = 4
        return settings

    def test_all_pass_no_regeneration(self, thresholds):
        """All dimensions + score above threshold → no regeneration."""
        result = {
            "score": 7.0,
            "dimensions": {"consistency": 8, "quality": 7, "composition": 6},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is False
        assert failed == []

    def test_consistency_masking_detected(self, thresholds):
        """The masking scenario: consistency=3, but weighted score=6.9 > 6.0.
        Should still trigger regeneration because consistency < 4."""
        result = {
            "score": 6.9,
            "dimensions": {"consistency": 3, "quality": 10, "composition": 9},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is True
        assert "consistency" in failed[0]

    def test_quality_below_threshold_triggers(self, thresholds):
        """Quality dimension below threshold triggers regeneration."""
        result = {
            "score": 7.0,
            "dimensions": {"consistency": 8, "quality": 3, "composition": 8},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is True
        assert any("quality" in f for f in failed)

    def test_composition_below_threshold_triggers(self, thresholds):
        """Composition dimension below threshold triggers regeneration."""
        result = {
            "score": 7.0,
            "dimensions": {"consistency": 8, "quality": 8, "composition": 3},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is True
        assert any("composition" in f for f in failed)

    def test_all_dimensions_pass_but_score_fails(self, thresholds):
        """Dimensions OK but weighted score < 6.0 → regenerate."""
        result = {
            "score": 5.0,
            "dimensions": {"consistency": 5, "quality": 5, "composition": 5},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is True
        assert any("score" in f for f in failed)

    def test_all_fail_multiple_reasons(self, thresholds):
        """All checks fail → all 4 failure reasons returned."""
        result = {
            "score": 2.0,
            "dimensions": {"consistency": 2, "quality": 2, "composition": 1},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is True
        assert len(failed) == 4

    def test_boundary_values_at_threshold(self, thresholds):
        """Score exactly at threshold means pass (>= not >)."""
        result = {
            "score": 6.0,
            "dimensions": {"consistency": 4, "quality": 4, "composition": 4},
        }
        should, failed = CriticAgent._critique_decision(result, thresholds)
        assert should is False
        assert failed == []

    def test_custom_thresholds_respected(self):
        """Non-default thresholds are respected."""
        settings = MagicMock()
        settings.critique_score_threshold = 8.0
        settings.critique_consistency_threshold = 6
        settings.critique_quality_threshold = 5
        settings.critique_composition_threshold = 5

        # Should pass with default thresholds but fail with custom
        result = {
            "score": 7.0,
            "dimensions": {"consistency": 5, "quality": 7, "composition": 7},
        }
        should, failed = CriticAgent._critique_decision(result, settings)
        assert should is True
        # consistency: 5 < 6, score: 7.0 < 8.0
        assert len(failed) == 2

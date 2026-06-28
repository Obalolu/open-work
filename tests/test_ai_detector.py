"""Tests for the AI detector module."""

import pytest

from src.reviewers.ai_detector import detect_ai_text, AI_INDICATORS


class TestDetectAiText:
    def test_returns_detection_result(self):
        result = detect_ai_text("This is some text to analyze.")
        assert hasattr(result, "score")
        assert hasattr(result, "pass_quality")
        assert hasattr(result, "details")
        assert 0 <= result.score <= 100

    def test_ai_heavy_text(self):
        # Text with many AI indicators
        text = """Furthermore, it is worth noting that this is important.
        Additionally, the landscape of AI is revolutionary.
        Moreover, this groundbreaking paradigm shift is unprecedented.
        Consequently, we delve into the realm of possibilities.
        In today's world, the tapestry of technology is pivotal.
        Furthermore, this approach leverages cutting-edge synergy.
        Additionally, the endeavor facilitates myriad opportunities.
        Moreover, this underscores the significance of our work."""
        result = detect_ai_text(text)
        assert result.score > 30  # Should be flagged

    def test_human_like_text(self):
        text = """The experiment yielded mixed results. Some participants
        improved while others showed no change. We ran the analysis twice
        to confirm. The data suggests a modest effect, though the sample
        size limits what we can claim. One thing stood out: the timing
        of interventions mattered more than we expected."""
        result = detect_ai_text(text)
        assert result.score < 60  # Should be less flagged

    def test_flagged_phrases(self):
        text = "Furthermore, moreover, additionally, we delve into the landscape."
        result = detect_ai_text(text)
        assert len(result.flagged_phrases) > 0

    def test_custom_threshold(self):
        text = "Some normal text."
        result = detect_ai_text(text, threshold=10)
        # With a very low threshold, even normal text might fail
        assert isinstance(result.pass_quality, bool)

    def test_empty_text(self):
        result = detect_ai_text("")
        # Empty text gets flagged for zero vocabulary diversity
        assert result.score >= 0
        assert isinstance(result.pass_quality, bool)
        assert result.flagged_phrases == []

    def test_details_dict(self):
        text = "This is a test sentence with some words."
        result = detect_ai_text(text)
        assert isinstance(result.details, dict)
        assert len(result.details) > 0


class TestAiIndicators:
    def test_categories_exist(self):
        assert "transition_overuse" in AI_INDICATORS
        assert "hedging" in AI_INDICATORS
        assert "filler_starters" in AI_INDICATORS
        assert "superlatives" in AI_INDICATORS

    def test_phrases_are_strings(self):
        for category, phrases in AI_INDICATORS.items():
            assert isinstance(phrases, list)
            for phrase in phrases:
                assert isinstance(phrase, str)

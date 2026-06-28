"""Tests for the style checker module."""

import pytest

from src.reviewers.style_checker import review_style, StyleIssue


class TestReviewStyle:
    @pytest.mark.asyncio
    async def test_returns_review(self):
        text = """This paper examines the impact of AI on healthcare.
        The results demonstrate significant improvements in diagnostic accuracy.
        Furthermore, the methodology follows established protocols."""
        chapter_config = {"forbidden": ["furthermore"], "required": []}
        style_config = {
            "tone": "professional",
            "formality": 0.7,
            "forbidden_phrases": ["delve into"],
        }
        result = await review_style(text, chapter_config, style_config)
        assert hasattr(result, "score")
        assert hasattr(result, "pass_quality")
        assert hasattr(result, "issues")
        assert hasattr(result, "metrics")
        assert 0 <= result.score <= 100

    @pytest.mark.asyncio
    async def test_catches_forbidden_phrases(self):
        text = "Furthermore, this is important to note. We delve into the topic."
        chapter_config = {"forbidden": [], "required": []}
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": ["delve into"]}
        result = await review_style(text, chapter_config, style_config)
        # Should catch "delve into"
        forbidden_issues = [i for i in result.issues if i.issue_type == "forbidden_phrase"]
        assert len(forbidden_issues) > 0

    @pytest.mark.asyncio
    async def test_catches_ai_phrases(self):
        text = """Furthermore, it is worth noting that this is important.
        Additionally, the results are significant."""
        chapter_config = {"forbidden": [], "required": []}
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": []}
        result = await review_style(text, chapter_config, style_config)
        ai_issues = [i for i in result.issues if i.issue_type == "ai_phrase"]
        assert len(ai_issues) > 0

    @pytest.mark.asyncio
    async def test_clean_text_scores_high(self):
        text = """The study examined 500 patients across three hospitals.
        Results showed a 23% improvement in diagnostic speed.
        The methodology involved a randomized controlled trial.
        Limitations include the single-center design."""
        chapter_config = {"forbidden": [], "required": []}
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": []}
        result = await review_style(text, chapter_config, style_config)
        assert result.score >= 60

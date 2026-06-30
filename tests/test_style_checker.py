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

    @pytest.mark.asyncio
    async def test_catches_missing_numbered_list(self):
        text = "This chapter has only prose and no numbered items."
        chapter_config = {"forbidden": [], "required": ["Use numbered list format for objectives"]}
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": []}
        result = await review_style(text, chapter_config, style_config)
        missing = [i for i in result.issues if i.issue_type == "missing_required_element"]
        assert any("numbered list" in i.description.lower() for i in missing)

    @pytest.mark.asyncio
    async def test_allows_numbered_list_when_required(self):
        text = "The objectives are:\n1. First objective\n2. Second objective\n3. Third objective"
        chapter_config = {"forbidden": [], "required": ["Use numbered list format for objectives"]}
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": []}
        result = await review_style(text, chapter_config, style_config)
        missing = [i for i in result.issues if i.issue_type == "missing_required_element"]
        assert not any("numbered list" in i.description.lower() for i in missing)

    @pytest.mark.asyncio
    async def test_catches_bullet_list_when_prose_only_required(self):
        text = "Some prose\n- bullet item one\n- bullet item two"
        chapter_config = {"forbidden": [], "required": ["No bullet lists — prose only"]}
        style_config = {"tone": "professional", "formality": 0.7, "forbidden_phrases": []}
        result = await review_style(text, chapter_config, style_config)
        missing = [i for i in result.issues if i.issue_type == "missing_required_element"]
        assert any("bullet" in i.description.lower() for i in missing)

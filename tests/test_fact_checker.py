"""Tests for the fact checker module."""

import pytest

from src.reviewers.fact_checker import fact_check
from src.research.summarizer import Citation


def _make_test_citations():
    return [
        Citation(
            cite_id="cite_001",
            title="Test Paper One",
            authors=["John Smith"],
            year=2023,
            venue="Journal",
            abstract_summary="Summary",
            paper_url="http://example.com",
            paper_id="p1",
        ),
        Citation(
            cite_id="cite_002",
            title="Test Paper Two",
            authors=["Jane Doe"],
            year=2022,
            venue="Journal",
            abstract_summary="Summary",
            paper_url="http://example.com",
            paper_id="p2",
        ),
    ]


class TestFactCheck:
    @pytest.mark.asyncio
    async def test_clean_text_passes(self):
        citations = _make_test_citations()
        text = "Recent studies (Smith, 2023) demonstrate improvements. Further work (Doe, 2022) confirms."
        result = await fact_check(text, citations)
        assert result.hallucinated_citations == 0

    @pytest.mark.asyncio
    async def test_catches_hallucinated_citations(self):
        citations = _make_test_citations()
        text = "Study (Bogus, 2020) shows results."
        result = await fact_check(text, citations)
        assert result.hallucinated_citations == 1
        assert result.score < 100

    @pytest.mark.asyncio
    async def test_catches_verify_markers(self):
        citations = _make_test_citations()
        text = "Study shows [VERIFY] significant results (Smith, 2023)."
        result = await fact_check(text, citations)
        assert result.uncited_claims > 0

    @pytest.mark.asyncio
    async def test_no_citations_still_runs_llm_check(self):
        citations = []
        text = "Some text without any citations."
        result = await fact_check(text, citations)
        assert result.score >= 0

"""Tests for the citation compiler."""

import pytest

from src.writers.citation_compiler import (
    compile_citations,
    _format_inline,
    _format_apa,
    _format_mla,
    _format_ieee,
    _build_reference_list,
)
from src.research.summarizer import Citation


def _make_citations():
    """Create test citations."""
    return [
        Citation(
            cite_id="cite_001",
            title="Deep Learning in Medical Imaging",
            authors=["John Smith", "Jane Doe", "Bob Wilson"],
            year=2023,
            venue="Nature Medicine",
            abstract_summary="A study on deep learning.",
            paper_url="https://example.com/1",
            paper_id="p1",
        ),
        Citation(
            cite_id="cite_002",
            title="AI Diagnostics Review",
            authors=["Alice Johnson"],
            year=2022,
            venue="The Lancet",
            abstract_summary="A review of AI diagnostics.",
            paper_url="https://example.com/2",
            paper_id="p2",
        ),
        Citation(
            cite_id="cite_003",
            title="Machine Learning in Healthcare",
            authors=["Tom Brown", "Sara Lee"],
            year=2024,
            venue="JAMA",
            abstract_summary="ML applications in healthcare.",
            paper_url="https://example.com/3",
            paper_id="p3",
        ),
    ]


class TestCompileCitations:
    def test_appends_reference_list(self):
        citations = _make_citations()
        text = "Recent studies show that AI is useful."
        result = compile_citations(text, citations, style="apa")
        assert "References" in result
        assert "Deep Learning" in result
        assert "AI Diagnostics Review" in result
        assert "Machine Learning" in result

    def test_preserves_original_text(self):
        citations = _make_citations()
        text = "This is my (Smith, 2023) citation."
        result = compile_citations(text, citations, style="apa")
        assert result.startswith("This is my (Smith, 2023) citation.")
        assert "References" in result

    def test_includes_all_citations_in_references(self):
        citations = _make_citations()
        text = "Some text with no inline citations."
        result = compile_citations(text, citations, style="apa")
        assert "References" in result
        assert "Deep Learning" in result
        assert "AI Diagnostics Review" in result
        assert "Machine Learning" in result

    def test_empty_citations_returns_text_unchanged(self):
        text = "No citations here."
        result = compile_citations(text, [], style="apa")
        assert result == text

    def test_different_styles(self):
        citations = _make_citations()
        text = "Test text."
        for style in ["apa", "mla", "chicago", "ieee"]:
            result = compile_citations(text, citations, style=style)
            assert "References" in result


class TestFormatInline:
    def test_apa_single_author(self):
        c = _make_citations()[1]  # Alice Johnson
        result = _format_inline(c, "apa")
        assert "Johnson" in result
        assert "2022" in result

    def test_apa_two_authors(self):
        c = _make_citations()[2]  # Tom Brown, Sara Lee
        result = _format_inline(c, "apa")
        assert "Brown" in result
        assert "Lee" in result

    def test_apa_three_authors(self):
        c = _make_citations()[0]  # 3 authors
        result = _format_inline(c, "apa")
        assert "Smith" in result
        assert "et al." in result

    def test_mla_format(self):
        c = _make_citations()[0]
        result = _format_inline(c, "mla")
        assert "Smith" in result

    def test_ieee_format(self):
        c = _make_citations()[0]
        result = _format_inline(c, "ieee")
        assert "[" in result


class TestFormatApa:
    def test_basic_format(self):
        c = _make_citations()[0]
        result = _format_apa(c)
        assert "Smith" in result
        assert "Doe" in result
        assert "Wilson" in result
        assert "2023" in result
        assert "Deep Learning" in result
        assert "Nature Medicine" in result

    def test_single_author(self):
        c = _make_citations()[1]
        result = _format_apa(c)
        assert "Johnson, A." in result


class TestBuildReferenceList:
    def test_sorted_by_author(self):
        citations = _make_citations()
        result = _build_reference_list(citations, "apa")
        assert "References" in result
        brown_pos = result.find("Brown")
        johnson_pos = result.find("Johnson")
        smith_pos = result.find("Smith")
        assert brown_pos < johnson_pos < smith_pos

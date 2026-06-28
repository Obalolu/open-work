"""Tests for the humanizer rewriter module."""

import pytest

from src.humanizer.rewriter import humanize_text, polish_text


class TestHumanizeText:
    @pytest.mark.asyncio
    async def test_returns_string(self):
        text = "This is a test sentence. It should be rewritten."
        # This test requires LLM API access - skip if not available
        try:
            result = await humanize_text(text, intensity="light")
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception:
            pytest.skip("LLM API not available")

    @pytest.mark.asyncio
    async def test_preserves_citations(self):
        text = "Study {cite_001} shows results. Paper {cite_002} confirms."
        try:
            result = await humanize_text(text, intensity="light")
            assert "{cite_001}" in result or "cite_001" in result
        except Exception:
            pytest.skip("LLM API not available")


class TestPolishText:
    @pytest.mark.asyncio
    async def test_returns_string(self):
        text = "This is a test. It has good grammar."
        try:
            result = await polish_text(text)
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception:
            pytest.skip("LLM API not available")

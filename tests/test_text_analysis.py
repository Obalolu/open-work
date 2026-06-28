"""Tests for the text analysis module."""

import pytest

from src.utils.text_analysis import (
    split_sentences,
    count_syllables,
    flesch_kincaid_grade,
    detect_passive_voice,
    calculate_ttr,
    count_bullets,
    count_ai_phrases,
    analyze_text,
)


class TestSplitSentences:
    def test_simple_sentences(self):
        text = "This is a sentence. This is another one. And a third."
        result = split_sentences(text)
        assert len(result) == 3

    def test_empty_text(self):
        assert split_sentences("") == []

    def test_single_sentence(self):
        result = split_sentences("Just one sentence here.")
        assert len(result) == 1


class TestCountSyllables:
    def test_single_syllable(self):
        assert count_syllables("cat") == 1

    def test_multiple_syllables(self):
        assert count_syllables("beautiful") >= 2

    def test_short_word(self):
        assert count_syllables("a") == 1


class TestFleschKincaidGrade:
    def test_simple_text(self):
        text = "The cat sat on the mat. It was a good cat. The cat liked the mat."
        grade = flesch_kincaid_grade(text)
        assert -5 <= grade <= 20

    def test_empty_text(self):
        assert flesch_kincaid_grade("") == 0.0


class TestDetectPassiveVoice:
    def test_passive_sentence(self):
        text = "The paper was written by the researchers."
        count = detect_passive_voice(text)
        assert count >= 1

    def test_active_sentence(self):
        text = "The researchers wrote the paper."
        count = detect_passive_voice(text)
        assert count == 0


class TestCalculateTtr:
    def test_repetitive_text(self):
        words = ["the"] * 100
        ttr = calculate_ttr(words)
        assert ttr < 0.1

    def test_diverse_text(self):
        words = [f"word{i}" for i in range(80)] * 2
        ttr = calculate_ttr(words)
        assert ttr > 0.5


class TestCountBullets:
    def test_bullets(self):
        text = "- Item one\n- Item two\n* Item three\n  - Nested"
        assert count_bullets(text) == 4

    def test_no_bullets(self):
        text = "Just plain text.\nNo bullets here."
        assert count_bullets(text) == 0


class TestCountAiPhrases:
    def test_finds_phrases(self):
        text = "Furthermore, it is worth noting that this is important."
        phrases = count_ai_phrases(text)
        assert "furthermore" in phrases
        assert "it is worth noting" in phrases

    def test_clean_text(self):
        text = "The results show a significant improvement in accuracy."
        phrases = count_ai_phrases(text)
        assert len(phrases) == 0


class TestAnalyzeText:
    def test_returns_metrics(self):
        text = """This is a sample academic text. It contains multiple sentences.
        The analysis should calculate various metrics including word count,
        sentence count, and reading grade. Each metric provides insight
        into the writing quality and potential AI detection risk."""
        metrics = analyze_text(text)
        assert metrics.total_words > 0
        assert metrics.total_sentences > 0
        assert metrics.reading_grade > 0
        assert 0 <= metrics.passive_voice_pct <= 100

    def test_empty_text(self):
        metrics = analyze_text("")
        assert metrics.total_words == 0
        assert metrics.total_sentences == 0

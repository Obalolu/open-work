"""Text analysis utilities for style checking and diversity metrics."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class TextMetrics:
    """Metrics for analyzing text quality and AI-detection risk."""
    total_words: int
    total_sentences: int
    avg_sentence_length: float
    short_sentences_pct: float   # < 15 words
    medium_sentences_pct: float  # 15-25 words
    long_sentences_pct: float    # > 25 words
    type_token_ratio: float
    passive_voice_pct: float
    bullet_count: int
    reading_grade: float


def split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    text = re.sub(r'\s+', ' ', text.strip())
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'\[])', text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def count_syllables(word: str) -> int:
    """Estimate syllable count for a word."""
    word = word.lower().strip()
    if len(word) <= 3:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_kincaid_grade(text: str) -> float:
    """Calculate Flesch-Kincaid reading grade level."""
    sentences = split_sentences(text)
    words = text.split()
    if not sentences or not words:
        return 0.0
    total_syllables = sum(count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = total_syllables / len(words)
    return 0.39 * asl + 11.8 * asw - 15.59


def detect_passive_voice(text: str) -> int:
    """Count passive voice constructions (approximate)."""
    pattern = r'\b(is|are|was|were|be|been|being)\s+(being\s+)?\w+(ed|en|wn|nt)\b'
    return len(re.findall(pattern, text, re.IGNORECASE))


def calculate_ttr(words: list[str], window: int = 100) -> float:
    """Calculate Type-Token Ratio with a sliding window."""
    if len(words) <= window:
        return len(set(words)) / max(len(words), 1)
    ratios = []
    for i in range(0, len(words) - window + 1, window // 2):
        chunk = words[i:i + window]
        ratios.append(len(set(chunk)) / len(chunk))
    return sum(ratios) / max(len(ratios), 1)


def count_bullets(text: str) -> int:
    """Count bullet point lines."""
    return len(re.findall(r'^\s*[\*\-]\s+', text, re.MULTILINE))


AI_PHRASES = [
    "it is worth noting", "it is important to note", "in conclusion",
    "furthermore", "moreover", "additionally", "consequently",
    "this paper aims to", "this research aims to", "delve into",
    "in the realm of", "landscape", "tapestry", "pivotal",
    "it goes without saying", "needless to say",
    "in today's world", "in this day and age",
    "the purpose of this paper is", "in this paper we will",
]


def count_ai_phrases(text: str) -> list[str]:
    """Find AI-typical phrases in text."""
    text_lower = text.lower()
    found = []
    for phrase in AI_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


def analyze_text(text: str) -> TextMetrics:
    """Perform full text analysis."""
    sentences = split_sentences(text)
    words = text.split()
    word_count = len(words)

    if word_count == 0:
        return TextMetrics(
            total_words=0, total_sentences=0, avg_sentence_length=0,
            short_sentences_pct=0, medium_sentences_pct=0, long_sentences_pct=0,
            type_token_ratio=0, passive_voice_pct=0, bullet_count=0,
            reading_grade=0,
        )

    sent_lengths = [len(s.split()) for s in sentences]
    short = sum(1 for l in sent_lengths if l < 15)
    medium = sum(1 for l in sent_lengths if 15 <= l <= 25)
    long_ = sum(1 for l in sent_lengths if l > 25)
    total_sents = max(len(sentences), 1)

    passive = detect_passive_voice(text)
    passive_pct = (passive / max(word_count, 1)) * 100

    return TextMetrics(
        total_words=word_count,
        total_sentences=len(sentences),
        avg_sentence_length=word_count / total_sents,
        short_sentences_pct=(short / total_sents) * 100,
        medium_sentences_pct=(medium / total_sents) * 100,
        long_sentences_pct=(long_ / total_sents) * 100,
        type_token_ratio=calculate_ttr([w.lower() for w in words]),
        passive_voice_pct=min(passive_pct, 100),
        bullet_count=count_bullets(text),
        reading_grade=flesch_kincaid_grade(text),
    )

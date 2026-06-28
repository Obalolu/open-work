"""Lightweight AI detection using statistical heuristics.

Based on research from DetectGPT, GLTR, and Binoculars.
This is a local, free detector — no external API needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections import Counter

from src.utils.text_analysis import (
    split_sentences,
    calculate_ttr,
    count_ai_phrases,
)


@dataclass
class DetectionResult:
    """AI detection result."""
    score: float  # 0-100 (higher = more likely AI)
    pass_quality: bool
    details: dict[str, float]
    flagged_phrases: list[str]


AI_INDICATORS = {
    "transition_overuse": [
        "furthermore", "moreover", "additionally", "consequently",
        "nevertheless", "however", "in addition", "similarly",
        "likewise", "subsequently", "henceforth",
    ],
    "hedging": [
        "it is worth noting", "it is important to note",
        "it should be noted", "it goes without saying",
        "needless to say", "it is worth mentioning",
    ],
    "filler_starters": [
        "in conclusion", "in summary", "to summarize",
        "in today's world", "in this day and age",
        "the world of", "the realm of",
    ],
    "superlatives": [
        "revolutionary", "groundbreaking", "paradigm shift",
        "cutting-edge", "state-of-the-art", "unprecedented",
    ],
}


def detect_ai_text(
    text: str,
    threshold: float = 50.0,
) -> DetectionResult:
    """Run statistical AI detection on text.

    Args:
        text: Text to analyze.
        threshold: Score threshold for flagging (0-100).

    Returns:
        DetectionResult with score and details.
    """
    details: dict[str, float] = {}
    total_score = 0.0

    # 1. Sentence length uniformity
    sentences = split_sentences(text)
    if sentences:
        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        cv = (variance ** 0.5) / max(avg_len, 1)  # coefficient of variation
        # AI text tends to have low CV (uniform sentences)
        uniformity_score = max(0, min(40, (1 - cv) * 50))
        details["sentence_uniformity"] = uniformity_score
        total_score += uniformity_score

    # 2. Vocabulary diversity (TTR)
    words = text.lower().split()
    ttr = calculate_ttr(words)
    # Low TTR = more repetitive = more AI-like
    ttr_score = max(0, min(30, (0.6 - ttr) * 80))
    details["vocabulary_repetition"] = ttr_score
    total_score += ttr_score

    # 3. AI phrase detection
    ai_phrases = count_ai_phrases(text)
    phrase_score = min(20, len(ai_phrases) * 4)
    details["ai_phrases"] = phrase_score
    total_score += phrase_score

    # 4. Transition word overuse
    text_lower = text.lower()
    transition_count = sum(
        text_lower.count(phrase)
        for phrases in AI_INDICATORS.values()
        for phrase in phrases
    )
    # Normalize by text length (per 1000 words)
    word_count = max(len(words), 1)
    transition_density = (transition_count / word_count) * 1000
    transition_score = min(15, transition_density * 3)
    details["transition_density"] = transition_score
    total_score += transition_score

    # 5. Paragraph length uniformity
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 2:
        para_lengths = [len(p.split()) for p in paragraphs]
        avg_para = sum(para_lengths) / len(para_lengths)
        para_var = sum((l - avg_para) ** 2 for l in para_lengths) / len(para_lengths)
        para_cv = (para_var ** 0.5) / max(avg_para, 1)
        para_score = max(0, min(15, (1 - para_cv) * 20))
        details["paragraph_uniformity"] = para_score
        total_score += para_score

    # Normalize to 0-100
    total_score = min(100, total_score)

    flagged = []
    for category, phrases in AI_INDICATORS.items():
        for phrase in phrases:
            if phrase in text_lower:
                flagged.append(phrase)

    return DetectionResult(
        score=total_score,
        pass_quality=total_score < threshold,
        details=details,
        flagged_phrases=flagged,
    )

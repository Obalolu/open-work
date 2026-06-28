"""Style and voice consistency checker."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.utils.llm_client import call_llm_json
from src.utils.text_analysis import (
    analyze_text,
    count_ai_phrases,
    TextMetrics,
)


@dataclass
class StyleIssue:
    """A single style issue found during review."""
    issue_type: str
    description: str
    severity: str  # "high", "medium", "low"
    line_suggestion: str = ""


@dataclass
class StyleReview:
    """Result of a style review."""
    score: int  # 0-100
    pass_quality: bool
    issues: list[StyleIssue]
    metrics: TextMetrics
    ai_phrases_found: list[str]
    rewrite_needed: list[str]


async def review_style(
    chapter_text: str,
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
) -> StyleReview:
    """Review chapter text for style consistency and quality.

    Args:
        chapter_text: The chapter markdown text.
        chapter_config: Chapter config with forbidden/required lists.
        style_config: Style config with tone, formality, etc.

    Returns:
        StyleReview with score, issues, and metrics.
    """
    metrics = analyze_text(chapter_text)
    issues: list[StyleIssue] = []

    # Check forbidden phrases
    forbidden = chapter_config.get("forbidden", []) + style_config.get("forbidden_phrases", [])
    text_lower = chapter_text.lower()
    for phrase in forbidden:
        if phrase.lower() in text_lower:
            issues.append(StyleIssue(
                issue_type="forbidden_phrase",
                description=f"Forbidden phrase found: \"{phrase}\"",
                severity="high",
            ))

    # Check AI phrases
    ai_phrases = count_ai_phrases(chapter_text)
    for phrase in ai_phrases:
        issues.append(StyleIssue(
            issue_type="ai_phrase",
            description=f"AI-typical phrase found: \"{phrase}\"",
            severity="medium",
        ))

    # Check passive voice
    if metrics.passive_voice_pct > 20:
        issues.append(StyleIssue(
            issue_type="passive_voice",
            description=f"Passive voice too high: {metrics.passive_voice_pct:.1f}% (target: <20%)",
            severity="medium",
        ))

    # Check bullet points
    max_bullets = style_config.get("max_bullet_points_per_section", 2)
    if metrics.bullet_count > max_bullets * 5:  # rough estimate of sections
        issues.append(StyleIssue(
            issue_type="bullet_overuse",
            description=f"Too many bullet points: {metrics.bullet_count}",
            severity="medium",
        ))

    # Check sentence variety
    if metrics.short_sentences_pct < 15 or metrics.long_sentences_pct < 10:
        issues.append(StyleIssue(
            issue_type="sentence_variety",
            description="Low sentence length variety — sounds robotic",
            severity="medium",
        ))

    # Check TTR (vocabulary diversity)
    if metrics.type_token_ratio < 0.4:
        issues.append(StyleIssue(
            issue_type="vocabulary",
            description=f"Low vocabulary diversity (TTR: {metrics.type_token_ratio:.2f})",
            severity="medium",
        ))

    # Use LLM for deeper review
    llm_issues = await _llm_style_review(chapter_text, chapter_config, style_config)
    issues.extend(llm_issues)

    # Calculate score
    high_count = sum(1 for i in issues if i.severity == "high")
    medium_count = sum(1 for i in issues if i.severity == "medium")
    low_count = sum(1 for i in issues if i.severity == "low")
    score = max(0, 100 - (high_count * 15) - (medium_count * 5) - (low_count * 2))

    return StyleReview(
        score=score,
        pass_quality=score >= 70 and high_count == 0,
        issues=issues,
        metrics=metrics,
        ai_phrases_found=ai_phrases,
        rewrite_needed=[],
    )


async def _llm_style_review(
    text: str,
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
) -> list[StyleIssue]:
    """Use LLM for deeper style analysis."""
    tone = style_config.get("tone", "professional")
    formality = style_config.get("formality", 0.7)

    prompt = f"""Review this academic text for style issues.

Target tone: {tone}
Target formality: {formality} (0=casual, 1=fully formal)

Text:
---
{text[:3000]}
---

Check for:
1. Tone inconsistency (mixing formal and casual)
2. Tense inconsistency within sections
3. Person inconsistency (mixing "we" and "the authors")
4. Overconfident claims without evidence
5. Repetitive sentence openings
6. Weak or vague transitions

Return JSON:
{{
  "issues": [
    {{"type": "...", "description": "...", "severity": "high|medium|low"}}
  ]
}}
Only include actual issues found. Empty list if no issues."""

    try:
        result = await call_llm_json(prompt=prompt, temperature=0.2)
        return [
            StyleIssue(
                issue_type=iss.get("type", "unknown"),
                description=iss.get("description", ""),
                severity=iss.get("severity", "low"),
            )
            for iss in result.get("issues", [])
        ]
    except Exception:
        return []

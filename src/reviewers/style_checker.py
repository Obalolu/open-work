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

    # Check required elements
    required_issues = _check_required_elements(chapter_text, chapter_config)
    issues.extend(required_issues)

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


def _check_required_elements(text: str, chapter_config: dict[str, Any]) -> list[StyleIssue]:
    """Check that required elements from the chapter config are present.

    Applies concrete pattern checks where possible and leaves subjective
    requirements to the LLM review.
    """
    issues: list[StyleIssue] = []
    required = chapter_config.get("required", [])
    if not required:
        return issues

    text_lower = text.lower()

    for req in required:
        req_lower = req.lower()

        # Numbered list requirement
        if "numbered list" in req_lower or "numbered format" in req_lower or "numbered items" in req_lower:
            if not re.search(r"^\s*\d+\.", text, re.MULTILINE):
                issues.append(StyleIssue(
                    issue_type="missing_required_element",
                    description=f"Required numbered list not found: \"{req}\"",
                    severity="high",
                ))

        # No bullet list requirement
        elif "no bullet" in req_lower or "no bullet points" in req_lower or ("prose only" in req_lower and "bullet" in req_lower):
            if re.search(r"^\s*[-*+]\s+", text, re.MULTILINE):
                issues.append(StyleIssue(
                    issue_type="missing_required_element",
                    description=f"Bullet list found where prose only is required: \"{req}\"",
                    severity="high",
                ))

        # No table requirement
        elif "no table" in req_lower:
            if "|" in text and "\n---" in text:
                issues.append(StyleIssue(
                    issue_type="missing_required_element",
                    description=f"Table found where tables are forbidden: \"{req}\"",
                    severity="high",
                ))

        # Active voice percentage
        elif "active voice" in req_lower:
            match = re.search(r"(\d+)%?\s*active voice", req_lower)
            target = int(match.group(1)) if match else 60
            # Quick estimate: count sentences with clear active markers vs passive
            sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
            if sentences:
                passive_markers = ["was ", "were ", "is ", "are ", "been ", "being ", "by the"]
                passive_count = sum(1 for s in sentences if any(m in s.lower() for m in passive_markers))
                active_pct = int(((len(sentences) - passive_count) / len(sentences)) * 100)
                if active_pct < target:
                    issues.append(StyleIssue(
                        issue_type="missing_required_element",
                        description=f"Active voice below required {target}% (estimated {active_pct}%): \"{req}\"",
                        severity="medium",
                    ))

    return issues


async def _llm_style_review(
    text: str,
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
) -> list[StyleIssue]:
    """Use LLM for deeper style analysis."""
    tone = style_config.get("tone", "professional")
    formality = style_config.get("formality", 0.7)
    required = chapter_config.get("required", [])
    required_text = "\n".join(f"  - {r}" for r in required) if required else "  (none specified)"

    prompt = f"""Review this academic text for style issues and required-element compliance.

Target tone: {tone}
Target formality: {formality} (0=casual, 1=fully formal)

Required elements the text MUST satisfy:
{required_text}

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
7. Missing or poorly satisfied required elements (e.g. rhetorical question, variable definitions, operational definitions, citations)

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

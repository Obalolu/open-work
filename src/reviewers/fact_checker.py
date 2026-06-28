"""Fact checker — validates claims against research sources."""

from __future__ import annotations

from dataclasses import dataclass

from src.research.summarizer import Citation
from src.utils.llm_client import call_llm_json


@dataclass
class FactCheckIssue:
    """A fact-check issue."""
    issue_type: str
    description: str
    severity: str


@dataclass
class FactCheckResult:
    """Result of fact-checking a chapter."""
    score: int  # 0-100
    pass_quality: bool
    issues: list[FactCheckIssue]
    uncited_claims: int
    hallucinated_citations: int


async def fact_check(
    chapter_text: str,
    citations: list[Citation],
) -> FactCheckResult:
    """Fact-check a chapter against its citations.

    Args:
        chapter_text: The chapter text to check.
        citations: List of Citation objects used in the chapter.

    Returns:
        FactCheckResult with score and issues.
    """
    issues: list[FactCheckIssue] = []

    # Check for {cite_MISSING} patterns
    import re
    missing = re.findall(r'\{cite_MISSING[^}]*\}', chapter_text)
    for m in missing:
        issues.append(FactCheckIssue(
            issue_type="missing_citation",
            description=f"Missing citation placeholder found: {m}",
            severity="high",
        ))

    # Check for invented citation IDs
    all_cite_ids = {c.cite_id for c in citations}
    used_cites = set(re.findall(r'\{cite_(\d{3})\}', chapter_text))
    for cid in used_cites:
        full_id = f"cite_{cid}"
        if full_id not in all_cite_ids:
            issues.append(FactCheckIssue(
                issue_type="hallucinated_citation",
                description=f"Citation ID {full_id} not found in citation database",
                severity="high",
            ))

    # Check for [VERIFY] markers
    verify_count = chapter_text.count("[VERIFY]")
    if verify_count > 0:
        issues.append(FactCheckIssue(
            issue_type="unverified_claims",
            description=f"{verify_count} claims marked as unverified",
            severity="medium",
        ))

    # Use LLM for deeper fact-checking
    llm_issues = await _llm_fact_check(chapter_text, citations)
    issues.extend(llm_issues)

    high_count = sum(1 for i in issues if i.severity == "high")
    medium_count = sum(1 for i in issues if i.severity == "medium")
    score = max(0, 100 - (high_count * 20) - (medium_count * 5))

    return FactCheckResult(
        score=score,
        pass_quality=score >= 70 and high_count == 0,
        issues=issues,
        uncited_claims=verify_count,
        hallucinated_citations=sum(1 for i in issues if i.issue_type == "hallucinated_citation"),
    )


async def _llm_fact_check(
    text: str,
    citations: list[Citation],
) -> list[FactCheckIssue]:
    """Use LLM to check for unsupported claims."""
    cite_list = "\n".join(
        f"{c.cite_id}: {c.title} ({c.year}) — {', '.join(c.authors[:2])}"
        for c in citations
    )

    prompt = f"""Fact-check this academic text against its citation database.

Citation database:
{cite_list}

Text:
---
{text[:3000]}
---

Check for:
1. Claims that appear factual but have no citation
2. Statistics or percentages without sources
3. Overconfident language ("proves", "indisputable", "always", "never")
4. Claims that don't match what the cited source likely says

Return JSON:
{{
  "issues": [
    {{"type": "...", "description": "...", "severity": "high|medium|low"}}
  ]
}}
Only include actual issues. Empty list if clean."""

    try:
        result = await call_llm_json(prompt=prompt, temperature=0.2)
        return [
            FactCheckIssue(
                issue_type=iss.get("type", "unknown"),
                description=iss.get("description", ""),
                severity=iss.get("severity", "low"),
            )
            for iss in result.get("issues", [])
        ]
    except Exception:
        return []

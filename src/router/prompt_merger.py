"""Merges base prompts + chapter config + style config into a final system prompt."""

from __future__ import annotations

from typing import Any


def build_system_prompt(
    base_prompt: str,
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
    job_config: dict[str, Any] | None = None,
) -> str:
    """Build the final system prompt by merging all layers.

    Args:
        base_prompt: The base agent markdown prompt (e.g. from prompts/base/writer.md).
        chapter_config: Chapter YAML config with sections, forbidden phrases, etc.
        style_config: Style YAML config with tone, formality, etc.
        job_config: Optional job-level config (topic, citation style, etc.).

    Returns:
        Merged system prompt string ready to send to the LLM.
    """
    parts: list[str] = []

    # Layer 1: Base prompt
    parts.append("=== WRITING INSTRUCTIONS ===\n")
    parts.append(base_prompt)

    # Layer 2: Style rules
    parts.append("\n\n=== STYLE CONFIGURATION ===\n")
    parts.append(_format_style(style_config))

    # Layer 3: Chapter structure rules
    parts.append("\n\n=== CHAPTER STRUCTURE ===\n")
    parts.append(_format_chapter(chapter_config))

    # Layer 4: Job context
    if job_config:
        parts.append("\n\n=== JOB CONTEXT ===\n")
        parts.append(_format_job(job_config))

    return "\n".join(parts)


def build_research_prompt(
    chapter_config: dict[str, Any],
    job_config: dict[str, Any],
) -> str:
    """Build a research query prompt from chapter and job config."""
    topic = job_config.get("topic", "research topic")
    chapter_name = chapter_config.get("name", "this chapter")
    sections = chapter_config.get("sections", [])

    queries: list[str] = []
    for section in sections:
        title = section.get("title", "")
        instructions = section.get("instructions", "")
        if title:
            queries.append(f"- {title}: {instructions}")

    queries_text = "\n".join(queries) if queries else "General research on the topic"

    return f"""Research task for chapter: {chapter_name}

Topic: {topic}
Paper type: {job_config.get('paper_type', 'literature_review')}
Citation style: {job_config.get('citation_style', 'apa')}

Research queries for this chapter:
{queries_text}

Find relevant academic papers and summarize key findings for each section.
Return a structured summary with paper metadata (authors, year, title, key findings).
Use citation IDs (cite_001, cite_002, etc.) for each unique source."""


def build_review_prompt(
    chapter_text: str,
    chapter_config: dict[str, Any],
    review_type: str = "style",
) -> str:
    """Build a review prompt for a chapter."""
    forbidden = chapter_config.get("forbidden", [])
    required = chapter_config.get("required", [])

    forbidden_text = "\n".join(f"  - \"{p}\"" for p in forbidden) if forbidden else "  (none specified)"
    required_text = "\n".join(f"  - {r}" for r in required) if required else "  (none specified)"

    if review_type == "style":
        return f"""Review this chapter for style consistency and quality.

FORBIDDEN phrases to check for:
{forbidden_text}

REQUIRED elements to verify:
{required_text}

Chapter text:
---
{chapter_text}
---

Check for:
1. Forbidden phrases (flag each occurrence)
2. Required elements (check if present)
3. Voice consistency (formal vs casual mixing)
4. Tense consistency
5. Passive voice overuse (> 20% is too much)
6. Bullet point overuse (> 3 per section is too much)
7. AI-typical phrases

Return a JSON object with:
{{
  "issues": [{{"type": "...", "line": N, "description": "...", "severity": "high|medium|low"}}],
  "score": 0-100,
  "pass": true/false,
  "rewrite_needed": ["section_ids"]
}}"""

    elif review_type == "fact_check":
        return f"""Fact-check this chapter against the research sources.

Chapter text:
---
{chapter_text}
---

Verify:
1. Every factual claim has a citation
2. Citation IDs are used correctly ({{cite_XXX}} format)
3. No invented statistics or data
4. Claims match what the cited sources actually say
5. No overconfident language without evidence

Return a JSON object with:
{{
  "issues": [{{"type": "...", "description": "...", "severity": "high|medium|low"}}],
  "score": 0-100,
  "pass": true/false
}}"""

    return ""


def _format_style(style: dict[str, Any]) -> str:
    """Format style config into readable instructions."""
    lines: list[str] = []

    tone = style.get("tone", "professional")
    lines.append(f"Tone: {tone}")

    formality = style.get("formality", 0.7)
    lines.append(f"Formality level: {formality} (0=casual, 1=fully formal)")

    voice = style.get("preferred_voice", "active")
    lines.append(f"Preferred voice: {voice}")

    intro_style = style.get("introduction_style", "standard")
    lines.append(f"Introduction style: {intro_style}")

    max_bullets = style.get("max_bullet_points_per_section", 2)
    lines.append(f"Max bullet points per section: {max_bullets}")

    forbidden = style.get("forbidden_phrases", [])
    if forbidden:
        lines.append("\nForbidden phrases (never use these):")
        for phrase in forbidden:
            lines.append(f"  - \"{phrase}\"")

    return "\n".join(lines)


def _format_chapter(chapter: dict[str, Any]) -> str:
    """Format chapter config into readable instructions."""
    lines: list[str] = []

    name = chapter.get("name", "Chapter")
    lines.append(f"Chapter: {name}")

    sections = chapter.get("sections", [])
    if sections:
        lines.append("\nSections:")
        for sec in sections:
            sid = sec.get("id", "?")
            title = sec.get("title", "Untitled")
            paras = sec.get("paragraphs", 2)
            wc = sec.get("word_count", 300)
            fmt = sec.get("format", "prose")
            instructions = sec.get("instructions", "")

            lines.append(f"\n  Section {sid}: {title}")
            lines.append(f"    Paragraphs: {paras}")
            lines.append(f"    Target word count: {wc}")
            lines.append(f"    Format: {fmt}")
            if instructions:
                lines.append(f"    Instructions: {instructions}")

    forbidden = chapter.get("forbidden", [])
    if forbidden:
        lines.append("\nForbidden phrases for this chapter:")
        for phrase in forbidden:
            lines.append(f"  - \"{phrase}\"")

    required = chapter.get("required", [])
    if required:
        lines.append("\nRequired elements:")
        for req in required:
            lines.append(f"  - {req}")

    return "\n".join(lines)


def _format_job(job: dict[str, Any]) -> str:
    """Format job config into readable context."""
    lines: list[str] = []
    for key in ["topic", "paper_type", "citation_style", "target_audience"]:
        if key in job:
            lines.append(f"{key.replace('_', ' ').title()}: {job[key]}")
    return "\n".join(lines)

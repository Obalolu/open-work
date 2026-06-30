"""Chapter writer — generates chapter content section-by-section with LLM."""

from __future__ import annotations

import re
from typing import Any, AsyncIterator

from src.router.prompt_merger import build_system_prompt
from src.research.summarizer import ResearchSummary, format_citations_for_prompt
from src.utils.llm_client import call_llm, stream_llm


async def write_chapter(
    base_prompt: str,
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
    research: ResearchSummary,
    job_config: dict[str, Any],
    previous_chapters: list[str] | None = None,
) -> str:
    """Write a complete chapter by generating each section individually.

    This allows different formats per section (prose, numbered_list, definitions).
    """
    chapter_name = chapter_config.get("name", "Chapter")
    sections = chapter_config.get("sections", [])

    system_prompt = build_system_prompt(base_prompt, chapter_config, style_config, job_config)
    citations_ref = format_citations_for_prompt(research)
    section_summaries = _build_section_summaries(research)
    prev_context = _build_previous_chapters_context(previous_chapters)

    all_sections: list[str] = []
    for i, section in enumerate(sections):
        section_text = await _write_section(
            section_config=section,
            chapter_name=chapter_name,
            system_prompt=system_prompt,
            citations_ref=citations_ref,
            section_summaries=section_summaries,
            prev_context=prev_context,
            style_config=style_config,
            job_config=job_config,
            section_index=i + 1,
            total_sections=len(sections),
        )
        all_sections.append(section_text)

    return "\n\n".join(all_sections)


async def stream_write_chapter(
    base_prompt: str,
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
    research: ResearchSummary,
    job_config: dict[str, Any],
    previous_chapters: list[str] | None = None,
    on_section_start: Any | None = None,
    on_section_done: Any | None = None,
) -> AsyncIterator[str]:
    """Stream a chapter being written, yielding text chunks as they arrive.

    Yields the section heading first, then LLM chunks for each section, then a
    blank line between sections. The caller is expected to assemble the final
    text from the chunks.
    """
    chapter_name = chapter_config.get("name", "Chapter")
    sections = chapter_config.get("sections", [])

    system_prompt = build_system_prompt(base_prompt, chapter_config, style_config, job_config)
    citations_ref = format_citations_for_prompt(research)
    section_summaries = _build_section_summaries(research)
    prev_context = _build_previous_chapters_context(previous_chapters)

    for i, section in enumerate(sections):
        if on_section_start:
            on_section_start(i + 1, len(sections), section)
        prompt = _build_section_prompt(
            section_config=section,
            chapter_name=chapter_name,
            citations_ref=citations_ref,
            section_summaries=section_summaries,
            prev_context=prev_context,
            section_index=i + 1,
            total_sections=len(sections),
        )
        async for chunk in stream_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=style_config.get("temperature", 0.7),
        ):
            yield chunk
        if on_section_done:
            on_section_done(i + 1, len(sections))
        if i < len(sections) - 1:
            yield "\n\n"


def _build_section_summaries(research: ResearchSummary) -> str:
    if not research.summaries:
        return ""
    return "\n\n".join(
        f"### Section {sid} research:\n{summary}"
        for sid, summary in research.summaries.items()
    )


def _build_previous_chapters_context(previous_chapters: list[str] | None) -> str:
    if not previous_chapters:
        return ""
    context = "\n\n=== PREVIOUS CHAPTERS (for context and continuity) ===\n"
    for i, ch in enumerate(previous_chapters, 1):
        context += f"\n--- Chapter {i} (first 500 words) ---\n"
        context += ch[:500] + "...\n"
    return context


def _build_section_prompt(
    *,
    section_config: dict[str, Any],
    chapter_name: str,
    citations_ref: str,
    section_summaries: str,
    prev_context: str,
    section_index: int,
    total_sections: int,
) -> str:
    sid = section_config.get("id", f"1.{section_index}")
    title = section_config.get("title", "Section")
    paras = section_config.get("paragraphs", 2)
    wc = section_config.get("word_count", 300)
    fmt = section_config.get("format", "prose")
    instructions = section_config.get("instructions", "")
    forbidden = section_config.get("forbidden", [])
    forbidden_text = ", ".join(f'"{p}"' for p in forbidden) if forbidden else "none"

    format_instructions = _get_format_instructions(fmt, paras, wc)

    return f"""Write section {sid}: {title}
This is section {section_index} of {total_sections} in Chapter: {chapter_name}.

{format_instructions}

Target word count: {wc} words (minimum)

Section-specific instructions:
{instructions}

Available citations:
{citations_ref}

{section_summaries}
{prev_context}

FORBIDDEN phrases: {forbidden_text}

IMPORTANT CITATION FORMAT:
Use placeholder citations in the format {{cite_XXX}} where XXX is the citation ID.
Examples:
- Single source: {{cite_001}}
- Multiple sources: {{cite_001}}; {{cite_002}}
- Do NOT use (Author, Year) inline citations
- Do NOT use [cite_XXX] square brackets
- The compiler will replace {{cite_XXX}} with (Author, Year) later

Write the section now. Start directly with the section heading ({sid} {title})."""


async def _write_section(
    section_config: dict[str, Any],
    chapter_name: str,
    system_prompt: str,
    citations_ref: str,
    section_summaries: str,
    prev_context: str,
    style_config: dict[str, Any],
    job_config: dict[str, Any],
    section_index: int,
    total_sections: int,
) -> str:
    """Write a single section with format-specific instructions."""
    prompt = _build_section_prompt(
        section_config=section_config,
        chapter_name=chapter_name,
        citations_ref=citations_ref,
        section_summaries=section_summaries,
        prev_context=prev_context,
        section_index=section_index,
        total_sections=total_sections,
    )
    return await call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=style_config.get("temperature", 0.7),
    )


def _get_format_instructions(fmt: str, paras: int, wc: int) -> str:
    """Return format-specific instructions based on section config."""
    if fmt == "numbered_list":
        return f"""FORMAT: Numbered list
- Start with a main objective/purpose statement as a paragraph
- Then list specific objectives as numbered items, EACH ON ITS OWN LINE
- Format each objective as:
1. Examine [what] among [who].
2. Determine [what] based on [variable].
3. Assess whether [hypothesis].
4. Evaluate [what] according to [variable].
- Each numbered item must start on a new line with the number
- Do NOT put all objectives on one line
- Do NOT use bullet points — use numbered format only
- Do NOT write additional paragraphs after the numbered list"""

    elif fmt == "definitions":
        return f"""FORMAT: Definitions
- Each variable gets its own definition paragraph
- Structure each definition as: Variable Name: Definition. In this study, it will be measured using the [Instrument Name] developed by (Author, Year). The scale assesses [description]. Higher scores indicate [meaning].
- Do NOT use bullet points — write each definition as a flowing paragraph
- Include at least {paras} variable definitions"""

    else:  # prose (default)
        return f"""FORMAT: Prose
- Write {paras} paragraphs of flowing academic prose
- Each paragraph should be 4-8 sentences
- Use transitions between paragraphs
- Do NOT use bullet points or numbered lists
- Do NOT include tables"""


async def write_section(
    section_config: dict[str, Any],
    chapter_config: dict[str, Any],
    style_config: dict[str, Any],
    citations_ref: str,
    section_research: str,
) -> str:
    """Write a single section within a chapter (legacy interface)."""
    system_prompt = build_system_prompt(
        "You are an expert academic writer. Write clear, evidence-based prose.",
        chapter_config,
        style_config,
        None,
    )

    return await _write_section(
        section_config=section_config,
        chapter_name=chapter_config.get("name", "Chapter"),
        system_prompt=system_prompt,
        citations_ref=citations_ref,
        section_summaries=section_research,
        prev_context="",
        style_config=style_config,
        job_config={},
        section_index=1,
        total_sections=1,
    )

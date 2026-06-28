"""Summarizes research papers into structured citation databases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.research.orchestrator import Citation, ResearchSummary
from src.research.semantic_scholar import SemanticScholarClient


async def summarize_papers(
    papers: list[dict] | list[Citation],
    section_instructions: dict[str, str] | None = None,
) -> ResearchSummary:
    """Summarize a list of papers into a structured research summary.

    Args:
        papers: List of paper metadata dicts or Citation objects.
        section_instructions: Optional mapping of section_id -> research focus.

    Returns:
        ResearchSummary with citation database and per-section summaries.
    """
    # Convert dicts to Citations if needed
    citations: list[Citation] = []
    for i, paper in enumerate(papers):
        if isinstance(paper, Citation):
            paper.cite_id = f"cite_{i + 1:03d}"
            citations.append(paper)
        elif isinstance(paper, dict):
            citations.append(Citation(
                cite_id=f"cite_{i + 1:03d}",
                title=paper.get("title", ""),
                authors=paper.get("authors", []),
                year=paper.get("year"),
                venue=paper.get("journal", "") or paper.get("venue", ""),
                abstract_summary=(paper.get("abstract") or "")[:300],
                paper_url=paper.get("url", ""),
                paper_id=paper.get("doi", "") or paper.get("url", ""),
                doi=paper.get("doi", ""),
                source_type=paper.get("source_type", "journal"),
                citation_count=paper.get("citation_count", 0),
                confidence=paper.get("confidence", 0.0),
            ))

    # Build paper list for summarization
    paper_list = "\n".join(
        f"[{c.cite_id}] {c.title} ({c.year}) — {', '.join(c.authors[:3])}{'...' if len(c.authors) > 3 else ''}\n"
        f"  Venue: {c.venue}\n"
        f"  Summary: {c.abstract_summary}"
        for c in citations
    )

    # Generate summaries per section
    summaries: dict[str, str] = {}
    if section_instructions:
        for section_id, focus in section_instructions.items():
            summary = await _summarize_for_section(paper_list, focus)
            summaries[section_id] = summary
    else:
        summary = await _summarize_for_section(paper_list, "general research overview")
        summaries["general"] = summary

    return ResearchSummary(
        citations=citations,
        summaries=summaries,
        raw_results=[],
    )


async def _summarize_for_section(paper_list: str, focus: str) -> str:
    """Use LLM to summarize papers relevant to a specific section focus."""
    prompt = f"""Summarize the following research papers with focus on: {focus}

Papers:
{paper_list}

Provide a concise summary (200-400 words) covering:
1. Key findings relevant to the focus area
2. Methodological approaches used
3. Gaps or limitations identified
4. How these papers relate to each other

Use citation IDs [cite_XXX] when referencing specific papers."""

    from src.utils.llm_client import call_llm
    return await call_llm(
        prompt=prompt,
        system_prompt="You are a research assistant. Provide concise, factual summaries grounded in the provided papers.",
        temperature=0.3,
    )


def format_citation_database(research: ResearchSummary) -> str:
    """Format the citation database as a markdown reference."""
    lines = ["# Citation Database\n"]
    for c in research.citations:
        authors_str = ", ".join(c.authors[:3])
        if len(c.authors) > 3:
            authors_str += " et al."
        lines.append(f"**{c.cite_id}**: {c.title} ({c.year}). {authors_str}. {c.venue}.")
        lines.append(f"  URL: {c.paper_url}\n")
    return "\n".join(lines)


def format_citations_for_prompt(research: ResearchSummary) -> str:
    """Format citations as (Author, Year) reference block for the writer prompt.

    The LLM uses these to generate inline (Author, Year) citations directly.
    """
    lines: list[str] = []
    for c in research.citations:
        # Build author string: (Last, Last, Last) or (Last et al.)
        if not c.authors:
            author_str = "Unknown"
        elif len(c.authors) <= 3:
            # Format: Smith, Jones, & Williams
            last_names = [a.split()[-1] for a in c.authors]
            if len(last_names) == 1:
                author_str = last_names[0]
            elif len(last_names) == 2:
                author_str = f"{last_names[0]} & {last_names[1]}"
            else:
                author_str = ", ".join(last_names[:-1]) + f", & {last_names[-1]}"
        else:
            author_str = f"{c.authors[0].split()[-1]} et al."

        year = c.year or "n.d."
        doi_str = f" DOI: {c.doi}" if c.doi else ""
        lines.append(f"[{c.cite_id}] {author_str} ({year}). {c.title}.{doi_str}")
    return "\n".join(lines)

"""Citation compiler — replaces {cite_XXX} IDs with formatted citations."""

from __future__ import annotations

import re
from typing import Any

from src.research.summarizer import Citation


CITE_PATTERN = re.compile(r'\{cite_(\d{3})\}')


def compile_citations(
    text: str,
    citations: list[Citation],
    style: str = "apa",
) -> str:
    """Replace citation IDs with formatted citations and append reference list.

    Args:
        text: Text containing {cite_XXX} placeholders.
        citations: List of Citation objects.
        style: Citation style ("apa", "mla", "chicago", "ieee").

    Returns:
        Text with formatted citations and a reference list appended.
    """
    citation_map = {c.cite_id: c for c in citations}

    def replace_cite(match: re.Match) -> str:
        cite_id = f"cite_{match.group(1)}"
        citation = citation_map.get(cite_id)
        if not citation:
            return match.group(0)  # Leave unchanged if not found
        return _format_inline(citation, style)

    compiled = CITE_PATTERN.sub(replace_cite, text)

    # Build reference list from actually cited IDs
    cited_ids = set(CITE_PATTERN.findall(text))
    cited_citations = [
        citation_map[f"cite_{cid}"]
        for cid in sorted(cited_ids)
        if f"cite_{cid}" in citation_map
    ]

    if cited_citations:
        ref_list = _build_reference_list(cited_citations, style)
        compiled = compiled.rstrip() + "\n\n---\n\n" + ref_list

    return compiled


def _format_inline(citation: Citation, style: str) -> str:
    """Format a single inline citation."""
    authors = citation.authors
    year = citation.year or "n.d."

    if style == "apa":
        if len(authors) == 0:
            return f"({year})"
        elif len(authors) == 1:
            last = authors[0].split()[-1]
            return f"({last}, {year})"
        elif len(authors) == 2:
            last1 = authors[0].split()[-1]
            last2 = authors[1].split()[-1]
            return f"({last1} & {last2}, {year})"
        else:
            last1 = authors[0].split()[-1]
            return f"({last1} et al., {year})"

    elif style == "mla":
        if len(authors) == 0:
            return f"({citation.title})"
        elif len(authors) == 1:
            last = authors[0].split()[-1]
            return f"({last})"
        else:
            last1 = authors[0].split()[-1]
            return f"({last1} et al.)"

    elif style == "ieee":
        # IEEE uses numbered references — return the cite ID as-is for now
        return f"[{citation.cite_id.replace('cite_', '')}]"

    elif style == "chicago":
        if len(authors) == 0:
            return f"({citation.title}, {year})"
        last = authors[0].split()[-1]
        return f"({last} {year})"

    # Default to APA
    if authors:
        last = authors[0].split()[-1]
        return f"({last}, {year})"
    return f"({year})"


def _build_reference_list(citations: list[Citation], style: str) -> str:
    """Build a formatted reference list."""
    lines = ["# References\n"]

    for c in sorted(citations, key=lambda x: x.authors[0].split()[-1] if x.authors else ""):
        if style == "apa":
            ref = _format_apa(c)
        elif style == "mla":
            ref = _format_mla(c)
        elif style == "ieee":
            ref = _format_ieee(c)
        elif style == "chicago":
            ref = _format_chicago(c)
        else:
            ref = _format_apa(c)
        lines.append(ref)

    return "\n\n".join(lines)


def _format_apa(c: Citation) -> str:
    """Format a reference in APA 7th edition style."""
    authors = c.authors
    year = c.year or "n.d."

    if len(authors) == 0:
        author_str = ""
    elif len(authors) == 1:
        author_str = _format_author_apa(authors[0])
    elif len(authors) == 2:
        author_str = f"{_format_author_apa(authors[0])}, & {_format_author_apa(authors[1])}"
    elif len(authors) <= 20:
        author_str = ", ".join(_format_author_apa(a) for a in authors[:-1])
        author_str += f", & {_format_author_apa(authors[-1])}"
    else:
        author_str = ", ".join(_format_author_apa(a) for a in authors[:19])
        author_str += f", ... {_format_author_apa(authors[-1])}"

    venue = f". {c.venue}" if c.venue else ""
    return f"{author_str} ({year}). {c.title}{venue}."


def _format_author_apa(name: str) -> str:
    """Format a single author name in APA style: Last, F. M."""
    parts = name.strip().split()
    if len(parts) == 0:
        return name
    if len(parts) == 1:
        return parts[0]
    last = parts[-1]
    initials = " ".join(f"{p[0]}." for p in parts[:-1] if p)
    return f"{last}, {initials}"


def _format_mla(c: Citation) -> str:
    """Format a reference in MLA style."""
    authors = c.authors
    if len(authors) == 0:
        author_str = ""
    elif len(authors) == 1:
        author_str = authors[0]
    elif len(authors) == 2:
        author_str = f"{authors[0]}, and {authors[1]}"
    else:
        author_str = f"{authors[0]}, et al."

    return f"{author_str}. \"{c.title}.\" {c.venue}. {c.year}."


def _format_ieee(c: Citation) -> str:
    """Format a reference in IEEE style."""
    authors = ", ".join(c.authors[:6])
    if len(c.authors) > 6:
        authors += ", et al."
    year = c.year or "n.d."
    return f"{authors}, \"{c.title},\" {c.venue}, {year}."


def _format_chicago(c: Citation) -> str:
    """Format a reference in Chicago style."""
    authors = c.authors
    if len(authors) == 0:
        author_str = ""
    elif len(authors) == 1:
        author_str = authors[0]
    elif len(authors) <= 10:
        author_str = ", ".join(authors[:-1]) + f", and {authors[-1]}"
    else:
        author_str = ", ".join(authors[:7]) + f", et al."

    return f"{author_str}. \"{c.title}.\" {c.venue} ({c.year})."

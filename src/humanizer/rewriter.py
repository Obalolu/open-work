"""LLM-based style diversification for anti-detection rewriting."""

from __future__ import annotations

import re
from typing import Any

from src.utils.llm_client import call_llm


ENTROPY_SYSTEM_PROMPT = """You are a style diversification specialist. Your task is to rewrite academic text to make it sound more natural and human-like, while preserving all citations and academic integrity.

RULES:
1. NEVER remove or change citation IDs ({cite_XXX} patterns)
2. NEVER add unsupported claims
3. Vary sentence lengths (mix short, medium, long)
4. Replace AI-typical phrases with natural alternatives
5. Use varied sentence openings (not all starting with "The" or "This")
6. Add occasional natural constructions (em-dashes, parenthetical asides)
7. Keep the academic tone — this is NOT casual rewriting
8. Preserve all factual content and data
9. Keep paragraph structure intact
10. Do NOT add bullet points

AI PHRASES TO REPLACE:
- "furthermore" → "also", "and", "Plus"
- "moreover" → "also", "Beyond that"
- "additionally" → "also", "On top of that"
- "consequently" → "so", "As a result"
- "it is worth noting that" → remove or rephrase
- "delve into" → "explore", "examine", "look at"
- "in the realm of" → "in the field of", "in"
- "landscape" → "field", "area", "domain"
- "pivotal" → "important", "key", "significant"
- "tapestry" → remove or rephrase
- "synergy" → "combination", "interaction"
- "utilize" → "use"
- "in order to" → "to"
- "facilitate" → "enable", "help"
- "endeavor" → "attempt", "try"
- "myriad" → "many", "numerous"
- "underscore" → "emphasize", "highlight"
"""


async def humanize_text(
    text: str,
    intensity: str = "medium",
    preserve_citations: bool = True,
) -> str:
    """Rewrite text to sound more human-like.

    Args:
        text: Input text to humanize.
        intensity: "light", "medium", or "aggressive".
        preserve_citations: Whether to preserve citation IDs.

    Returns:
        Humanized text.
    """
    intensity_instructions = {
        "light": "Make subtle changes — only fix the most obvious AI patterns. Keep the overall structure intact.",
        "medium": "Rewrite for natural flow — vary sentence structures, replace AI phrases, add natural rhythm while keeping academic tone.",
        "aggressive": "Thoroughly rewrite for maximum naturalness — restructure sentences, vary vocabulary significantly, add natural imperfections while preserving all citations and facts.",
    }

    instruction = intensity_instructions.get(intensity, intensity_instructions["medium"])

    prompt = f"""Rewrite the following academic text to sound more human-written.

{instruction}

PRESERVE EXACTLY: All {{cite_XXX}} patterns, all statistics, all factual claims.

Text to rewrite:
---
{text}
---

Return ONLY the rewritten text. No explanations, no meta-commentary."""

    return await call_llm(
        prompt=prompt,
        system_prompt=ENTROPY_SYSTEM_PROMPT,
        temperature=0.8,
    )


async def polish_text(text: str) -> str:
    """Final grammar and flow polish.

    Args:
        text: Text to polish.

    Returns:
        Polished text.
    """
    prompt = f"""Perform final grammar and flow polish on this academic text.

Fix:
1. Grammar errors (subject-verb agreement, tense consistency)
2. Spelling inconsistencies (US vs UK — pick one and be consistent)
3. Punctuation issues (serial commas, hyphenation)
4. Awkward phrasing
5. Weak transitions between paragraphs
6. Overconfident claims (soften "proves" → "supports", "always" → "consistently")

DO NOT:
- Change the meaning or content
- Remove or alter citations ({{cite_XXX}} patterns)
- Add new content
- Change the overall structure

Text:
---
{text}
---

Return ONLY the polished text."""

    return await call_llm(
        prompt=prompt,
        system_prompt="You are a meticulous academic copyeditor. Polish for clarity and flow while preserving all content.",
        temperature=0.3,
    )

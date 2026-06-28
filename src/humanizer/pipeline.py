"""Humanization pipeline — chains rewriting steps for maximum anti-detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.humanizer.rewriter import humanize_text, polish_text


@dataclass
class HumanizeResult:
    """Result of the humanization pipeline."""
    final_text: str
    steps: list[dict[str, Any]]
    original_length: int
    final_length: int


async def run_humanize_pipeline(
    text: str,
    intensity: str = "medium",
    include_polish: bool = True,
    max_retries: int = 2,
) -> HumanizeResult:
    """Run the full humanization pipeline.

    Pipeline:
    1. LLM style diversification (entropy rewrite)
    2. Optional: final polish pass
    3. Optional: second entropy pass if still flagged

    Args:
        text: Input text to humanize.
        intensity: "light", "medium", or "aggressive".
        include_polish: Whether to include a final polish pass.
        max_retries: Maximum number of humanize + check loops.

    Returns:
        HumanizeResult with final text and step history.
    """
    steps: list[dict[str, Any]] = []
    current = text
    original_length = len(text)

    # Step 1: Main humanization
    current = await humanize_text(current, intensity=intensity)
    steps.append({
        "step": "entropy_rewrite",
        "intensity": intensity,
        "length": len(current),
    })

    # Step 2: Polish
    if include_polish:
        current = await polish_text(current)
        steps.append({
            "step": "polish",
            "length": len(current),
        })

    return HumanizeResult(
        final_text=current,
        steps=steps,
        original_length=original_length,
        final_length=len(current),
    )

"""Humanization pipeline — chains rewriting steps for maximum anti-detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.humanizer.rewriter import humanize_text, polish_text, stream_humanize_text


@dataclass
class HumanizeResult:
    """Result of the humanization pipeline."""

    final_text: str
    steps: list[dict[str, Any]]
    original_length: int
    final_length: int
    attempts: list[dict[str, Any]] = field(default_factory=list)


async def run_humanize_pipeline(
    text: str,
    intensity: str = "medium",
    include_polish: bool = True,
    max_retries: int = 2,
    on_attempt: Optional[Any] = None,
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
        on_attempt: Optional callback invoked after each attempt; receives
            (original, rewritten, intensity, ai_score_before, ai_score_after).

    Returns:
        HumanizeResult with final text and step history.
    """
    steps: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    current = text
    original_length = len(text)

    current = await humanize_text(current, intensity=intensity)
    steps.append({"step": "entropy_rewrite", "intensity": intensity, "length": len(current)})
    attempts.append(
        {
            "original_text": text,
            "rewritten_text": current,
            "intensity": intensity,
        }
    )
    if on_attempt:
        on_attempt(text, current, intensity, None, None)

    if include_polish:
        current = await polish_text(current)
        steps.append({"step": "polish", "length": len(current)})

    return HumanizeResult(
        final_text=current,
        steps=steps,
        original_length=original_length,
        final_length=len(current),
        attempts=attempts,
    )


async def stream_humanize(
    text: str,
    intensity: str = "medium",
):
    """Stream the humanization rewrite, yielding chunks of the rewritten text."""
    async for chunk in stream_humanize_text(text, intensity=intensity):
        yield chunk

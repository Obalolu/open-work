"""Loads YAML prompt templates and base markdown prompts from disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.config import get_prompts_dir


def load_chapter_template(chapter_file: str | Path) -> dict[str, Any]:
    """Load a chapter YAML template.

    Args:
        chapter_file: Filename or path relative to prompts/chapters/.
            E.g. "chapter_1.yaml" or a full Path.

    Returns:
        Parsed YAML dict with chapter structure rules.
    """
    path = _resolve(chapter_file, "chapters")
    return _load_yaml(path)


def load_style_template(style_file: str | Path) -> dict[str, Any]:
    """Load a writing style YAML template.

    Args:
        style_file: Filename or path relative to prompts/styles/.

    Returns:
        Parsed YAML dict with style rules.
    """
    path = _resolve(style_file, "styles")
    return _load_yaml(path)


def load_base_prompt(agent_name: str) -> str:
    """Load a base agent prompt (markdown) from prompts/base/.

    Args:
        agent_name: Name of the agent, e.g. "writer", "researcher", "reviewer".

    Returns:
        Raw markdown prompt string.
    """
    prompts_dir = get_prompts_dir()
    path = prompts_dir / "base" / f"{agent_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Base prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def load_humanizer_prompt(agent_name: str) -> str:
    """Load a humanizer prompt from prompts/humanizer/."""
    prompts_dir = get_prompts_dir()
    path = prompts_dir / "humanizer" / f"{agent_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Humanizer prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def list_chapter_templates() -> list[str]:
    """List available chapter template files."""
    chapters_dir = get_prompts_dir() / "chapters"
    if not chapters_dir.exists():
        return []
    return sorted(f.name for f in chapters_dir.glob("*.yaml"))


def list_style_templates() -> list[str]:
    """List available style template files."""
    styles_dir = get_prompts_dir() / "styles"
    if not styles_dir.exists():
        return []
    return sorted(f.name for f in styles_dir.glob("*.yaml"))


def _resolve(file_ref: str | Path, subdir: str) -> Path:
    """Resolve a file reference to an absolute path."""
    prompts_dir = get_prompts_dir()
    p = Path(file_ref)
    if p.is_absolute():
        return p
    return prompts_dir / subdir / p


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"YAML template not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

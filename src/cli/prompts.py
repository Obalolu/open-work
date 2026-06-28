"""Interactive prompts using InquirerPy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from InquirerPy.separator import Separator

from src.router.prompt_loader import list_chapter_templates, list_style_templates
from src.config import load_yaml, get_jobs_dir


def select_job(existing_jobs: list[str]) -> str | None:
    """Interactive job selection."""
    choices = existing_jobs + [Separator(), "Create new job"]
    result = inquirer.select(
        message="Select a job:",
        choices=choices,
        default=existing_jobs[0] if existing_jobs else None,
    ).execute()
    return result


def select_chapters(max_chapter: int = 10) -> list[int]:
    """Interactive chapter selection (multi-select)."""
    choices = [
        {"name": f"Chapter {i}", "value": i}
        for i in range(1, max_chapter + 1)
    ]
    result = inquirer.checkbox(
        message="Select chapters to generate:",
        choices=choices,
        default=[1],
    ).execute()
    return result


def select_style() -> str:
    """Interactive style selection."""
    templates = list_style_templates()
    if not templates:
        return "academic_balanced.yaml"
    result = inquirer.select(
        message="Select writing style:",
        choices=templates,
        default=templates[0] if templates else None,
    ).execute()
    return result


def select_output_formats() -> list[str]:
    """Interactive output format selection."""
    result = inquirer.checkbox(
        message="Select output formats:",
        choices=[
            {"name": "Markdown (.md)", "value": "md"},
            {"name": "Word (.docx)", "value": "docx"},
            {"name": "PDF (.pdf)", "value": "pdf"},
        ],
        default=["md"],
    ).execute()
    return result


def confirm_action(message: str) -> bool:
    """Interactive confirmation."""
    return inquirer.confirm(message=message, default=True).execute()


def text_input(message: str, default: str = "") -> str:
    """Interactive text input."""
    return inquirer.text(message=message, default=default).execute()


def get_new_job_config() -> dict[str, Any]:
    """Interactive new job creation."""
    topic = text_input("Research topic:")
    if not topic:
        return {}

    paper_type = inquirer.select(
        message="Paper type:",
        choices=[
            {"name": "Literature Review", "value": "literature_review"},
            {"name": "Empirical Study (IMRaD)", "value": "empirical_study"},
            {"name": "Theoretical Paper", "value": "theoretical"},
            {"name": "Mixed Methods", "value": "mixed_methods"},
            {"name": "Technical Report", "value": "technical_report"},
        ],
    ).execute()

    citation_style = inquirer.select(
        message="Citation style:",
        choices=[
            {"name": "APA 7th Edition", "value": "apa"},
            {"name": "MLA", "value": "mla"},
            {"name": "IEEE", "value": "ieee"},
            {"name": "Chicago", "value": "chicago"},
        ],
    ).execute()

    audience = inquirer.select(
        message="Target audience:",
        choices=[
            {"name": "Graduate Students", "value": "graduate_students"},
            {"name": "Researchers / Academics", "value": "researchers"},
            {"name": "General Academic", "value": "general_academic"},
            {"name": "Industry Professionals", "value": "industry"},
        ],
    ).execute()

    return {
        "topic": topic,
        "paper_type": paper_type,
        "citation_style": citation_style,
        "target_audience": audience,
    }


def get_job_name() -> str:
    """Get a name for a new job."""
    name = text_input("Job name (e.g., my_healthcare_paper):")
    return name.strip().replace(" ", "_").lower() if name else "untitled_job"

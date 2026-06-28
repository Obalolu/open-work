"""Export module — writes chapters to various formats."""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.config import get_output_dir


def export_markdown(
    content: str,
    output_path: Path,
    filename: str = "chapter.md",
) -> Path:
    """Export content as a Markdown file."""
    target = output_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def export_docx(
    content: str,
    output_path: Path,
    filename: str = "chapter.docx",
) -> Path:
    """Export content as a Word document via Pandoc."""
    target = output_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)

    md_path = output_path / "_temp.md"
    md_path.write_text(content, encoding="utf-8")

    try:
        subprocess.run(
            ["pandoc", str(md_path), "-o", str(target), "--wrap=none"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Pandoc not installed — save as markdown with .docx note
        note_path = output_path / f"{filename}.md"
        note_path.write_text(
            f"<!-- Export to DOCX requires Pandoc. Install: apt install pandoc -->\n\n{content}",
            encoding="utf-8",
        )
        target = note_path
    finally:
        md_path.unlink(missing_ok=True)

    return target


def export_pdf(
    content: str,
    output_path: Path,
    filename: str = "chapter.pdf",
) -> Path:
    """Export content as PDF via Pandoc."""
    target = output_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)

    md_path = output_path / "_temp.md"
    md_path.write_text(content, encoding="utf-8")

    try:
        subprocess.run(
            ["pandoc", str(md_path), "-o", str(target),
             "--pdf-engine=xelatex", "-V", "geometry:margin=1in"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        note_path = output_path / f"{filename}.md"
        note_path.write_text(
            f"<!-- Export to PDF requires Pandoc + XeLaTeX -->\n\n{content}",
            encoding="utf-8",
        )
        target = note_path
    finally:
        md_path.unlink(missing_ok=True)

    return target


def export_chapter(
    content: str,
    job_name: str,
    chapter_id: int | str,
    formats: list[str] | None = None,
) -> dict[str, Path]:
    """Export a chapter in multiple formats.

    Args:
        content: Chapter markdown content.
        job_name: Job name (used as output directory).
        chapter_id: Chapter number or identifier.
        formats: List of formats to export ("md", "docx", "pdf").

    Returns:
        Dict mapping format to output file path.
    """
    if formats is None:
        formats = ["md"]

    output_dir = get_output_dir() / job_name
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Path] = {}
    base_name = f"chapter_{chapter_id}"

    for fmt in formats:
        if fmt == "md":
            results["md"] = export_markdown(content, output_dir, f"{base_name}.md")
        elif fmt == "docx":
            results["docx"] = export_docx(content, output_dir, f"{base_name}.docx")
        elif fmt == "pdf":
            results["pdf"] = export_pdf(content, output_dir, f"{base_name}.pdf")

    return results

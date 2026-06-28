"""Chapter operations — read content from output files."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from api.models import Chapter
from src.config import get_output_dir


def get_chapter(db: Session, job_id: str, chapter_number: int) -> Chapter | None:
    return (
        db.query(Chapter)
        .filter(Chapter.job_id == job_id, Chapter.chapter_number == chapter_number)
        .first()
    )


def get_chapter_content(job_id: str, chapter_number: int) -> str:
    output_dir = get_output_dir() / job_id
    compiled = output_dir / f"chapter_{chapter_number}_compiled.md"
    raw = output_dir / f"chapter_{chapter_number}.md"
    v2 = output_dir / f"chapter_{chapter_number}_v2.md"

    for path in [compiled, v2, raw]:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def get_references(job_id: str) -> str:
    refs_path = get_output_dir() / job_id / "references.md"
    if refs_path.exists():
        return refs_path.read_text(encoding="utf-8")
    return ""


def list_chapter_files(job_id: str) -> dict[int, list[str]]:
    output_dir = get_output_dir() / job_id
    if not output_dir.exists():
        return {}
    result: dict[int, list[str]] = {}
    for f in sorted(output_dir.iterdir()):
        if f.name.startswith("chapter_") and f.suffix == ".md":
            try:
                num = int(f.name.split("_")[1].split("_")[0].split(".")[0])
                result.setdefault(num, []).append(f.name)
            except (IndexError, ValueError):
                continue
    return result

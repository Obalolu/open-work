"""Chapter operations — read content from output files, save edits."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from api.models import Chapter, ChapterContentRevision, HumanizerAttempt
from src.config import get_output_dir
from src.reviewers.ai_detector import detect_ai_text


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


def save_chapter_edit(
    db: Session,
    job_id: str,
    chapter_number: int,
    content: str,
    source: str = "tiptap",
    summary: str | None = None,
) -> Chapter:
    """Persist an edited chapter and create a content revision row.

    Updates the markdown output file too so exports stay in sync.
    """
    chapter = get_chapter(db, job_id, chapter_number)
    if not chapter:
        raise ValueError(f"Chapter {chapter_number} not found for job {job_id}")

    word_count = len(content.split())
    chapter.content = content
    chapter.word_count = word_count
    try:
        detection = detect_ai_text(content)
        chapter.ai_score = detection.score
    except Exception:
        pass

    revision = ChapterContentRevision(
        chapter_id=chapter.id,
        content=content,
        source=source,
        summary=summary or "",
        word_count=word_count,
        ai_score=chapter.ai_score,
    )
    db.add(revision)
    db.commit()
    db.refresh(chapter)

    # Mirror to disk so MD/DOCX/PDF exports still reflect the latest edit.
    output_dir = get_output_dir() / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"chapter_{chapter_number}.md"
    md_path.write_text(content, encoding="utf-8")

    return chapter


def list_revisions(db: Session, chapter_id: int) -> list[ChapterContentRevision]:
    return (
        db.query(ChapterContentRevision)
        .filter(ChapterContentRevision.chapter_id == chapter_id)
        .order_by(ChapterContentRevision.created_at.desc())
        .all()
    )


def get_revision(db: Session, revision_id: int) -> ChapterContentRevision | None:
    return (
        db.query(ChapterContentRevision)
        .filter(ChapterContentRevision.id == revision_id)
        .first()
    )


def list_humanizer_attempts(db: Session, chapter_id: int) -> list[HumanizerAttempt]:
    return (
        db.query(HumanizerAttempt)
        .filter(HumanizerAttempt.chapter_id == chapter_id)
        .order_by(HumanizerAttempt.created_at.desc())
        .all()
    )

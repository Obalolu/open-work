"""Chapter read + edit routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import (
    ChapterDetail,
    ChapterRevisionDetail,
    ChapterRevisionSummary,
    ChapterSummary,
    ChapterUpdate,
    HumanizerAttemptSummary,
)
from api.services import chapter_service, job_service
from api.models import Chapter

router = APIRouter()


@router.get("/{job_id}/chapters", response_model=list[dict])
def list_chapters(job_id: str, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_service.sync_chapters_from_output(db, job_id)
    return [
        ChapterSummary(
            id=ch.id,
            chapter_number=ch.chapter_number,
            name=ch.name,
            status=ch.status,
            word_count=ch.word_count,
            ai_score=ch.ai_score,
            style_score=ch.style_score,
        )
        for ch in sorted(job.chapters, key=lambda c: c.chapter_number)
    ]


@router.get("/{job_id}/chapters/{chapter_number}", response_model=ChapterDetail)
def get_chapter(job_id: str, chapter_number: int, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_service.sync_chapters_from_output(db, job_id)
    ch = chapter_service.get_chapter(db, job_id, chapter_number)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapter not found")

    content = ch.content or chapter_service.get_chapter_content(job_id, chapter_number)

    return ChapterDetail(
        id=ch.id,
        chapter_number=ch.chapter_number,
        name=ch.name,
        status=ch.status,
        word_count=ch.word_count,
        ai_score=ch.ai_score,
        style_score=ch.style_score,
        content=content,
        created_at=ch.created_at,
        updated_at=ch.updated_at,
    )


@router.patch("/{job_id}/chapters/{chapter_number}", response_model=ChapterDetail)
def update_chapter(
    job_id: str,
    chapter_number: int,
    data: ChapterUpdate,
    db: Session = Depends(get_db),
):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        chapter = chapter_service.save_chapter_edit(
            db=db,
            job_id=job_id,
            chapter_number=chapter_number,
            content=data.content,
            source=data.source,
            summary=data.summary,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ChapterDetail(
        id=chapter.id,
        chapter_number=chapter.chapter_number,
        name=chapter.name,
        status=chapter.status,
        word_count=chapter.word_count,
        ai_score=chapter.ai_score,
        style_score=chapter.style_score,
        content=chapter.content or "",
        created_at=chapter.created_at,
        updated_at=chapter.updated_at,
    )


@router.get(
    "/{job_id}/chapters/{chapter_number}/revisions",
    response_model=list[ChapterRevisionSummary],
)
def list_chapter_revisions(
    job_id: str, chapter_number: int, db: Session = Depends(get_db)
):
    ch = chapter_service.get_chapter(db, job_id, chapter_number)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapter not found")
    revisions = chapter_service.list_revisions(db, ch.id)
    return [
        ChapterRevisionSummary(
            id=r.id,
            source=r.source,
            summary=r.summary or "",
            word_count=r.word_count,
            ai_score=r.ai_score,
            created_at=r.created_at,
        )
        for r in revisions
    ]


@router.get(
    "/{job_id}/chapters/{chapter_number}/revisions/{revision_id}",
    response_model=ChapterRevisionDetail,
)
def get_chapter_revision(
    job_id: str,
    chapter_number: int,
    revision_id: int,
    db: Session = Depends(get_db),
):
    ch = chapter_service.get_chapter(db, job_id, chapter_number)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapter not found")
    rev = chapter_service.get_revision(db, revision_id)
    if not rev or rev.chapter_id != ch.id:
        raise HTTPException(status_code=404, detail="Revision not found")
    return ChapterRevisionDetail(
        id=rev.id,
        source=rev.source,
        summary=rev.summary or "",
        word_count=rev.word_count,
        ai_score=rev.ai_score,
        created_at=rev.created_at,
        content=rev.content,
    )


@router.get(
    "/{job_id}/chapters/{chapter_number}/humanizer-attempts",
    response_model=list[HumanizerAttemptSummary],
)
def list_humanizer_attempts(
    job_id: str, chapter_number: int, db: Session = Depends(get_db)
):
    ch = chapter_service.get_chapter(db, job_id, chapter_number)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapter not found")
    attempts = chapter_service.list_humanizer_attempts(db, ch.id)
    return [
        HumanizerAttemptSummary(
            id=a.id,
            intensity=a.intensity,
            ai_score_before=a.ai_score_before,
            ai_score_after=a.ai_score_after,
            created_at=a.created_at,
        )
        for a in attempts
    ]


@router.get("/{job_id}/references")
def get_references(job_id: str, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    refs = chapter_service.get_references(job_id)
    if not refs:
        raise HTTPException(status_code=404, detail="No references found")
    return {"content": refs}

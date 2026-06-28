"""Chapter read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ChapterDetail
from api.services import chapter_service, job_service

router = APIRouter()


@router.get("/{job_id}/chapters", response_model=list[dict])
def list_chapters(job_id: str, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_service.sync_chapters_from_output(db, job_id)
    return [
        {
            "id": ch.id,
            "chapter_number": ch.chapter_number,
            "name": ch.name,
            "status": ch.status,
            "word_count": ch.word_count,
            "ai_score": ch.ai_score,
            "style_score": ch.style_score,
        }
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


@router.get("/{job_id}/references")
def get_references(job_id: str):
    refs = chapter_service.get_references(job_id)
    if not refs:
        raise HTTPException(status_code=404, detail="No references found")
    return {"content": refs}

"""Generation trigger + polling routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ChapterGenStatus, GenerateRequest, GenerationStatus
from api.services import job_service, pipeline_service
from api.services.pipeline_service import get_active_run_for_job

router = APIRouter()


@router.post("/{job_id}/generate", response_model=dict)
def start_generation(job_id: str, data: GenerateRequest, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    active = get_active_run_for_job(db, job_id)
    if active:
        raise HTTPException(status_code=409, detail=f"Generation already in progress (run {active.id})")

    chapters = data.chapters
    if not chapters:
        job_chapters = job_service.sync_chapters_from_output(db, job_id) or []
        from api.models import Chapter
        db_chapters = db.query(Chapter).filter(Chapter.job_id == job_id).all()
        chapters = [ch.chapter_number for ch in db_chapters]

    run_id = pipeline_service.start_generation(
        db=db,
        job_id=job_id,
        chapter_numbers=chapters,
        style_file=data.style,
        skip_humanize=data.skip_humanize,
        skip_review=data.skip_review,
    )

    job.status = "generating"
    db.commit()

    return {"run_id": run_id, "status": "started"}


@router.get("/{job_id}/generate/status")
def get_generation_status(job_id: str, db: Session = Depends(get_db)):
    active = get_active_run_for_job(db, job_id)
    if not active:
        all_runs = (
            db.query(pipeline_service.GenerationRun)
            .filter(pipeline_service.GenerationRun.job_id == job_id)
            .order_by(pipeline_service.GenerationRun.started_at.desc())
            .limit(1)
            .all()
        )
        if all_runs:
            last = all_runs[0]
            return GenerationStatus(
                run_id=last.id,
                job_id=job_id,
                phase=last.phase,
                progress=last.progress,
                message=last.message or ("Complete" if last.phase == "complete" else "Idle"),
                chapter_status=[],
            )
        return GenerationStatus(
            run_id="",
            job_id=job_id,
            phase="idle",
            progress=0,
            message="No generation runs found",
            chapter_status=[],
        )

    from api.models import Chapter
    chapters = (
        db.query(Chapter)
        .filter(Chapter.job_id == job_id)
        .order_by(Chapter.chapter_number)
        .all()
    )

    chapter_status = [
        ChapterGenStatus(
            number=ch.chapter_number,
            name=ch.name,
            status=ch.status,
            progress=100 if ch.status == "complete" else (active.progress if active.chapter_number == ch.chapter_number else 0),
        )
        for ch in chapters
    ]

    return GenerationStatus(
        run_id=active.id,
        job_id=job_id,
        phase=active.phase,
        progress=active.progress,
        message=active.message,
        chapter_status=chapter_status,
    )

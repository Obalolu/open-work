"""Job CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import JobCreate, JobDetail, JobResponse, JobUpdate
from api.services import job_service

router = APIRouter()


@router.get("", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    job_service.sync_jobs_from_yaml(db)
    jobs = job_service.list_jobs(db)
    result = []
    for job in jobs:
        chapters = db.query(job_service.Chapter).filter(
            job_service.Chapter.job_id == job.id
        ).all()
        result.append(JobResponse(
            id=job.id,
            topic=job.topic,
            paper_type=job.paper_type,
            citation_style=job.citation_style,
            target_audience=job.target_audience,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            chapter_count=len(chapters),
            total_words=sum(ch.word_count for ch in chapters),
        ))
    return result


@router.post("", response_model=JobResponse, status_code=201)
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    job = job_service.create_job(db, data)
    chapters = db.query(job_service.Chapter).filter(
        job_service.Chapter.job_id == job.id
    ).all()
    return JobResponse(
        id=job.id,
        topic=job.topic,
        paper_type=job.paper_type,
        citation_style=job.citation_style,
        target_audience=job.target_audience,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        chapter_count=len(chapters),
        total_words=0,
    )


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job_service.sync_chapters_from_output(db, job_id)
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    from api.schemas import ChapterSummary
    chapters = [
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
    return JobDetail(
        id=job.id,
        topic=job.topic,
        paper_type=job.paper_type,
        citation_style=job.citation_style,
        target_audience=job.target_audience,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        config_json=job.config_json,
        chapters=chapters,
    )


@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, data: JobUpdate, db: Session = Depends(get_db)):
    job = job_service.update_job(db, job_id, data)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    chapters = db.query(job_service.Chapter).filter(
        job_service.Chapter.job_id == job.id
    ).all()
    return JobResponse(
        id=job.id,
        topic=job.topic,
        paper_type=job.paper_type,
        citation_style=job.citation_style,
        target_audience=job.target_audience,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        chapter_count=len(chapters),
        total_words=sum(ch.word_count for ch in chapters),
    )


@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    if not job_service.delete_job(db, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}

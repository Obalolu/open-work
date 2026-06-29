"""Job business logic — syncs YAML files with SQLite."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from api.models import Chapter, Job
from api.schemas import JobCreate, JobUpdate
from src.config import get_jobs_dir, get_output_dir, load_yaml, save_yaml


def list_jobs(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.updated_at.desc()).all()


def get_job(db: Session, job_id: str) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def create_job(db: Session, data: JobCreate) -> Job:
    job = Job(
        id=_slugify_unique(db, data.topic),
        topic=data.topic,
        paper_type=data.paper_type,
        citation_style=data.citation_style,
        target_audience=data.target_audience,
        status="draft",
        config_json=json.dumps(data.model_dump()),
    )
    db.add(job)
    db.flush()

    for i, ch in enumerate(data.chapters, 1):
        chapter = Chapter(
            job_id=job.id,
            chapter_number=i,
            name=ch.get("name", f"Chapter {i}"),
            status="pending",
        )
        db.add(chapter)

    if not data.chapters:
        for i in range(1, 4):
            chapter = Chapter(
                job_id=job.id,
                chapter_number=i,
                name=f"Chapter {i}",
                status="pending",
            )
            db.add(chapter)

    db.commit()
    db.refresh(job)
    _sync_yaml(job)
    return job


def update_job(db: Session, job_id: str, data: JobUpdate) -> Job | None:
    job = get_job(db, job_id)
    if not job:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    _sync_yaml(job)
    return job


def delete_job(db: Session, job_id: str) -> bool:
    job = get_job(db, job_id)
    if not job:
        return False
    db.delete(job)
    db.commit()
    yaml_path = get_jobs_dir() / f"{job_id}.yaml"
    yaml_path.unlink(missing_ok=True)
    return True


def sync_jobs_from_yaml(db: Session):
    """Import jobs from YAML files that aren't in the DB yet."""
    jobs_dir = get_jobs_dir()
    if not jobs_dir.exists():
        return

    for yaml_path in jobs_dir.glob("*.yaml"):
        job_id = yaml_path.stem
        existing = get_job(db, job_id)
        if existing:
            continue

        try:
            data = load_yaml(yaml_path)
        except Exception:
            continue

        job = Job(
            id=job_id,
            topic=data.get("topic", ""),
            paper_type=data.get("paper_type", "literature_review"),
            citation_style=data.get("citation_style", "apa"),
            target_audience=data.get("target_audience", "graduate_students"),
            status="draft",
            config_json=json.dumps(data),
        )
        db.add(job)
        db.flush()

        chapters_ref = data.get("chapters", [])
        for i, ch_ref in enumerate(chapters_ref, 1):
            name = ch_ref.get("name", f"Chapter {i}") if isinstance(ch_ref, dict) else f"Chapter {i}"
            chapter = Chapter(
                job_id=job_id,
                chapter_number=i,
                name=name,
                status="pending",
            )
            db.add(chapter)

        if not chapters_ref:
            for i in range(1, 4):
                db.add(Chapter(job_id=job_id, chapter_number=i, name=f"Chapter {i}", status="pending"))

    db.commit()


def sync_chapters_from_output(db: Session, job_id: str):
    """Update chapter status/word_count from output files."""
    job = get_job(db, job_id)
    if not job:
        return

    output_dir = get_output_dir() / job_id
    if not output_dir.exists():
        return

    chapters = db.query(Chapter).filter(Chapter.job_id == job_id).all()
    for ch in chapters:
        compiled_path = output_dir / f"chapter_{ch.chapter_number}_compiled.md"
        raw_path = output_dir / f"chapter_{ch.chapter_number}.md"
        target = compiled_path if compiled_path.exists() else raw_path

        if target.exists():
            content = target.read_text(encoding="utf-8")
            ch.content = content
            ch.word_count = len(content.split())
            ch.status = "complete"

    db.commit()


def _sync_yaml(job: Job):
    """Write job config back to YAML."""
    jobs_dir = get_jobs_dir()
    jobs_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(job.config_json)
    config["name"] = job.id
    save_yaml(config, jobs_dir / f"{job.id}.yaml")


def _slugify(text: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    slug = slug.strip("_")[:50]
    return slug or "untitled_job"


def _slugify_unique(db: Session, text: str) -> str:
    base = _slugify(text)
    slug = base
    counter = 1
    while db.query(Job).filter(Job.id == slug).first():
        suffix = f"_{counter}"
        slug = base[:50 - len(suffix)] + suffix
        counter += 1
    return slug

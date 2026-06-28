"""Research sources routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Job
from api.schemas import SourceResponse

router = APIRouter()


@router.get("/jobs/{job_id}/research", response_model=list[SourceResponse])
def get_research_sources(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from src.config import get_project_root
    cache_path = get_project_root() / ".citation_cache.json"
    if not cache_path.exists():
        return []

    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    sources = []
    seen = set()
    job_config = json.loads(job.config_json)
    topic = job_config.get("topic", "")

    for key, entry in cache.items():
        if isinstance(entry, dict) and "papers" in entry:
            for paper in entry["papers"]:
                pid = paper.get("paper_id", "")
                if pid in seen:
                    continue
                seen.add(pid)
                sources.append(SourceResponse(
                    paper_id=pid,
                    title=paper.get("title", ""),
                    authors=paper.get("authors", []),
                    year=paper.get("year"),
                    venue=paper.get("venue", ""),
                    abstract_summary=paper.get("abstract_summary", "")[:200],
                    paper_url=paper.get("paper_url", ""),
                    doi=paper.get("doi", ""),
                    source_type=paper.get("source_type", ""),
                    citation_count=paper.get("citation_count", 0),
                    confidence=paper.get("confidence", 0.0),
                ))

    return sources[:100]

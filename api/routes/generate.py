"""Generation trigger + polling routes."""

from __future__ import annotations

import asyncio
import json
import queue
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ChapterGenStatus, GenerateRequest, GenerationStatus
from api.services import job_service, pipeline_service
from api.services.pipeline_service import (
    get_active_run_for_job,
    subscribe_to_run,
    unsubscribe_from_run,
)

router = APIRouter()


@router.post("/{job_id}/generate", response_model=dict)
def start_generation(
    job_id: str, data: GenerateRequest, db: Session = Depends(get_db)
):
    job = job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    active = get_active_run_for_job(db, job_id)
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Generation already in progress (run {active.id})",
        )

    chapters = data.chapters
    if not chapters:
        chapters = job_service.sync_chapters_from_output(db, job_id) or []
        from api.models import Chapter

        db_chapters = db.query(Chapter).filter(Chapter.job_id == job_id).all()
        chapters = [ch.chapter_number for ch in db_chapters]

    run_id = pipeline_service.start_generation(
        db=db,
        job_id=job_id,
        chapter_numbers=chapters,
        style_file=data.style,
        output_formats=data.formats,
        skip_humanize=data.skip_humanize,
        skip_review=data.skip_review,
    )

    job.status = "generating"
    db.commit()

    return {"run_id": run_id, "status": "started"}


@router.post("/{job_id}/generate/cancel")
def cancel_generation(job_id: str, db: Session = Depends(get_db)):
    active = get_active_run_for_job(db, job_id)
    if not active:
        raise HTTPException(status_code=404, detail="No active generation for this job")
    cancelled = pipeline_service.cancel_generation(db, job_id)
    if not cancelled:
        raise HTTPException(status_code=500, detail="Failed to cancel generation")
    return {"ok": True, "run_id": active.id}


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

    import json as _json

    try:
        run_statuses: dict = _json.loads(active.chapter_status_json or "{}")
    except _json.JSONDecodeError:
        run_statuses = {}

    chapter_status = []
    for ch in chapters:
        ch_status = run_statuses.get(str(ch.chapter_number), {})
        if ch.status == "complete":
            progress = 100
            status_text = "complete"
        elif active.chapter_number == ch.chapter_number:
            progress = ch_status.get("progress", active.progress)
            status_text = ch_status.get("status", active.phase)
        else:
            progress = 0
            status_text = ch.status or "pending"
        chapter_status.append(
            ChapterGenStatus(
                number=ch.chapter_number,
                name=ch.name,
                status=status_text,
                progress=progress,
            )
        )

    return GenerationStatus(
        run_id=active.id,
        job_id=job_id,
        phase=active.phase,
        progress=active.progress,
        message=active.message,
        chapter_status=chapter_status,
    )


@router.get("/{job_id}/generate/stream")
async def stream_generation(
    job_id: str, request: Request, db: Session = Depends(get_db)
):
    """Server-Sent Events stream of phase, chapter, and lifecycle events for a generation run.

    Resolves the most recent run (active if any, else last completed). If the
    run is already finished, the server replays a single `complete` event
    before closing. Otherwise it subscribes to live events.
    """
    active = get_active_run_for_job(db, job_id)
    if not active:
        all_runs = (
            db.query(pipeline_service.GenerationRun)
            .filter(pipeline_service.GenerationRun.job_id == job_id)
            .order_by(pipeline_service.GenerationRun.started_at.desc())
            .limit(1)
            .all()
        )
        if not all_runs:
            raise HTTPException(status_code=404, detail="No generation runs for this job")
        last = all_runs[0]
        if last.phase not in ("complete", "error", "cancelled"):
            raise HTTPException(status_code=404, detail="No active generation for this job")

        async def replay_finished() -> AsyncIterator[bytes]:
            payload = json.dumps(
                {
                    "type": "complete" if last.phase == "complete" else "error",
                    "phase": last.phase,
                    "message": last.message,
                    "run_id": last.id,
                }
            )
            yield f"data: {payload}\n\n".encode()

        return StreamingResponse(
            replay_finished(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    run_id = active.id
    q = subscribe_to_run(run_id)

    async def event_stream() -> AsyncIterator[bytes]:
        try:
            # initial snapshot
            snapshot = {
                "type": "snapshot",
                "run_id": run_id,
                "phase": active.phase,
                "progress": active.progress,
                "message": active.message,
            }
            yield f"data: {json.dumps(snapshot)}\n\n".encode()
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.to_thread(q.get, timeout=15.0)
                except queue.Empty:
                    # keep-alive ping
                    yield b": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n".encode()
                if event.get("type") in {"complete", "error", "cancelled"}:
                    break
        finally:
            unsubscribe_from_run(run_id, q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

"""Pipeline orchestration — runs generation in background thread."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from api.database import SessionLocal
from api.models import Chapter, ChapterContentRevision, GenerationRun, HumanizerAttempt, Job
from src.config import get_output_dir, load_yaml
from src.export.exporter import export_chapter
from src.humanizer.pipeline import stream_humanize_text
from src.research.orchestrator import CitationResearcher
from src.research.summarizer import summarize_papers
from src.reviewers.ai_detector import detect_ai_text
from src.reviewers.fact_checker import fact_check
from src.reviewers.style_checker import review_style
from src.router.prompt_loader import load_base_prompt, load_chapter_template, load_style_template
from src.writers.chapter_writer import stream_write_chapter
from src.writers.citation_compiler import (
    compile_citations,
    format_reference_list,
    replace_inline_citations,
)

_active_runs: dict[str, threading.Thread] = {}
_active_run_cancels: dict[str, threading.Event] = {}
_event_queues: dict[str, list[queue.Queue]] = {}
_run_lock = threading.Lock()


def _run_async(coro):
    """Run a coroutine in a new event loop and close it."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _drain_stream(
    agen: Any, *, on_chunk: Any | None = None
) -> str:
    """Drain an async generator of text chunks, optionally invoking
    on_chunk(str) for each piece. Returns the concatenated string. Safe to call
    from the background pipeline thread.
    """
    pieces: list[str] = []

    async def _drain() -> str:
        async for chunk in agen:
            pieces.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)
        return "".join(pieces)

    return _run_async(_drain())


def _phase_progress(
    chapter_index: int, total_chapters: int, phase_index: int, total_phases: int
) -> tuple[int, float, float]:
    """Compute overall progress (0-100) based on chapter and phase position."""
    chapter_share = 100 / max(total_chapters, 1)
    phase_share = chapter_share / max(total_phases, 1)
    return (
        int(chapter_index * chapter_share + phase_index * phase_share),
        chapter_share,
        phase_share,
    )


def start_generation(
    db: Session,
    job_id: str,
    chapter_numbers: list[int],
    style_file: str,
    output_formats: list[str],
    skip_humanize: bool,
    skip_review: bool,
) -> str:
    run = GenerationRun(
        id=str(uuid.uuid4()),
        job_id=job_id,
        phase="queued",
        progress=0,
        message="Queued...",
    )
    db.add(run)
    db.commit()

    cancel_event = threading.Event()
    with _run_lock:
        _active_runs[run.id] = None  # placeholder, set below
        _active_run_cancels[run.id] = cancel_event

    thread = threading.Thread(
        target=_run_pipeline,
        args=(
            run.id,
            job_id,
            chapter_numbers,
            style_file,
            output_formats,
            skip_humanize,
            skip_review,
            cancel_event,
        ),
        daemon=True,
    )
    with _run_lock:
        _active_runs[run.id] = thread
    thread.start()

    return run.id


def cancel_generation(db: Session, job_id: str) -> bool:
    """Mark the active run for a job as cancelled. Returns True if a run was cancelled."""
    run = get_active_run_for_job(db, job_id)
    if not run:
        return False
    with _run_lock:
        evt = _active_run_cancels.get(run.id)
    if evt:
        evt.set()
    run.cancelled = 1
    run.message = "Cancellation requested…"
    run.phase = "cancelling"
    db.commit()
    return True


def get_run_status(db: Session, run_id: str) -> GenerationRun | None:
    return db.query(GenerationRun).filter(GenerationRun.id == run_id).first()


def get_active_run_for_job(db: Session, job_id: str) -> GenerationRun | None:
    return (
        db.query(GenerationRun)
        .filter(GenerationRun.job_id == job_id)
        .filter(GenerationRun.phase.notin_(["complete", "error", "idle"]))
        .order_by(GenerationRun.started_at.desc())
        .first()
    )


def subscribe_to_run(run_id: str) -> queue.Queue:
    """Subscribe to live events for a run. Returns a queue that receives dict events.

    Caller must call `unsubscribe_from_run` to clean up.
    """
    q: queue.Queue = queue.Queue(maxsize=512)
    with _run_lock:
        _event_queues.setdefault(run_id, []).append(q)
    return q


def unsubscribe_from_run(run_id: str, q: queue.Queue) -> None:
    with _run_lock:
        if run_id in _event_queues:
            try:
                _event_queues[run_id].remove(q)
                if not _event_queues[run_id]:
                    del _event_queues[run_id]
            except ValueError:
                pass


def _publish_event(run_id: str, event: dict[str, Any]) -> None:
    with _run_lock:
        qs = list(_event_queues.get(run_id, []))
    for q in qs:
        try:
            q.put_nowait(event)
        except queue.Full:
            # Drop event for slow consumers
            pass


def _publish_chunk(run_id: str, chapter: int, phase: str, text: str) -> None:
    """Publish a text chunk to all SSE subscribers for the given run."""
    _publish_event(
        run_id,
        {"type": "chunk", "chapter": chapter, "phase": phase, "text": text},
    )


def _run_pipeline(
    run_id: str,
    job_id: str,
    chapter_numbers: list[int],
    style_file: str,
    output_formats: list[str],
    skip_humanize: bool,
    skip_review: bool,
    cancel_event: threading.Event,
):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            _update_run(db, run_id, phase="error", message="Job not found", error="Job not found")
            _publish_event(run_id, {"type": "error", "message": "Job not found"})
            return

        _update_run(db, run_id, phase="starting", message="Loading configs...")

        try:
            style_config = load_style_template(style_file)
        except FileNotFoundError:
            style_config = {
                "tone": "professional",
                "formality": 0.7,
                "preferred_voice": "active",
                "forbidden_phrases": [],
            }

        try:
            base_prompt = load_base_prompt("writer")
        except FileNotFoundError:
            base_prompt = "You are an expert academic writer."

        job_config = json.loads(job.config_json)
        chapter_configs = _get_chapter_configs(job_config)

        all_chapter_texts: list[str] = []
        total_chapters = len(chapter_numbers)
        citation_style = job_config.get("citation_style", "apa")

        for idx, ch_num in enumerate(sorted(chapter_numbers)):
            if cancel_event.is_set():
                _update_run(db, run_id, phase="cancelled", progress=0, message="Generation cancelled")
                _publish_event(run_id, {"type": "cancelled"})
                return

            ch_index = ch_num - 1
            if ch_index >= len(chapter_configs):
                continue

            ch_config = chapter_configs[ch_index]
            ch_name = ch_config.get("name", f"Chapter {ch_num}")
            total_phases = 7 if not skip_humanize else 5

            def _progress(phase_index: int) -> int:
                return _phase_progress(idx, total_chapters, phase_index, total_phases)[0]

            # Phase 1: Research
            _update_run(
                db,
                run_id,
                phase="research",
                progress=_progress(0),
                message=f"Researching Chapter {ch_num}: {ch_name}...",
                chapter_number=ch_num,
            )
            _set_chapter_status(db, run_id, ch_num, "research", 0, f"Starting research for {ch_name}")
            db.commit()
            _publish_event(
                run_id,
                {
                    "type": "phase",
                    "phase": "research",
                    "chapter": ch_num,
                    "progress": _progress(0),
                    "message": f"Researching Chapter {ch_num}: {ch_name}...",
                },
            )

            topic = job_config.get("topic", "research topic")
            research_queries = _extract_research_queries(ch_config, topic)
            all_papers: list[dict] = []
            try:
                with CitationResearcher() as researcher:
                    for q_idx, query in enumerate(research_queries[:3]):
                        if cancel_event.is_set():
                            _update_run(db, run_id, phase="cancelled", progress=0, message="Cancelled")
                            _publish_event(run_id, {"type": "cancelled"})
                            return
                        q_progress = int((q_idx / max(len(research_queries[:3]), 1)) * 100)
                        _set_chapter_status(
                            db,
                            run_id,
                            ch_num,
                            "research",
                            q_progress,
                            f"Query {q_idx + 1}/{len(research_queries[:3])}",
                        )
                        db.commit()
                        try:
                            citations = researcher.research(query)
                            for c in citations:
                                paper = {
                                    "title": c.title,
                                    "authors": c.authors,
                                    "year": c.year,
                                    "doi": c.doi,
                                    "url": c.paper_url,
                                    "journal": c.venue,
                                    "abstract": c.abstract_summary,
                                    "source_type": c.source_type,
                                    "citation_count": c.citation_count,
                                    "confidence": c.confidence,
                                    "api_source": c.api_source,
                                }
                                key = paper.get("doi") or paper.get("url") or paper.get("title", "")
                                if key and key not in {
                                    p.get("doi") or p.get("url") or p.get("title", "")
                                    for p in all_papers
                                }:
                                    all_papers.append(paper)
                            logger.info(
                                f"Research query '{query[:60]}...' returned {len(citations)} papers, total unique: {len(all_papers)}"
                            )
                        except Exception as query_err:
                            logger.warning(f"Research query failed: {query_err}")
            except Exception as research_err:
                logger.error(f"Research phase failed: {research_err}")
                raise

            if not all_papers:
                logger.warning("No papers found from section queries; trying topic fallback.")
                try:
                    with CitationResearcher() as fallback_researcher:
                        fallback_citations = fallback_researcher.research(topic)
                        for c in fallback_citations:
                            paper = {
                                "title": c.title,
                                "authors": c.authors,
                                "year": c.year,
                                "doi": c.doi,
                                "url": c.paper_url,
                                "journal": c.venue,
                                "abstract": c.abstract_summary,
                                "source_type": c.source_type,
                                "citation_count": c.citation_count,
                                "confidence": c.confidence,
                                "api_source": c.api_source,
                            }
                            key = paper.get("doi") or paper.get("url") or paper.get("title", "")
                            if key and key not in {
                                p.get("doi") or p.get("url") or p.get("title", "")
                                for p in all_papers
                            }:
                                all_papers.append(paper)
                except Exception as fallback_err:
                    logger.warning(f"Topic fallback research failed: {fallback_err}")

            if not all_papers:
                raise RuntimeError(
                    "Research returned no papers. "
                    "Check API keys (OpenAlex, Semantic Scholar) and internet connectivity."
                )

            section_instructions = {
                str(s.get("id", "")): s.get("instructions", "")
                for s in ch_config.get("sections", [])
                if s.get("instructions")
            }
            _set_chapter_status(
                db, run_id, ch_num, "research", 100, f"Found {len(all_papers)} papers"
            )
            db.commit()
            research = _run_async(summarize_papers(all_papers, section_instructions or None))

            # Phase 2: Writing (streamed)
            _update_run(
                db,
                run_id,
                phase="writing",
                progress=_progress(1),
                message=f"Writing Chapter {ch_num}...",
                chapter_number=ch_num,
            )
            _set_chapter_status(db, run_id, ch_num, "writing", 0, "Drafting chapter")
            _publish_event(
                run_id,
                {
                    "type": "phase",
                    "phase": "writing",
                    "chapter": ch_num,
                    "progress": _progress(1),
                    "message": f"Writing Chapter {ch_num}...",
                },
            )

            def _on_write_chunk(chunk: str) -> None:
                _publish_chunk(run_id, ch_num, "writing", chunk)

            chapter_text = _drain_stream(
                stream_write_chapter(
                    base_prompt=base_prompt,
                    chapter_config=ch_config,
                    style_config=style_config,
                    research=research,
                    job_config=job_config,
                    previous_chapters=all_chapter_texts if all_chapter_texts else None,
                ),
                on_chunk=_on_write_chunk,
            )

            # Phase 3: Replace {cite_XXX} with inline (Author, Year) for review/humanize
            _update_run(
                db,
                run_id,
                phase="writing",
                progress=_progress(2),
                message=f"Formatting citations for Chapter {ch_num}...",
                chapter_number=ch_num,
            )
            _set_chapter_status(db, run_id, ch_num, "writing", 80, "Compiling inline citations")
            chapter_text = replace_inline_citations(chapter_text, research.citations, citation_style)

            # Phase 4: Pre-humanization review
            if not skip_review:
                _update_run(
                    db,
                    run_id,
                    phase="review",
                    progress=_progress(2),
                    message=f"Pre-reviewing Chapter {ch_num}...",
                    chapter_number=ch_num,
                )
                _set_chapter_status(db, run_id, ch_num, "review", 0, "Pre-reviewing style and facts")
                style_review = _run_async(review_style(chapter_text, ch_config, style_config))
                fact_result = _run_async(fact_check(chapter_text, research.citations))
                pre_score = (style_review.score + fact_result.score) // 2
                _set_chapter_status(db, run_id, ch_num, "review", 50, f"Pre-review score: {pre_score}")
            else:
                pre_score = 75

            # Phase 5: Humanize (streamed)
            if not skip_humanize:
                _update_run(
                    db,
                    run_id,
                    phase="humanize",
                    progress=_progress(3),
                    message=f"Humanizing Chapter {ch_num}...",
                    chapter_number=ch_num,
                )
                _set_chapter_status(db, run_id, ch_num, "humanize", 0, "Humanizing draft")
                _publish_event(
                    run_id,
                    {
                        "type": "phase",
                        "phase": "humanize",
                        "chapter": ch_num,
                        "progress": _progress(3),
                        "message": f"Humanizing Chapter {ch_num}...",
                    },
                )

                def _record_attempt(
                    original, rewritten, intensity, before, after, *, _ch: int = ch_num
                ):
                    ch_db = (
                        db.query(Chapter)
                        .filter(Chapter.job_id == job_id, Chapter.chapter_number == _ch)
                        .first()
                    )
                    if not ch_db:
                        return
                    attempt = HumanizerAttempt(
                        chapter_id=ch_db.id,
                        run_id=run_id,
                        original_text=original,
                        rewritten_text=rewritten,
                        intensity=intensity,
                        ai_score_before=before,
                        ai_score_after=after,
                    )
                    db.add(attempt)
                    db.commit()

                def _on_humanize_chunk(chunk: str) -> None:
                    _publish_chunk(run_id, ch_num, "humanize", chunk)

                # First humanize pass — measure AI score before, stream the
                # rewrite, then measure the score after so we can record the
                # actual delta in humanizer_attempts.
                pre_humanize_score = detect_ai_text(chapter_text).score
                rewritten = _drain_stream(
                    stream_humanize_text(
                        chapter_text,
                        intensity="medium",
                    ),
                    on_chunk=_on_humanize_chunk,
                )
                post_humanize_score = detect_ai_text(rewritten).score
                _record_attempt(
                    chapter_text,
                    rewritten,
                    "medium",
                    pre_humanize_score,
                    post_humanize_score,
                )
                chapter_text = rewritten

                if not skip_review:
                    _update_run(
                        db,
                        run_id,
                        phase="review",
                        progress=_progress(4),
                        message=f"Post-reviewing Chapter {ch_num}...",
                        chapter_number=ch_num,
                    )
                    _set_chapter_status(db, run_id, ch_num, "review", 60, "Post-reviewing style and facts")
                    style_review = _run_async(review_style(chapter_text, ch_config, style_config))
                    fact_result = _run_async(fact_check(chapter_text, research.citations))
                    post_score = (style_review.score + fact_result.score) // 2
                    _set_chapter_status(
                        db, run_id, ch_num, "review", 90, f"Post-review score: {post_score}"
                    )
                else:
                    post_score = pre_score

                detection = detect_ai_text(chapter_text)
                _set_chapter_status(
                    db, run_id, ch_num, "humanize", 80, f"AI detection score: {detection.score}"
                )
                if not detection.pass_quality and detection.score > 60:
                    _update_run(
                        db,
                        run_id,
                        phase="humanize",
                        progress=_progress(5),
                        message=f"Re-humanizing Chapter {ch_num} (AI score high)...",
                        chapter_number=ch_num,
                    )
                    _set_chapter_status(
                        db, run_id, ch_num, "humanize", 90, "Re-humanizing high-AI sections"
                    )
                    pre_score_2 = detection.score
                    rewritten = _drain_stream(
                        stream_humanize_text(
                            chapter_text,
                            intensity="aggressive",
                        ),
                        on_chunk=_on_humanize_chunk,
                    )
                    post_score_2 = detect_ai_text(rewritten).score
                    _record_attempt(
                        chapter_text,
                        rewritten,
                        "aggressive",
                        pre_score_2,
                        post_score_2,
                    )
                    chapter_text = rewritten
                    detection = detect_ai_text(chapter_text)
            else:
                post_score = pre_score
                detection = detect_ai_text(chapter_text)

            avg_score = post_score if not skip_review else pre_score

            # Phase 7: Append reference list and export
            _update_run(
                db,
                run_id,
                phase="export",
                progress=_progress(6),
                message=f"Exporting Chapter {ch_num}...",
                chapter_number=ch_num,
            )
            _set_chapter_status(db, run_id, ch_num, "export", 0, "Appending references")
            refs = format_reference_list(research.citations, citation_style)
            if refs:
                chapter_text = chapter_text.rstrip() + "\n\n---\n\n" + refs

            export_chapter(chapter_text, job_id, ch_num, output_formats or ["md"])
            _set_chapter_status(db, run_id, ch_num, "export", 100, "Exported")

            ch_db = (
                db.query(Chapter)
                .filter(Chapter.job_id == job_id, Chapter.chapter_number == ch_num)
                .first()
            )
            if ch_db:
                word_count = len(chapter_text.split())
                ch_db.content = chapter_text
                ch_db.word_count = word_count
                ch_db.ai_score = detection.score
                ch_db.style_score = float(avg_score)
                ch_db.status = "complete"
                revision = ChapterContentRevision(
                    chapter_id=ch_db.id,
                    content=chapter_text,
                    source="pipeline",
                    word_count=word_count,
                    ai_score=detection.score,
                )
                db.add(revision)

            _set_chapter_status(db, run_id, ch_num, "complete", 100, f"Done (score {avg_score})")
            db.commit()
            _publish_event(
                run_id,
                {
                    "type": "chapter",
                    "chapter": ch_num,
                    "status": "complete",
                    "word_count": ch_db.word_count if ch_db else 0,
                    "ai_score": float(detection.score),
                },
            )
            all_chapter_texts.append(chapter_text)

        _update_run(
            db, run_id, phase="complete", progress=100, message="Generation complete!"
        )
        _publish_event(run_id, {"type": "complete", "job_id": job_id, "run_id": run_id})

        job.status = "complete"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        full_traceback = traceback.format_exc()
        logger.error(f"Pipeline run {run_id} failed: {error_msg}\n{full_traceback}")
        _update_run(
            db,
            run_id,
            phase="error",
            message=f"Generation failed: {error_msg}",
            error=f"{error_msg}\n{full_traceback}",
        )
        _publish_event(
            run_id,
            {"type": "error", "message": error_msg, "traceback": full_traceback},
        )
    finally:
        with _run_lock:
            _active_runs.pop(run_id, None)
            _active_run_cancels.pop(run_id, None)
        db.close()


def _get_chapter_status(run: GenerationRun) -> dict[str, Any]:
    try:
        return json.loads(run.chapter_status_json or "{}")
    except json.JSONDecodeError:
        return {}


def _set_chapter_status(
    db: Session,
    run_id: str,
    chapter_number: int,
    status: str,
    progress: int,
    message: str,
):
    run = db.query(GenerationRun).filter(GenerationRun.id == run_id).first()
    if not run:
        return
    statuses = _get_chapter_status(run)
    statuses[str(chapter_number)] = {
        "status": status,
        "progress": progress,
        "message": message,
    }
    run.chapter_status_json = json.dumps(statuses)
    _publish_event(
        run_id,
        {
            "type": "chapter",
            "chapter": chapter_number,
            "status": status,
            "progress": progress,
            "message": message,
        },
    )


def _update_run(db: Session, run_id: str, **kwargs):
    run = db.query(GenerationRun).filter(GenerationRun.id == run_id).first()
    if not run:
        return
    for k, v in kwargs.items():
        if k == "error":
            run.error = v
            run.phase = "error"
        elif k == "chapter_number":
            run.chapter_number = v
            run.message = kwargs.get("message", run.message)
        else:
            setattr(run, k, v)
    if kwargs.get("phase") in ("complete", "cancelled"):
        run.completed_at = datetime.now(timezone.utc)
        if kwargs.get("phase") == "complete":
            run.progress = 100
    db.commit()


def _get_chapter_configs(job_config: dict[str, Any]) -> list[dict[str, Any]]:
    chapters_ref = job_config.get("chapters", [])
    configs: list[dict[str, Any]] = []

    for ch_ref in chapters_ref:
        if isinstance(ch_ref, dict):
            template_file = ch_ref.get("template", "")
            if template_file:
                try:
                    configs.append(load_chapter_template(template_file))
                except FileNotFoundError:
                    configs.append(
                        {
                            "name": ch_ref.get("name", f"Chapter {len(configs)+1}"),
                            "sections": ch_ref.get("sections", []),
                            "forbidden": ch_ref.get("forbidden", []),
                            "required": ch_ref.get("required", []),
                        }
                    )
            else:
                configs.append(ch_ref)
        elif isinstance(ch_ref, str):
            try:
                configs.append(load_chapter_template(ch_ref))
            except FileNotFoundError:
                configs.append({"name": f"Chapter {len(configs)+1}", "sections": []})

    if not configs:
        for i in range(1, 4):
            configs.append(
                {
                    "name": f"Chapter {i}",
                    "sections": [
                        {
                            "id": f"{i}.1",
                            "title": "Section 1",
                            "paragraphs": 3,
                            "word_count": 500,
                        }
                    ],
                    "forbidden": [],
                    "required": [],
                }
            )

    return configs


def _extract_research_queries(
    ch_config: dict[str, Any], topic: str = ""
) -> list[str]:
    queries: list[str] = []
    topic = (topic or "").strip()
    for section in ch_config.get("sections", []):
        title = (section.get("title", "") or "").strip()
        instructions = (section.get("instructions", "") or "").strip()
        if title.lower() in ("section 1", "section", "") and not instructions:
            continue
        if not title and not instructions:
            continue
        parts = [p for p in [topic, title] if p]
        if instructions:
            first_sentence = instructions.split(".")[0].strip()
            if len(first_sentence) > 200:
                first_sentence = first_sentence[:200].rsplit(" ", 1)[0] + "..."
            if first_sentence:
                parts.append(first_sentence)
        query = " ".join(parts).strip()
        if query and query not in queries:
            queries.append(query)
    if not queries:
        fallback = topic or ch_config.get("name", "general research") or "general research"
        queries.append(fallback)
    return queries

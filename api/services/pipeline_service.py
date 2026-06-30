"""Pipeline orchestration — runs generation in background thread."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from api.database import SessionLocal
from api.models import Chapter, GenerationRun, Job
from src.config import get_output_dir, load_yaml
from src.export.exporter import export_chapter
from src.humanizer.pipeline import run_humanize_pipeline
from src.research.orchestrator import CitationResearcher
from src.research.summarizer import summarize_papers
from src.reviewers.ai_detector import detect_ai_text
from src.reviewers.fact_checker import fact_check
from src.reviewers.style_checker import review_style
from src.router.prompt_loader import load_base_prompt, load_chapter_template, load_style_template
from src.writers.chapter_writer import write_chapter
from src.writers.citation_compiler import compile_citations

_active_runs: dict[str, threading.Thread] = {}
_run_lock = threading.Lock()


def start_generation(
    db: Session,
    job_id: str,
    chapter_numbers: list[int],
    style_file: str,
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

    thread = threading.Thread(
        target=_run_pipeline,
        args=(run.id, job_id, chapter_numbers, style_file, skip_humanize, skip_review),
        daemon=True,
    )
    with _run_lock:
        _active_runs[run.id] = thread
    thread.start()

    return run.id


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


def _run_pipeline(
    run_id: str,
    job_id: str,
    chapter_numbers: list[int],
    style_file: str,
    skip_humanize: bool,
    skip_review: bool,
):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            _update_run(db, run_id, phase="error", message="Job not found", error="Job not found")
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

        for idx, ch_num in enumerate(sorted(chapter_numbers)):
            ch_index = ch_num - 1
            if ch_index >= len(chapter_configs):
                continue

            ch_config = chapter_configs[ch_index]
            ch_name = ch_config.get("name", f"Chapter {ch_num}")

            _update_run(
                db, run_id,
                phase="research",
                progress=int((idx / total_chapters) * 100),
                message=f"Researching Chapter {ch_num}: {ch_name}...",
                chapter_number=ch_num,
            )

            topic = job_config.get("topic", "research topic")
            research_queries = _extract_research_queries(ch_config, topic)
            _update_run(db, run_id, message=f"Researching Chapter {ch_num}: {ch_name} (queries: {len(research_queries)})...")

            all_papers: list[dict] = []
            try:
                with CitationResearcher() as researcher:
                    for query in research_queries[:3]:
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
                                if key and key not in {p.get("doi") or p.get("url") or p.get("title", "") for p in all_papers}:
                                    all_papers.append(paper)
                            logger.info(f"Research query '{query[:40]}...' returned {len(citations)} papers")
                        except Exception as query_err:
                            logger.warning(f"Research query failed: {query_err}")
            except Exception as research_err:
                logger.error(f"Research phase failed: {research_err}")
                raise

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
            loop = asyncio.new_event_loop()
            try:
                research = loop.run_until_complete(
                    summarize_papers(all_papers, section_instructions or None)
                )
            finally:
                loop.close()

            _update_run(db, run_id, phase="writing", message=f"Writing Chapter {ch_num}...")

            loop = asyncio.new_event_loop()
            chapter_text = loop.run_until_complete(
                write_chapter(
                    base_prompt=base_prompt,
                    chapter_config=ch_config,
                    style_config=style_config,
                    research=research,
                    job_config=job_config,
                    previous_chapters=all_chapter_texts if all_chapter_texts else None,
                )
            )
            loop.close()

            if not skip_review:
                _update_run(db, run_id, phase="review", message=f"Reviewing Chapter {ch_num}...")
                loop = asyncio.new_event_loop()
                style_review = loop.run_until_complete(
                    review_style(chapter_text, ch_config, style_config)
                )
                fact_result = loop.run_until_complete(
                    fact_check(chapter_text, research.citations)
                )
                loop.close()
                avg_score = (style_review.score + fact_result.score) // 2
            else:
                avg_score = 75

            if not skip_humanize:
                _update_run(db, run_id, phase="humanize", message=f"Humanizing Chapter {ch_num}...")
                loop = asyncio.new_event_loop()
                humanize_result = loop.run_until_complete(
                    run_humanize_pipeline(chapter_text, intensity="medium")
                )
                loop.close()
                chapter_text = humanize_result.final_text

            detection = detect_ai_text(chapter_text)
            if not detection.pass_quality and detection.score > 60 and not skip_humanize:
                _update_run(db, run_id, message=f"Re-humanizing Chapter {ch_num} (AI score high)...")
                loop = asyncio.new_event_loop()
                humanize_result = loop.run_until_complete(
                    run_humanize_pipeline(chapter_text, intensity="aggressive")
                )
                loop.close()
                chapter_text = humanize_result.final_text

            chapter_text = compile_citations(
                chapter_text, research.citations, job_config.get("citation_style", "apa")
            )

            _update_run(db, run_id, phase="export", message=f"Exporting Chapter {ch_num}...")
            export_chapter(chapter_text, job_id, ch_num, ["md", "docx", "pdf"])

            ch_db = (
                db.query(Chapter)
                .filter(Chapter.job_id == job_id, Chapter.chapter_number == ch_num)
                .first()
            )
            if ch_db:
                ch_db.content = chapter_text
                ch_db.word_count = len(chapter_text.split())
                ch_db.ai_score = detection.score
                ch_db.style_score = float(avg_score)
                ch_db.status = "complete"

            all_chapter_texts.append(chapter_text)

        _update_run(db, run_id, phase="complete", progress=100, message="Generation complete!")

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
    finally:
        with _run_lock:
            _active_runs.pop(run_id, None)
        db.close()


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
    if kwargs.get("phase") == "complete":
        run.completed_at = datetime.now(timezone.utc)
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
                    configs.append({
                        "name": ch_ref.get("name", f"Chapter {len(configs)+1}"),
                        "sections": ch_ref.get("sections", []),
                        "forbidden": ch_ref.get("forbidden", []),
                        "required": ch_ref.get("required", []),
                    })
            else:
                configs.append(ch_ref)
        elif isinstance(ch_ref, str):
            try:
                configs.append(load_chapter_template(ch_ref))
            except FileNotFoundError:
                configs.append({"name": f"Chapter {len(configs)+1}", "sections": []})

    if not configs:
        for i in range(1, 4):
            configs.append({
                "name": f"Chapter {i}",
                "sections": [{"id": f"{i}.1", "title": "Section 1", "paragraphs": 3, "word_count": 500}],
                "forbidden": [],
                "required": [],
            })

    return configs


def _extract_research_queries(ch_config: dict[str, Any], topic: str = "") -> list[str]:
    queries: list[str] = []
    for section in ch_config.get("sections", []):
        title = (section.get("title", "") or "").strip()
        instructions = (section.get("instructions", "") or "").strip()
        # Skip placeholder sections without meaningful instructions
        if title.lower() in ("section 1", "section", "") and not instructions:
            continue
        if title or instructions:
            queries.append(f"{topic} {title} {instructions}".strip())
    if not queries:
        fallback = topic or ch_config.get("name", "general research") or "general research"
        queries.append(fallback)
    return queries

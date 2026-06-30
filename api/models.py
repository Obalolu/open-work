"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    topic = Column(String, nullable=False)
    paper_type = Column(String, default="literature_review")
    citation_style = Column(String, default="apa")
    target_audience = Column(String, default="graduate_students")
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    config_json = Column(Text, default="{}")

    chapters = relationship("Chapter", back_populates="job", cascade="all, delete-orphan")
    runs = relationship("GenerationRun", back_populates="job", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    name = Column(String, default="")
    status = Column(String, default="pending")
    word_count = Column(Integer, default=0)
    ai_score = Column(Float, nullable=True)
    style_score = Column(Float, nullable=True)
    content = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    job = relationship("Job", back_populates="chapters")
    revisions = relationship(
        "ChapterContentRevision",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ChapterContentRevision.created_at",
    )
    humanizer_attempts = relationship(
        "HumanizerAttempt",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="HumanizerAttempt.created_at",
    )


class GenerationRun(Base):
    __tablename__ = "generation_runs"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    chapter_number = Column(Integer, nullable=True)
    phase = Column(String, default="idle")
    progress = Column(Integer, default=0)
    message = Column(String, default="")
    error = Column(Text, nullable=True)
    chapter_status_json = Column(Text, default="{}")
    started_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)
    cancelled = Column(Integer, default=0)

    job = relationship("Job", back_populates="runs")


class ResearchCache(Base):
    __tablename__ = "research_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String, nullable=False)
    results_json = Column(Text, default="[]")
    paper_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


class ChapterContentRevision(Base):
    """One row per persisted chapter content. Source tracks how it was produced."""

    __tablename__ = "chapter_content_revisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    content = Column(Text, default="")
    source = Column(String, default="pipeline")  # pipeline | tiptap | import
    summary = Column(String, default="")  # optional human note
    word_count = Column(Integer, default=0)
    ai_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    chapter = relationship("Chapter", back_populates="revisions")


class HumanizerAttempt(Base):
    """One row per humanizer pass. Feeds future fine-tuning datasets."""

    __tablename__ = "humanizer_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    run_id = Column(String, ForeignKey("generation_runs.id"), nullable=True)
    original_text = Column(Text, default="")
    rewritten_text = Column(Text, default="")
    intensity = Column(String, default="medium")
    ai_score_before = Column(Float, nullable=True)
    ai_score_after = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    chapter = relationship("Chapter", back_populates="humanizer_attempts")

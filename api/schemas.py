"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Job ──────────────────────────────────────────────
class ChapterCreate(BaseModel):
    name: str
    template: Optional[str] = None


class JobCreate(BaseModel):
    topic: str
    paper_type: str = "literature_review"
    citation_style: str = "apa"
    target_audience: str = "graduate_students"
    research_queries: list[str] = Field(default_factory=list)
    chapters: list[ChapterCreate] = Field(default_factory=list)


class JobUpdate(BaseModel):
    topic: Optional[str] = None
    paper_type: Optional[str] = None
    citation_style: Optional[str] = None
    target_audience: Optional[str] = None
    research_queries: Optional[list[str]] = None
    chapters: Optional[list[ChapterCreate]] = None


class JobResponse(BaseModel):
    id: str
    topic: str
    paper_type: str
    citation_style: str
    target_audience: str
    status: str
    created_at: datetime
    updated_at: datetime
    chapter_count: int = 0
    total_words: int = 0

    model_config = {"from_attributes": True}


class JobDetail(BaseModel):
    id: str
    topic: str
    paper_type: str
    citation_style: str
    target_audience: str
    status: str
    created_at: datetime
    updated_at: datetime
    config_json: str
    chapters: list["ChapterSummary"] = []
    chapter_count: int = 0
    total_words: int = 0

    model_config = {"from_attributes": True}


# ── Chapter ──────────────────────────────────────────
class ChapterSummary(BaseModel):
    id: int
    chapter_number: int
    name: str
    status: str
    word_count: int
    ai_score: Optional[float] = None
    style_score: Optional[float] = None

    model_config = {"from_attributes": True}


class ChapterDetail(BaseModel):
    id: int
    chapter_number: int
    name: str
    status: str
    word_count: int
    ai_score: Optional[float] = None
    style_score: Optional[float] = None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterUpdate(BaseModel):
    content: str = Field(..., description="New chapter content (markdown or HTML)")
    source: str = Field(default="tiptap", description="Source: tiptap | import")
    summary: Optional[str] = None


class ChapterRevisionSummary(BaseModel):
    id: int
    source: str
    summary: str = ""
    word_count: int
    ai_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterRevisionDetail(ChapterRevisionSummary):
    content: str


class HumanizerAttemptSummary(BaseModel):
    id: int
    intensity: str
    ai_score_before: Optional[float] = None
    ai_score_after: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generation ───────────────────────────────────────
class GenerateRequest(BaseModel):
    chapters: list[int] = Field(default_factory=list, description="Chapter numbers to generate")
    style: str = "academic_balanced.yaml"
    formats: list[str] = Field(default_factory=lambda: ["md"], description="Output formats")
    skip_humanize: bool = False
    skip_review: bool = False


class ChapterGenStatus(BaseModel):
    number: int
    name: str
    status: str
    progress: int


class GenerationStatus(BaseModel):
    run_id: str
    job_id: str
    phase: str
    progress: int
    message: str
    chapter_status: list[ChapterGenStatus] = []


# ── Research ─────────────────────────────────────────
class SourceResponse(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    year: Optional[int] = None
    venue: str = ""
    abstract_summary: str = ""
    paper_url: str = ""
    doi: str = ""
    source_type: str = ""
    citation_count: int = 0
    confidence: float = 0.0


# ── Config ───────────────────────────────────────────
class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str = ""
    temperature: float = 0.7
    api_key_set: bool = False


class ResearchConfig(BaseModel):
    semantic_scholar_api_key_set: bool = False
    openalex_api_key_set: bool = False
    max_papers_per_query: int = 15


class AppConfig(BaseModel):
    llm: LLMConfig
    research: ResearchConfig


# ── Proxy ────────────────────────────────────────────
class ProxyPoolStatus(BaseModel):
    total: int
    working: int
    failed: int
    last_refresh: Optional[datetime] = None


# ── Stats ────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_jobs: int
    total_chapters: int
    total_words: int
    avg_ai_score: Optional[float] = None
    jobs_by_status: dict[str, int] = Field(default_factory=dict)


# ── Health ───────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    db_ok: bool
    llm_configured: bool
    active_runs: int
    timestamp: datetime

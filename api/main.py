"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import SessionLocal, init_db
from api.routes import chapters, config, export, generate, jobs, proxy, research
from api.schemas import HealthResponse
from src.config import get_llm_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="open-work API",
    description="Automated research paper writing system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(chapters.router, prefix="/api/jobs", tags=["chapters"])
app.include_router(generate.router, prefix="/api/jobs", tags=["generate"])
app.include_router(export.router, prefix="/api/jobs", tags=["export"])
app.include_router(research.router, prefix="/api", tags=["research"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(proxy.router, prefix="/api", tags=["proxy"])


@app.get("/api/health", response_model=HealthResponse)
def health():
    llm = get_llm_config()
    llm_ok = bool(llm.get("api_key"))
    db_ok = True
    active_runs = 0
    try:
        from api.services.pipeline_service import _active_runs

        active_runs = sum(1 for t in _active_runs.values() if t is not None)
    except Exception:
        pass
    try:
        with SessionLocal() as db:
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False
    return HealthResponse(
        status="ok",
        db_ok=db_ok,
        llm_configured=llm_ok,
        active_runs=active_runs,
        timestamp=datetime.now(timezone.utc),
    )

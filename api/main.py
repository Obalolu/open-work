"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import init_db
from api.routes import chapters, config, export, generate, jobs, proxy, research


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


@app.get("/api/health")
async def health():
    return {"status": "ok"}

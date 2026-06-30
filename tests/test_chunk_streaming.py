"""Tests for SSE chunk events from the pipeline during writing/humanizing."""

from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.database as db_module
from api.database import Base
from api.main import app
from api.models import Chapter, GenerationRun, Job
from api.services import pipeline_service


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", echo=False)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    monkeypatch.setattr(db_module, "SessionLocal", TestSession)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield TestSession
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def client(test_db):
    return TestClient(app)


def test_subscribe_and_publish_round_trip():
    run_id = "run-1"
    q = pipeline_service.subscribe_to_run(run_id)
    pipeline_service._publish_event(run_id, {"type": "chunk", "text": "hello"})
    pipeline_service._publish_event(run_id, {"type": "complete"})
    received = []
    while True:
        try:
            received.append(q.get_nowait())
        except queue.Empty:
            break
    assert received[0] == {"type": "chunk", "text": "hello"}
    assert received[-1] == {"type": "complete"}
    pipeline_service.unsubscribe_from_run(run_id, q)


def test_subscribe_does_not_cross_runs():
    a = pipeline_service.subscribe_to_run("a")
    b = pipeline_service.subscribe_to_run("b")
    pipeline_service._publish_event("a", {"type": "chunk", "text": "A"})
    pipeline_service._publish_event("b", {"type": "chunk", "text": "B"})
    a_event = a.get_nowait()
    b_event = b.get_nowait()
    assert a_event["text"] == "A"
    assert b_event["text"] == "B"
    pipeline_service.unsubscribe_from_run("a", a)
    pipeline_service.unsubscribe_from_run("b", b)


def test_chunk_event_published_via_set_chapter_status(test_db):
    import api.models  # noqa: F401  -- ensure tables are registered

    run_id = "run-chunk"
    with test_db() as db:
        run = GenerationRun(id=run_id, job_id="j1", phase="writing", progress=50)
        db.add(run)
        db.commit()

    q = pipeline_service.subscribe_to_run(run_id)
    try:
        pipeline_service._set_chapter_status(
            test_db(),
            run_id,
            1,
            "writing",
            60,
            "halfway there",
        )
        evt = q.get(timeout=2)
        assert evt["type"] == "chapter"
        assert evt["chapter"] == 1
        assert evt["status"] == "writing"
    finally:
        pipeline_service.unsubscribe_from_run(run_id, q)


def test_stream_endpoint_serves_chunk_events(client, test_db):
    """End-to-end: subscribe via SSE and confirm chunk events are forwarded."""
    import api.models  # noqa: F401  -- ensure tables are registered

    with test_db() as db:
        job = Job(
            id="job-sse",
            topic="SSE chunk topic",
            paper_type="literature_review",
            citation_style="apa",
            target_audience="graduate_students",
            status="generating",
            config_json="{}",
        )
        run = GenerationRun(
            id="run-sse",
            job_id="job-sse",
            phase="writing",
            progress=20,
        )
        db.add(job)
        db.add(run)
        db.commit()

    # Pre-subscribe so the SSE handler picks up our publishes
    q = pipeline_service.subscribe_to_run("run-sse")

    def _publisher():
        # Give the SSE handler a moment to attach to the queue
        time.sleep(0.2)
        pipeline_service._publish_event(
            "run-sse",
            {"type": "chunk", "chapter": 1, "phase": "writing", "text": "Hello world"},
        )
        time.sleep(0.05)
        pipeline_service._publish_event("run-sse", {"type": "complete"})

    threading.Thread(target=_publisher, daemon=True).start()

    try:
        with client.stream("GET", "/api/jobs/job-sse/generate/stream") as res:
            assert res.status_code == 200
            buffer = ""
            saw_chunk = False
            saw_complete = False
            deadline = time.time() + 5
            for raw in res.iter_bytes():
                if time.time() > deadline:
                    break
                buffer += raw.decode("utf-8", errors="ignore")
                for line in buffer.split("\n\n"):
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        evt = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if evt.get("type") == "chunk" and evt.get("text") == "Hello world":
                        saw_chunk = True
                    if evt.get("type") == "complete":
                        saw_complete = True
                if saw_chunk and saw_complete:
                    break
        assert saw_chunk, "did not receive chunk event via SSE"
        assert saw_complete, "did not receive complete event via SSE"
    finally:
        pipeline_service.unsubscribe_from_run("run-sse", q)

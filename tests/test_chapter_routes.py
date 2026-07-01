"""Tests for the new chapter edit, revision, cancel, and SSE endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models import (
    Chapter,
    ChapterContentRevision,
    GenerationRun,
    HumanizerAttempt,
    Job,
)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def job_id(test_db):
    with test_db() as db:
        job = Job(
            id="job-1",
            topic="Test topic",
            paper_type="literature_review",
            citation_style="apa",
            target_audience="graduate_students",
            status="draft",
            config_json=json.dumps(
                {
                    "chapters": [
                        {"name": "Intro", "template": "chapter_1.yaml"},
                        {"name": "Lit", "template": "chapter_2.yaml"},
                    ],
                    "topic": "Test topic",
                    "citation_style": "apa",
                }
            ),
        )
        db.add(job)
        db.add(
            Chapter(
                job_id="job-1",
                chapter_number=1,
                name="Intro",
                content="hello world",
                word_count=2,
            )
        )
        db.add(
            Chapter(
                job_id="job-1",
                chapter_number=2,
                name="Lit",
                content="literature",
                word_count=1,
            )
        )
        db.commit()
    return "job-1"


def test_health_enriches(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "db_ok" in body
    assert "llm_configured" in body
    assert "active_runs" in body
    assert "timestamp" in body


def test_patch_chapter_creates_revision(client, job_id, tmp_path, test_db):
    res = client.patch(
        f"/api/jobs/{job_id}/chapters/1",
        json={"content": "Edited content from the TipTap editor", "source": "tiptap"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "Edited content from the TipTap editor"
    assert body["word_count"] == 6

    with test_db() as db:
        revs = (
            db.query(ChapterContentRevision)
            .filter(ChapterContentRevision.source == "tiptap")
            .all()
        )
    assert len(revs) == 1
    assert revs[0].summary == ""


def test_list_revisions(client, job_id):
    client.patch(
        f"/api/jobs/{job_id}/chapters/1",
        json={"content": "v1", "source": "tiptap"},
    )
    client.patch(
        f"/api/jobs/{job_id}/chapters/1",
        json={"content": "v2 longer", "source": "tiptap", "summary": "Tightened intro"},
    )
    res = client.get(f"/api/jobs/{job_id}/chapters/1/revisions")
    assert res.status_code == 200
    revs = res.json()
    assert len(revs) == 2
    # Sorted desc by created_at: newest first
    assert revs[0]["summary"] == "Tightened intro"
    assert revs[1]["summary"] == ""


def test_get_revision_content(client, job_id):
    client.patch(
        f"/api/jobs/{job_id}/chapters/1",
        json={"content": "specific content", "source": "tiptap"},
    )
    revs = client.get(f"/api/jobs/{job_id}/chapters/1/revisions").json()
    actual_rev_id = revs[0]["id"]
    res = client.get(f"/api/jobs/{job_id}/chapters/1/revisions/{actual_rev_id}")
    assert res.status_code == 200
    assert res.json()["content"] == "specific content"


def test_cancel_no_active_run_returns_404(client, job_id):
    res = client.post(f"/api/jobs/{job_id}/generate/cancel")
    assert res.status_code == 404


def test_cancel_marks_active_run(client, job_id, test_db):
    with test_db() as db:
        run = GenerationRun(
            id="run-1",
            job_id=job_id,
            phase="writing",
            progress=30,
            message="In progress",
        )
        db.add(run)
        db.commit()

    res = client.post(f"/api/jobs/{job_id}/generate/cancel")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["run_id"] == "run-1"

    with test_db() as db:
        refreshed = db.query(GenerationRun).filter(GenerationRun.id == "run-1").first()
    assert refreshed.cancelled == 1
    assert refreshed.phase == "cancelling"


def test_stream_404_when_no_runs(client, job_id):
    res = client.get(f"/api/jobs/{job_id}/generate/stream")
    assert res.status_code == 404


def test_stream_replays_finished_run(client, job_id, test_db):
    with test_db() as db:
        run = GenerationRun(
            id="run-done",
            job_id=job_id,
            phase="complete",
            progress=100,
            message="All done",
        )
        db.add(run)
        db.commit()

    with client.stream("GET", f"/api/jobs/{job_id}/generate/stream") as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = b""
        for chunk in res.iter_bytes():
            body += chunk
    text = body.decode("utf-8")
    assert "data:" in text
    payload = [line for line in text.splitlines() if line.startswith("data:")][0]
    decoded = json.loads(payload[len("data:"):].strip())
    assert decoded["type"] == "complete"
    assert decoded["phase"] == "complete"


def test_humanizer_attempts_empty(client, job_id):
    res = client.get(f"/api/jobs/{job_id}/chapters/1/humanizer-attempts")
    assert res.status_code == 200
    assert res.json() == []


def test_humanizer_attempt_round_trip(client, job_id, test_db):
    with test_db() as db:
        ch = (
            db.query(Chapter)
            .filter(Chapter.job_id == job_id, Chapter.chapter_number == 1)
            .first()
        )
        attempt = HumanizerAttempt(
            chapter_id=ch.id,
            original_text="orig",
            rewritten_text="rewritten",
            intensity="medium",
            ai_score_before=80.0,
            ai_score_after=42.0,
        )
        db.add(attempt)
        db.commit()

    res = client.get(f"/api/jobs/{job_id}/chapters/1/humanizer-attempts")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["intensity"] == "medium"
    assert body[0]["ai_score_before"] == 80.0
    assert body[0]["ai_score_after"] == 42.0

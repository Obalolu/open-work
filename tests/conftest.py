"""Shared pytest fixtures for API tests.

Provides a per-test in-memory SQLite database and a TestClient bound to a
patched engine/Base.metadata, so tests in different files can run
independently without touching the on-disk database at data/work.db.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.database as db_module
from api.database import Base
from api.main import app


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

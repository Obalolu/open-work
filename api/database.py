"""SQLite database setup with SQLAlchemy."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import get_project_root

DB_PATH = get_project_root() / "data" / "work.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    """Add a column to a SQLite table if it does not already exist."""
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table})"))  # noqa: S608
        columns = {row[1] for row in result}
        if column not in columns:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))  # noqa: S608
            conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Lightweight migrations for columns added after initial deploy.
    _add_column_if_missing("generation_runs", "chapter_status_json", "TEXT DEFAULT '{}'")

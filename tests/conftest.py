"""Shared pytest fixtures for ArkTower tests."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


@pytest.fixture()
def db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the full schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.executescript(migration.read_text())

    yield conn
    conn.close()


@pytest.fixture()
def make_task(db: sqlite3.Connection):
    """Factory fixture that inserts a task row and returns its id."""

    def _make(
        *,
        title: str = "Test task",
        description: str = "",
        status: str = "open",
        priority: str = "medium",
        parent_id: str | None = None,
        **extra: Any,
    ) -> str:
        task_id = uuid.uuid4().hex[:12]
        cols: dict[str, Any] = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "parent_id": parent_id,
            **extra,
        }
        placeholders = ", ".join(f":{k}" for k in cols)
        col_names = ", ".join(cols)
        db.execute(f"INSERT INTO tasks ({col_names}) VALUES ({placeholders})", cols)
        db.commit()
        return task_id

    return _make

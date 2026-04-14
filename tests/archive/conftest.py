"""Fixtures for archive tests (SQLite repository)."""

from __future__ import annotations

from pathlib import Path

import pytest

from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


@pytest.fixture()
def db_conn() -> DatabaseConnection:
    conn = DatabaseConnection(":memory:")
    conn.connect()
    runner = MigrationRunner(conn, MIGRATIONS_DIR)
    runner.run_migrations()
    yield conn
    conn.close()


@pytest.fixture()
def repo(db_conn: DatabaseConnection) -> SqliteTaskRepository:
    return SqliteTaskRepository(db_conn)

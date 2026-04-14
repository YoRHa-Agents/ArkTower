"""CLI dependency wiring: DB connection, migrations, repository, task service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from arktower.config import get_settings
from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

_state: dict[str, Any] = {}


def migrations_dir() -> Path:
    """Directory containing ``*.sql`` migrations (repo root ``migrations/``)."""
    return Path(__file__).resolve().parent.parent.parent / "migrations"


def reset_cli_state() -> None:
    """Close connections and clear cached CLI state (for tests)."""
    conn = _state.get("conn")
    if conn is not None:
        conn.close()
    _state.clear()


def ensure_cli_initialized() -> None:
    """Open DB, run pending migrations, and construct repository + service."""
    if _state.get("ready"):
        return

    settings = get_settings()
    conn = DatabaseConnection(settings.db_path)
    conn.connect()
    runner = MigrationRunner(conn, migrations_dir())
    runner.run_migrations()

    repo = SqliteTaskRepository(conn)
    bus = EventBus()
    service = TaskService(repo, bus)

    _state["conn"] = conn
    _state["repo"] = repo
    _state["service"] = service
    _state["ready"] = True


def get_task_service() -> TaskService:
    ensure_cli_initialized()
    return _state["service"]


def get_repository() -> SqliteTaskRepository:
    ensure_cli_initialized()
    return _state["repo"]

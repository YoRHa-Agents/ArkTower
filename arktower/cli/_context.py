"""CLI-specific service initialization without FastAPI Depends."""

from __future__ import annotations

from pathlib import Path

from arktower.config import Settings
from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

_db: DatabaseConnection | None = None
_svc: TaskService | None = None
_repo: SqliteTaskRepository | None = None


def _boot() -> None:
    global _db, _svc, _repo
    if _svc is not None:
        return
    settings = Settings()
    _db = DatabaseConnection(settings.db_path)
    _db.connect()
    if MIGRATIONS_DIR.is_dir():
        MigrationRunner(_db, MIGRATIONS_DIR).run_migrations()
    _repo = SqliteTaskRepository(_db)
    bus = EventBus()
    _svc = TaskService(_repo, bus)


def get_svc() -> TaskService:
    _boot()
    assert _svc is not None
    return _svc


def get_repo() -> SqliteTaskRepository:
    _boot()
    assert _repo is not None
    return _repo


def reset() -> None:
    """Reset singletons for testing."""
    global _db, _svc, _repo
    if _db is not None:
        _db.close()
    _db = None
    _svc = None
    _repo = None

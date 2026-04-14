"""FastAPI dependencies for settings, persistence, and application services."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from arktower.archive.archive_service import ArchiveService
from arktower.archive.snapshot_writer import SnapshotWriter
from arktower.config import Settings, get_settings
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _run_migrations(conn: DatabaseConnection) -> None:
    if not MIGRATIONS_DIR.is_dir():
        return
    runner = MigrationRunner(conn, MIGRATIONS_DIR)
    runner.run_migrations()


def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[DatabaseConnection, None, None]:
    """Open a SQLite connection for the request and apply pending migrations."""
    conn = DatabaseConnection(settings.db_path)
    conn.connect()
    _run_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()


def get_repository(
    db: Annotated[DatabaseConnection, Depends(get_db)],
) -> SqliteTaskRepository:
    return SqliteTaskRepository(db)


def get_task_service(
    request: Request,
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
) -> TaskService:
    bus = request.app.state.event_bus
    return TaskService(repo, bus)


def get_archive_service(
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ArchiveService:
    writer = SnapshotWriter(settings.archive_dir)
    return ArchiveService(repo, writer)

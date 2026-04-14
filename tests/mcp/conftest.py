"""Fixtures for MCP tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


@pytest.fixture()
def svc():
    db = DatabaseConnection(":memory:")
    db.connect()
    MigrationRunner(db, MIGRATIONS_DIR).run_migrations()
    repo = SqliteTaskRepository(db)
    bus = EventBus()
    return TaskService(repo, bus)

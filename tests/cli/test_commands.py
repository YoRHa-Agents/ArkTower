"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from arktower.cli import _context as ctx
from arktower.cli.app import app
from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskService
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"
runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_db():
    """Wire up in-memory DB for every test."""
    ctx.reset()

    db = DatabaseConnection(":memory:")
    db.connect()
    MigrationRunner(db, MIGRATIONS_DIR).run_migrations()
    repo = SqliteTaskRepository(db)
    bus = EventBus()
    svc = TaskService(repo, bus)

    ctx._db = db
    ctx._repo = repo
    ctx._svc = svc

    yield

    ctx.reset()


class TestVersion:
    def test_version(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ArkTower" in result.output


class TestTaskCommands:
    def test_task_list_empty(self):
        result = runner.invoke(app, ["task", "list"])
        assert result.exit_code == 0
        assert "No tasks found" in result.output

    def test_task_create_and_list(self):
        result = runner.invoke(app, ["task", "create", "My Test Task"])
        assert result.exit_code == 0
        assert "Created task" in result.output

        result = runner.invoke(app, ["task", "list"])
        assert result.exit_code == 0
        assert "My Test Task" in result.output

    def test_task_create_json(self):
        result = runner.invoke(app, ["task", "create", "JSON Task", "--json"])
        assert result.exit_code == 0
        assert '"title"' in result.output

    def test_task_create_with_options(self):
        result = runner.invoke(app, [
            "task", "create", "Priority Task",
            "--priority", "high",
            "--tags", "python,api",
            "--description", "A test",
        ])
        assert result.exit_code == 0
        assert "Created task" in result.output

    def test_task_show(self):
        import json as json_mod
        result = runner.invoke(app, ["task", "create", "Show Task", "--json"])
        task_data = json_mod.loads(result.output)
        task_id = task_data["id"]

        result = runner.invoke(app, ["task", "show", task_id])
        assert result.exit_code == 0
        assert "Show Task" in result.output

    def test_task_show_not_found(self):
        result = runner.invoke(app, ["task", "show", "nonexistent"])
        assert result.exit_code == 1

    def test_task_update(self):
        import json as json_mod
        result = runner.invoke(app, ["task", "create", "Old Title", "--json"])
        task_data = json_mod.loads(result.output)
        task_id = task_data["id"]

        result = runner.invoke(app, ["task", "update", task_id, "--title", "New Title"])
        assert result.exit_code == 0
        assert "Updated task" in result.output


class TestPoolCommands:
    def test_pool_stats(self):
        result = runner.invoke(app, ["pool", "stats"])
        assert result.exit_code == 0
        assert "total" in result.output.lower()

    def test_pool_stats_json(self):
        result = runner.invoke(app, ["pool", "stats", "--json"])
        assert result.exit_code == 0
        assert '"total"' in result.output

    def test_pool_next_empty(self):
        result = runner.invoke(app, ["pool", "next"])
        assert result.exit_code == 0
        assert "No queued tasks" in result.output

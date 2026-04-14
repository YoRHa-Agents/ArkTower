"""Tests for arktower.store.migration."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationError, MigrationRunner

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


class TestMigrationRunner:
    def test_initial_version_is_zero(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            assert runner.get_current_version() == 0

    def test_run_migrations_applies_all(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            count = runner.run_migrations()
            assert count == 3
            assert runner.get_current_version() == 3

    def test_run_migrations_idempotent(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            runner.run_migrations()
            second_run = runner.run_migrations()
            assert second_run == 0
            assert runner.get_current_version() == 3

    def test_pending_migrations_before_run(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            pending = runner.get_pending_migrations()
            assert len(pending) == 3
            assert pending[0].name.startswith("001")

    def test_pending_migrations_after_run(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            runner.run_migrations()
            assert runner.get_pending_migrations() == []

    def test_tables_created(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            runner.run_migrations()
            conn = db.get_connection()
            tables = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for expected in ("tasks", "tags", "dependencies", "task_history",
                             "task_templates", "archives", "schema_version"):
                assert expected in tables, f"Missing table: {expected}"

    def test_fts_virtual_tables_created(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, MIGRATIONS_DIR)
            runner.run_migrations()
            conn = db.get_connection()
            tables = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "tasks_fts" in tables
            assert "archives_fts" in tables

    def test_empty_migrations_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with DatabaseConnection(":memory:") as db:
                runner = MigrationRunner(db, Path(tmpdir))
                assert runner.run_migrations() == 0

    def test_nonexistent_migrations_dir(self) -> None:
        with DatabaseConnection(":memory:") as db:
            runner = MigrationRunner(db, Path("/nonexistent/path"))
            assert runner.get_pending_migrations() == []
            assert runner.run_migrations() == 0

    def test_bad_sql_raises_migration_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "001_bad.sql"
            bad_file.write_text("THIS IS NOT VALID SQL;")
            with DatabaseConnection(":memory:") as db:
                runner = MigrationRunner(db, Path(tmpdir))
                with pytest.raises(MigrationError) as exc_info:
                    runner.run_migrations()
                assert exc_info.value.version == 1

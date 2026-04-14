"""Tests for arktower.store.connection."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from arktower.store.connection import DatabaseConnection


class TestDatabaseConnection:
    def test_connect_returns_connection(self) -> None:
        db = DatabaseConnection(":memory:")
        conn = db.connect()
        assert isinstance(conn, sqlite3.Connection)
        db.close()

    def test_get_connection_lazy(self) -> None:
        db = DatabaseConnection(":memory:")
        conn = db.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert db.get_connection() is conn
        db.close()

    def test_close_sets_none(self) -> None:
        db = DatabaseConnection(":memory:")
        db.connect()
        db.close()
        conn2 = db.get_connection()
        assert isinstance(conn2, sqlite3.Connection)
        db.close()

    def test_context_manager(self) -> None:
        with DatabaseConnection(":memory:") as db:
            conn = db.get_connection()
            assert isinstance(conn, sqlite3.Connection)

    def test_foreign_keys_enabled(self) -> None:
        with DatabaseConnection(":memory:") as db:
            row = db.get_connection().execute("PRAGMA foreign_keys").fetchone()
            assert row[0] == 1

    def test_wal_mode_on_file_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.db"
            with DatabaseConnection(str(path)) as db:
                row = db.get_connection().execute("PRAGMA journal_mode").fetchone()
                assert row[0] == "wal"

    def test_memory_skips_wal(self) -> None:
        with DatabaseConnection(":memory:") as db:
            row = db.get_connection().execute("PRAGMA journal_mode").fetchone()
            assert row[0] != "wal"

    def test_db_path_property(self) -> None:
        db = DatabaseConnection("/tmp/test.db")
        assert db.db_path == "/tmp/test.db"

    def test_connect_idempotent(self) -> None:
        db = DatabaseConnection(":memory:")
        conn1 = db.connect()
        conn2 = db.connect()
        assert conn1 is conn2
        db.close()

"""Fixtures for API tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arktower.api.dependencies import get_db, get_settings
from arktower.api.rest_routes import create_app
from arktower.config import Settings
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


@pytest.fixture()
def api_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "test.db",
        archive_dir=tmp_path / "archives",
    )


@pytest.fixture()
def db_conn(api_settings: Settings) -> Generator[DatabaseConnection, None, None]:
    conn = DatabaseConnection(api_settings.db_path)
    conn.connect()
    MigrationRunner(conn, MIGRATIONS_DIR).run_migrations()
    yield conn
    conn.close()


@pytest.fixture()
def client(db_conn: DatabaseConnection, api_settings: Settings):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: api_settings

    def override_get_db() -> Generator[DatabaseConnection, None, None]:
        yield db_conn

    application.dependency_overrides[get_db] = override_get_db

    with TestClient(application) as tc:
        yield tc

"""Application configuration via environment variables and .env files."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ArkTower runtime configuration.

    Values are read from environment variables prefixed with ``ARKTOWER_``
    (e.g. ``ARKTOWER_DB_PATH``), or from a ``.env`` file if present.
    """

    model_config = {"env_prefix": "ARKTOWER_"}

    db_path: Path = Path("arktower.db")
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
    archive_dir: Path = Path(".arktower/archives")
    mcp_transport: Literal["stdio", "sse"] = "stdio"


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

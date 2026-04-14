"""Write and read JSON task snapshots on disk."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from arktower.core.models import Task, TaskEvent

logger = logging.getLogger(__name__)

_SNAPSHOT_SUFFIX = ".json"


class SnapshotWriter:
    """Persists ``Task`` + ``TaskEvent`` history as JSON files under ``archive_dir``."""

    def __init__(self, archive_dir: Path) -> None:
        self._archive_dir = Path(archive_dir)
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    @property
    def archive_dir(self) -> Path:
        return self._archive_dir

    def _path_for(self, task_id: str) -> Path:
        return self._archive_dir / f"{task_id}{_SNAPSHOT_SUFFIX}"

    def write_snapshot(self, task: Task, history: list[TaskEvent]) -> Path:
        """Serialize *task* and *history* to ``{archive_dir}/{task.id}.json``."""
        payload: dict[str, Any] = {
            "version": 1,
            "task": task.model_dump(mode="json"),
            "history": [e.model_dump(mode="json") for e in history],
        }
        path = self._path_for(task.id)
        text = json.dumps(payload, indent=2, sort_keys=True)
        path.write_text(text, encoding="utf-8")
        logger.info("Wrote snapshot for task %s to %s", task.id, path)
        return path

    def read_snapshot(self, task_id: str) -> dict[str, Any] | None:
        """Load snapshot JSON for *task_id*, or ``None`` if missing."""
        path = self._path_for(task_id)
        if not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)

    def list_snapshots(self) -> list[dict[str, Any]]:
        """Return metadata for each ``*.json`` file in ``archive_dir`` (sorted by task id)."""
        rows: list[dict[str, Any]] = []
        for path in sorted(self._archive_dir.glob(f"*{_SNAPSHOT_SUFFIX}")):
            if not path.is_file():
                continue
            task_id = path.name[: -len(_SNAPSHOT_SUFFIX)]
            stat = path.stat()
            rows.append(
                {
                    "task_id": task_id,
                    "path": path,
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                }
            )
        return rows

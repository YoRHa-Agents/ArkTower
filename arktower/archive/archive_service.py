"""High-level archive / restore operations over a repository and snapshot store."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from arktower.archive.export_formats import ExportFormats
from arktower.archive.snapshot_writer import SnapshotWriter
from arktower.core.models import Task, TaskEvent, TaskFilter, TaskStatus
from arktower.store.repository import TaskRepository

logger = logging.getLogger(__name__)

TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELED,
        TaskStatus.TIMED_OUT,
    }
)


class ArchiveError(Exception):
    """Raised when an archive operation cannot complete."""


class ArchiveService:
    """Archive terminal tasks to JSON snapshots and restore them when needed."""

    def __init__(self, repository: TaskRepository, snapshot_writer: SnapshotWriter) -> None:
        self._repository = repository
        self._writer = snapshot_writer

    def archive_task(self, task_id: str) -> Path:
        """Snapshot a terminal task and remove it from the active pool."""
        task = self._repository.get(task_id)
        if task is None:
            raise ArchiveError(f"Task not found: {task_id}")
        if task.status not in TERMINAL_STATUSES:
            raise ArchiveError(
                f"Task {task_id} is not in a terminal state (status={task.status.value})"
            )
        history = self._repository.get_history(task_id)
        path = self._writer.write_snapshot(task, history)
        try:
            deleted = self._repository.delete(task_id)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        if not deleted:
            path.unlink(missing_ok=True)
            raise ArchiveError(f"Failed to delete task {task_id} after writing snapshot")
        logger.info("Archived task %s to %s", task_id, path)
        return path

    def bulk_archive(self, older_than_days: int) -> list[Path]:
        """Archive all terminal tasks whose completion (or last update) is older than *cutoff*."""
        if older_than_days < 0:
            raise ValueError("older_than_days must be >= 0")
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        filters = TaskFilter(
            status=list(TERMINAL_STATUSES),
            limit=100_000,
            offset=0,
        )
        candidates = self._repository.list(filters)
        paths: list[Path] = []
        for task in candidates:
            end_time = task.completed_at or task.updated_at
            if end_time is None:
                continue
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            if end_time >= cutoff:
                continue
            paths.append(self.archive_task(task.id))
        return paths

    def restore_task(self, task_id: str) -> Task:
        """Load ``{archive_dir}/{task_id}.json`` and recreate the task plus history."""
        raw = self._writer.read_snapshot(task_id)
        if raw is None:
            raise FileNotFoundError(f"No snapshot for task_id={task_id!r}")
        if self._repository.get(task_id) is not None:
            raise ArchiveError(f"Task already exists in pool: {task_id}")
        task = Task.model_validate(raw["task"])
        events = [TaskEvent.model_validate(e) for e in raw.get("history", [])]
        self._repository.create(task)
        for event in events:
            self._repository.record_event(event)
        logger.info("Restored task %s from archive with %d events", task_id, len(events))
        restored = self._repository.get(task_id)
        if restored is None:
            raise ArchiveError(f"Restore failed: task {task_id} not found after create")
        return restored

    def export_archives(self, fmt: str = "json") -> str:
        """Export all on-disk snapshots using :class:`ExportFormats`."""
        key = fmt.lower().strip()
        payloads = self._all_snapshot_payloads()
        if key == "json":
            return ExportFormats.to_json(payloads)
        if key == "ndjson":
            return ExportFormats.to_ndjson(payloads)
        if key == "csv":
            rows = [_flatten_snapshot(p) for p in payloads]
            return ExportFormats.to_csv(rows)
        if key in ("md", "markdown", "task_md"):
            parts: list[str] = []
            for p in payloads:
                task_data = p.get("task")
                if isinstance(task_data, dict):
                    parts.append(ExportFormats.to_task_md(task_data))
            return "\n".join(parts)
        raise ValueError(f"Unsupported export format: {fmt!r}")

    def get_archive_stats(self) -> dict[str, Any]:
        """Aggregate counts from snapshot files under the writer's directory."""
        rows = self._writer.list_snapshots()
        total_bytes = sum(int(r["size_bytes"]) for r in rows)
        by_status: dict[str, int] = {}
        for row in rows:
            tid = row["task_id"]
            snap = self._writer.read_snapshot(tid)
            if snap is None:
                logger.warning("Snapshot metadata exists but file missing for %s", tid)
                continue
            task = snap.get("task")
            if isinstance(task, dict):
                status = str(task.get("status", "unknown"))
            else:
                status = "unknown"
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "count": len(rows),
            "total_bytes": total_bytes,
            "by_status": by_status,
        }

    def _all_snapshot_payloads(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in self._writer.list_snapshots():
            tid = row["task_id"]
            snap = self._writer.read_snapshot(tid)
            if snap is not None:
                out.append(snap)
        return out


def _flatten_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    task = snap.get("task")
    if not isinstance(task, dict):
        return {"history_count": len(snap.get("history", []))}
    flat: dict[str, Any] = {f"task_{k}": v for k, v in task.items()}
    flat["history_count"] = len(snap.get("history", []))
    return flat

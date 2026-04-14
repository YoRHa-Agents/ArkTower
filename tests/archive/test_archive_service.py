"""Tests for SnapshotWriter, ExportFormats, and ArchiveService."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from arktower.archive.archive_service import ArchiveError, ArchiveService
from arktower.archive.export_formats import ExportFormats
from arktower.archive.snapshot_writer import SnapshotWriter
from arktower.core.models import (
    Task,
    TaskEvent,
    TaskStatus,
    Trigger,
)
from arktower.store.sqlite_repository import SqliteTaskRepository


@pytest.fixture()
def archive_dir(tmp_path: Path) -> Path:
    d = tmp_path / "archives"
    d.mkdir()
    return d


@pytest.fixture()
def snapshot_writer(archive_dir: Path) -> SnapshotWriter:
    return SnapshotWriter(archive_dir)


@pytest.fixture()
def archive_service(
    repo: SqliteTaskRepository,
    snapshot_writer: SnapshotWriter,
) -> ArchiveService:
    return ArchiveService(repo, snapshot_writer)


def _completed_task(
    *,
    title: str = "Done",
    completed_at: datetime | None = None,
) -> Task:
    now = datetime.now(timezone.utc)
    return Task(
        title=title,
        status=TaskStatus.COMPLETED,
        completed_at=completed_at or now,
        updated_at=now,
    )


def test_snapshot_writer_roundtrip(snapshot_writer: SnapshotWriter) -> None:
    task = _completed_task(title="snap")
    history = [
        TaskEvent(
            task_id=task.id,
            trigger=Trigger.COMPLETE,
            from_status=TaskStatus.IN_PROGRESS,
            to_status=TaskStatus.COMPLETED,
        )
    ]
    path = snapshot_writer.write_snapshot(task, history)
    assert path.is_file()
    data = snapshot_writer.read_snapshot(task.id)
    assert data is not None
    assert data["task"]["title"] == "snap"
    assert len(data["history"]) == 1


def test_snapshot_writer_read_missing_returns_none(snapshot_writer: SnapshotWriter) -> None:
    assert snapshot_writer.read_snapshot("no-such-id") is None


def test_snapshot_writer_list_snapshots_empty(snapshot_writer: SnapshotWriter) -> None:
    assert snapshot_writer.list_snapshots() == []


def test_snapshot_writer_list_snapshots_metadata(
    snapshot_writer: SnapshotWriter,
) -> None:
    task = _completed_task()
    snapshot_writer.write_snapshot(task, [])
    rows = snapshot_writer.list_snapshots()
    assert len(rows) == 1
    assert rows[0]["task_id"] == task.id
    assert rows[0]["size_bytes"] > 0


def test_export_formats_json() -> None:
    s = ExportFormats.to_json({"a": 1, "b": [2]})
    assert '"a": 1' in s


def test_export_formats_ndjson() -> None:
    s = ExportFormats.to_ndjson([{"x": 1}, {"y": 2}])
    assert s.count("\n") == 2


def test_export_formats_csv() -> None:
    s = ExportFormats.to_csv([{"id": "a", "n": 1}, {"id": "b", "n": 2}])
    assert "id" in s and "a" in s


def test_export_formats_task_md() -> None:
    md = ExportFormats.to_task_md(
        {"id": "t1", "title": "Hello", "status": "completed", "description": "Body"}
    )
    assert "# Hello" in md
    assert "`t1`" in md
    assert "Body" in md


def test_archive_task_non_terminal_raises(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
) -> None:
    t = Task(title="open", status=TaskStatus.SUBMITTED)
    repo.create(t)
    with pytest.raises(ArchiveError, match="terminal"):
        archive_service.archive_task(t.id)


def test_archive_task_missing_raises(
    archive_service: ArchiveService,
) -> None:
    with pytest.raises(ArchiveError, match="not found"):
        archive_service.archive_task("missing-id")


def test_archive_task_deletes_and_writes_snapshot(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
    snapshot_writer: SnapshotWriter,
) -> None:
    task = _completed_task(title="gone")
    repo.create(task)
    ev = TaskEvent(
        task_id=task.id,
        trigger=Trigger.COMPLETE,
        from_status=TaskStatus.IN_PROGRESS,
        to_status=TaskStatus.COMPLETED,
    )
    repo.record_event(ev)

    path = archive_service.archive_task(task.id)
    assert path.is_file()
    assert repo.get(task.id) is None
    snap = snapshot_writer.read_snapshot(task.id)
    assert snap is not None
    assert len(snap["history"]) == 1


def test_restore_roundtrip(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
) -> None:
    task = _completed_task(title="restore me")
    repo.create(task)
    repo.record_event(
        TaskEvent(
            task_id=task.id,
            trigger=Trigger.COMPLETE,
            from_status=TaskStatus.QUEUED,
            to_status=TaskStatus.COMPLETED,
        )
    )
    archive_service.archive_task(task.id)
    assert repo.get(task.id) is None

    restored = archive_service.restore_task(task.id)
    assert restored.title == "restore me"
    assert len(repo.get_history(task.id)) == 1


def test_restore_missing_snapshot_raises(
    archive_service: ArchiveService,
) -> None:
    with pytest.raises(FileNotFoundError):
        archive_service.restore_task("nope")


def test_restore_conflict_existing_task(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
    snapshot_writer: SnapshotWriter,
) -> None:
    task = _completed_task(title="conflict")
    repo.create(task)
    snapshot_writer.write_snapshot(task, [])
    repo.delete(task.id)
    repo.create(Task(id=task.id, title="other", status=TaskStatus.SUBMITTED))
    with pytest.raises(ArchiveError, match="already exists"):
        archive_service.restore_task(task.id)


def test_bulk_archive_age_filter(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
) -> None:
    old = _completed_task(
        title="old",
        completed_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    new = _completed_task(
        title="new",
        completed_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    repo.create(old)
    repo.create(new)

    paths = archive_service.bulk_archive(older_than_days=7)
    assert len(paths) == 1
    assert repo.get(old.id) is None
    assert repo.get(new.id) is not None


def test_bulk_archive_negative_days_raises(archive_service: ArchiveService) -> None:
    with pytest.raises(ValueError):
        archive_service.bulk_archive(older_than_days=-1)


def test_export_archives_variants(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
) -> None:
    task = _completed_task(title="export")
    repo.create(task)
    archive_service.archive_task(task.id)

    j = archive_service.export_archives("json")
    assert "export" in j
    n = archive_service.export_archives("ndjson")
    assert "export" in n
    c = archive_service.export_archives("csv")
    assert "task_title" in c or "export" in c
    m = archive_service.export_archives("md")
    assert "# export" in m


def test_export_archives_invalid_format_raises(
    archive_service: ArchiveService,
) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        archive_service.export_archives("xml")


def test_get_archive_stats(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
) -> None:
    t1 = _completed_task(title="s1")
    t2 = Task(title="failed", status=TaskStatus.FAILED, completed_at=datetime.now(timezone.utc))
    repo.create(t1)
    repo.create(t2)
    archive_service.archive_task(t1.id)
    archive_service.archive_task(t2.id)

    stats = archive_service.get_archive_stats()
    assert stats["count"] == 2
    assert stats["total_bytes"] > 0
    assert stats["by_status"].get("completed") == 1
    assert stats["by_status"].get("failed") == 1


def test_failed_status_can_be_archived(
    archive_service: ArchiveService,
    repo: SqliteTaskRepository,
) -> None:
    task = Task(title="bad", status=TaskStatus.FAILED, completed_at=datetime.now(timezone.utc))
    repo.create(task)
    path = archive_service.archive_task(task.id)
    assert path.is_file()

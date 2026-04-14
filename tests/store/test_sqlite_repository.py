"""Tests for arktower.store.sqlite_repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from arktower.core.models import (
    Dependency,
    DependencyType,
    Task,
    TaskEvent,
    TaskFilter,
    TaskPriority,
    TaskStatus,
    TaskTemplate,
    TaskUpdate,
    Trigger,
)
from arktower.store.connection import DatabaseConnection
from arktower.store.sqlite_repository import (
    ClaimFailedError,
    SqliteTaskRepository,
    TaskNotFoundError,
)


# ── helpers ──────────────────────────────────────────────────────────────


def _make_task(**overrides) -> Task:
    defaults = {
        "id": str(uuid.uuid4()),
        "title": "Test task",
        "description": "A test task description",
        "status": TaskStatus.SUBMITTED,
        "priority": TaskPriority.MEDIUM,
        "tags": ["test"],
        "labels": {"env": "dev"},
        "parameters": {"key": "value"},
    }
    defaults.update(overrides)
    return Task(**defaults)


# ── Task CRUD ────────────────────────────────────────────────────────────


class TestCreate:
    def test_create_and_retrieve(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        created = repo.create(task)
        assert created.id == task.id

        fetched = repo.get(task.id)
        assert fetched is not None
        assert fetched.title == "Test task"
        assert fetched.tags == ["test"]
        assert fetched.labels == {"env": "dev"}
        assert fetched.parameters == {"key": "value"}

    def test_create_preserves_all_fields(self, repo: SqliteTaskRepository) -> None:
        task = _make_task(
            parent_id=None,
            context_id="ctx-1",
            owner_id="alice",
            assigned_to="bob",
            assigned_type="human",
            output="some output",
            error="some error",
            max_steps=10,
        )
        repo.create(task)
        fetched = repo.get(task.id)
        assert fetched is not None
        assert fetched.context_id == "ctx-1"
        assert fetched.owner_id == "alice"
        assert fetched.assigned_to == "bob"
        assert fetched.assigned_type == "human"
        assert fetched.output == "some output"
        assert fetched.error == "some error"
        assert fetched.max_steps == 10


class TestGet:
    def test_get_nonexistent(self, repo: SqliteTaskRepository) -> None:
        assert repo.get("nonexistent-id") is None


class TestUpdate:
    def test_update_title(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        updated = repo.update(task.id, TaskUpdate(title="New title"))
        assert updated.title == "New title"
        assert updated.version == 2

    def test_update_priority(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        updated = repo.update(task.id, TaskUpdate(priority=TaskPriority.CRITICAL))
        assert updated.priority == TaskPriority.CRITICAL

    def test_update_tags(self, repo: SqliteTaskRepository) -> None:
        task = _make_task(tags=["a", "b"])
        repo.create(task)
        updated = repo.update(task.id, TaskUpdate(tags=["c", "d"]))
        assert sorted(updated.tags) == ["c", "d"]

    def test_update_labels(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        updated = repo.update(task.id, TaskUpdate(labels={"team": "backend"}))
        assert updated.labels == {"team": "backend"}

    def test_update_parameters(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        updated = repo.update(task.id, TaskUpdate(parameters={"new": "param"}))
        assert updated.parameters == {"new": "param"}

    def test_update_nonexistent_raises(self, repo: SqliteTaskRepository) -> None:
        with pytest.raises(TaskNotFoundError):
            repo.update("nonexistent", TaskUpdate(title="x"))

    def test_update_noop_returns_existing(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        result = repo.update(task.id, TaskUpdate())
        assert result.version == 1


class TestDelete:
    def test_delete_existing(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        assert repo.delete(task.id) is True
        assert repo.get(task.id) is None

    def test_delete_nonexistent(self, repo: SqliteTaskRepository) -> None:
        assert repo.delete("nonexistent") is False

    def test_delete_cascades_tags(self, repo: SqliteTaskRepository) -> None:
        task = _make_task(tags=["a", "b"])
        repo.create(task)
        repo.delete(task.id)
        conn = repo._conn
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM tags WHERE task_id = ?", (task.id,)
        ).fetchone()["c"]
        assert count == 0


# ── List & filter ────────────────────────────────────────────────────────


class TestList:
    def test_list_empty(self, repo: SqliteTaskRepository) -> None:
        result = repo.list(TaskFilter())
        assert result == []

    def test_list_returns_tasks(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="T1"))
        repo.create(_make_task(title="T2"))
        result = repo.list(TaskFilter())
        assert len(result) == 2

    def test_filter_by_status(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="S1", status=TaskStatus.SUBMITTED))
        repo.create(_make_task(title="S2", status=TaskStatus.QUEUED))
        result = repo.list(TaskFilter(status=[TaskStatus.QUEUED]))
        assert len(result) == 1
        assert result[0].status == TaskStatus.QUEUED

    def test_filter_by_priority(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="P1", priority=TaskPriority.LOW))
        repo.create(_make_task(title="P2", priority=TaskPriority.HIGH))
        result = repo.list(TaskFilter(priority=[TaskPriority.HIGH]))
        assert len(result) == 1
        assert result[0].priority == TaskPriority.HIGH

    def test_filter_by_tags(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="T1", tags=["backend"]))
        repo.create(_make_task(title="T2", tags=["frontend"]))
        result = repo.list(TaskFilter(tags=["backend"]))
        assert len(result) == 1
        assert result[0].title == "T1"

    def test_filter_by_assigned_to(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="A1", assigned_to="agent-1"))
        repo.create(_make_task(title="A2", assigned_to="agent-2"))
        result = repo.list(TaskFilter(assigned_to="agent-1"))
        assert len(result) == 1

    def test_filter_by_context_id(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="C1", context_id="sprint-1"))
        repo.create(_make_task(title="C2", context_id="sprint-2"))
        result = repo.list(TaskFilter(context_id="sprint-1"))
        assert len(result) == 1
        assert result[0].context_id == "sprint-1"

    def test_limit_and_offset(self, repo: SqliteTaskRepository) -> None:
        for i in range(5):
            repo.create(_make_task(title=f"Task-{i}"))
        result = repo.list(TaskFilter(limit=2, offset=0))
        assert len(result) == 2
        result2 = repo.list(TaskFilter(limit=2, offset=2))
        assert len(result2) == 2

    def test_filter_combined(self, repo: SqliteTaskRepository) -> None:
        repo.create(
            _make_task(
                title="Match",
                status=TaskStatus.QUEUED,
                priority=TaskPriority.HIGH,
                tags=["backend"],
            )
        )
        repo.create(
            _make_task(
                title="NoMatch",
                status=TaskStatus.SUBMITTED,
                priority=TaskPriority.LOW,
            )
        )
        result = repo.list(
            TaskFilter(
                status=[TaskStatus.QUEUED],
                priority=[TaskPriority.HIGH],
                tags=["backend"],
            )
        )
        assert len(result) == 1
        assert result[0].title == "Match"


class TestCount:
    def test_count_all(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="A"))
        repo.create(_make_task(title="B"))
        assert repo.count(TaskFilter()) == 2

    def test_count_filtered(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(status=TaskStatus.QUEUED))
        repo.create(_make_task(status=TaskStatus.SUBMITTED))
        assert repo.count(TaskFilter(status=[TaskStatus.QUEUED])) == 1


# ── FTS5 search ──────────────────────────────────────────────────────────


class TestFTS5Search:
    def test_search_by_title(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="Implement authentication"))
        repo.create(_make_task(title="Write tests"))
        result = repo.list(TaskFilter(search="authentication"))
        assert len(result) == 1
        assert "authentication" in result[0].title

    def test_search_by_description(self, repo: SqliteTaskRepository) -> None:
        repo.create(
            _make_task(title="Task A", description="JWT token validation needed")
        )
        repo.create(_make_task(title="Task B", description="Nothing relevant"))
        result = repo.list(TaskFilter(search="JWT"))
        assert len(result) == 1

    def test_search_no_results(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="Something"))
        result = repo.list(TaskFilter(search="nonexistent_xyz"))
        assert result == []

    def test_search_combined_with_status_filter(
        self, repo: SqliteTaskRepository
    ) -> None:
        repo.create(
            _make_task(title="Auth feature", status=TaskStatus.QUEUED)
        )
        repo.create(
            _make_task(title="Auth bugfix", status=TaskStatus.SUBMITTED)
        )
        result = repo.list(
            TaskFilter(search="Auth", status=[TaskStatus.QUEUED])
        )
        assert len(result) == 1
        assert result[0].status == TaskStatus.QUEUED


# ── Atomic claim ─────────────────────────────────────────────────────────


class TestAtomicClaim:
    def test_claim_queued_task(self, repo: SqliteTaskRepository) -> None:
        task = _make_task(status=TaskStatus.QUEUED)
        repo.create(task)
        claimed = repo.atomic_claim(task.id, "agent-1", "cursor")
        assert claimed.status == TaskStatus.IN_PROGRESS
        assert claimed.assigned_to == "agent-1"
        assert claimed.assigned_type == "cursor"
        assert claimed.started_at is not None

    def test_claim_non_queued_raises(self, repo: SqliteTaskRepository) -> None:
        task = _make_task(status=TaskStatus.SUBMITTED)
        repo.create(task)
        with pytest.raises(ClaimFailedError):
            repo.atomic_claim(task.id, "agent-1")

    def test_claim_nonexistent_raises(self, repo: SqliteTaskRepository) -> None:
        with pytest.raises(ClaimFailedError):
            repo.atomic_claim("nonexistent", "agent-1")

    def test_double_claim_fails(self, repo: SqliteTaskRepository) -> None:
        task = _make_task(status=TaskStatus.QUEUED)
        repo.create(task)
        repo.atomic_claim(task.id, "agent-1")
        with pytest.raises(ClaimFailedError):
            repo.atomic_claim(task.id, "agent-2")


# ── Events / audit log ──────────────────────────────────────────────────


class TestEvents:
    def test_record_and_get_history(self, repo: SqliteTaskRepository) -> None:
        task = _make_task()
        repo.create(task)
        event = TaskEvent(
            task_id=task.id,
            trigger=Trigger.SUBMIT,
            from_status=TaskStatus.SUBMITTED,
            to_status=TaskStatus.SUBMITTED,
            actor="system",
        )
        repo.record_event(event)
        history = repo.get_history(task.id)
        assert len(history) == 1
        assert history[0].event_id == event.event_id
        assert history[0].trigger == Trigger.SUBMIT

    def test_history_ordered_by_timestamp(
        self, repo: SqliteTaskRepository
    ) -> None:
        task = _make_task()
        repo.create(task)
        for trigger in (Trigger.SUBMIT, Trigger.ENQUEUE, Trigger.CLAIM):
            repo.record_event(
                TaskEvent(
                    task_id=task.id,
                    trigger=trigger,
                    from_status=TaskStatus.SUBMITTED,
                    to_status=TaskStatus.QUEUED,
                )
            )
        history = repo.get_history(task.id)
        assert len(history) == 3

    def test_empty_history(self, repo: SqliteTaskRepository) -> None:
        assert repo.get_history("nonexistent") == []


# ── Dependencies ─────────────────────────────────────────────────────────


class TestDependencies:
    def test_create_and_get_dependencies(
        self, repo: SqliteTaskRepository
    ) -> None:
        t1 = _make_task(title="Task 1")
        t2 = _make_task(title="Task 2")
        repo.create(t1)
        repo.create(t2)
        dep = Dependency(
            from_task_id=t1.id,
            to_task_id=t2.id,
            dep_type=DependencyType.BLOCKS,
        )
        repo.create_dependency(dep)
        deps = repo.get_dependencies(t1.id)
        assert len(deps) == 1
        assert deps[0].to_task_id == t2.id

    def test_get_dependents(self, repo: SqliteTaskRepository) -> None:
        t1 = _make_task(title="Task 1")
        t2 = _make_task(title="Task 2")
        repo.create(t1)
        repo.create(t2)
        dep = Dependency(from_task_id=t1.id, to_task_id=t2.id)
        repo.create_dependency(dep)
        dependents = repo.get_dependents(t2.id)
        assert len(dependents) == 1
        assert dependents[0].from_task_id == t1.id

    def test_empty_dependencies(self, repo: SqliteTaskRepository) -> None:
        t = _make_task()
        repo.create(t)
        assert repo.get_dependencies(t.id) == []
        assert repo.get_dependents(t.id) == []

    def test_self_dependency_rejected(self, repo: SqliteTaskRepository) -> None:
        t = _make_task()
        repo.create(t)
        with pytest.raises(Exception):
            repo.create_dependency(
                Dependency(from_task_id=t.id, to_task_id=t.id)
            )


# ── Templates ────────────────────────────────────────────────────────────


class TestTemplates:
    def test_create_and_get_template(self, repo: SqliteTaskRepository) -> None:
        tpl = TaskTemplate(
            name="bug-fix",
            description="Standard bug fix workflow",
            default_priority=TaskPriority.HIGH,
            default_tags=["bug"],
            default_labels={"team": "platform"},
            parameter_schema={"type": "object"},
            checklist=["Reproduce", "Fix", "Test"],
        )
        created = repo.create_template(tpl)
        assert created.id == tpl.id

        fetched = repo.get_template(tpl.id)
        assert fetched is not None
        assert fetched.name == "bug-fix"
        assert fetched.default_tags == ["bug"]
        assert fetched.checklist == ["Reproduce", "Fix", "Test"]

    def test_get_nonexistent_template(self, repo: SqliteTaskRepository) -> None:
        assert repo.get_template("nonexistent") is None

    def test_list_templates(self, repo: SqliteTaskRepository) -> None:
        repo.create_template(TaskTemplate(name="tpl-1"))
        repo.create_template(TaskTemplate(name="tpl-2"))
        templates = repo.list_templates()
        assert len(templates) == 2

    def test_unique_template_name(self, repo: SqliteTaskRepository) -> None:
        repo.create_template(TaskTemplate(name="unique-name"))
        with pytest.raises(Exception):
            repo.create_template(TaskTemplate(name="unique-name"))


# ── Statistics ───────────────────────────────────────────────────────────


class TestStats:
    def test_empty_stats(self, repo: SqliteTaskRepository) -> None:
        stats = repo.get_stats()
        assert stats.total == 0
        assert stats.by_status == {}
        assert stats.by_priority == {}
        assert stats.oldest_queued_age_seconds is None
        assert stats.avg_completion_seconds is None

    def test_stats_by_status(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(status=TaskStatus.SUBMITTED))
        repo.create(_make_task(status=TaskStatus.QUEUED))
        repo.create(_make_task(status=TaskStatus.QUEUED))
        stats = repo.get_stats()
        assert stats.total == 3
        assert stats.by_status["queued"] == 2
        assert stats.by_status["submitted"] == 1

    def test_stats_by_priority(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(priority=TaskPriority.HIGH))
        repo.create(_make_task(priority=TaskPriority.LOW))
        stats = repo.get_stats()
        assert stats.by_priority["high"] == 1
        assert stats.by_priority["low"] == 1

    def test_stats_oldest_queued(self, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(status=TaskStatus.QUEUED))
        stats = repo.get_stats()
        assert stats.oldest_queued_age_seconds is not None
        assert stats.oldest_queued_age_seconds >= 0

    def test_stats_avg_completion(self, repo: SqliteTaskRepository) -> None:
        now = datetime.now(timezone.utc)
        task = _make_task(
            status=TaskStatus.COMPLETED,
            started_at=now,
            completed_at=now,
        )
        repo.create(task)
        stats = repo.get_stats()
        assert stats.avg_completion_seconds is not None

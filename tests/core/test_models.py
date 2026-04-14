"""Tests for arktower.core.models — enums and Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from arktower.core.models import (
    Dependency,
    DependencyType,
    PoolStats,
    Task,
    TaskCreate,
    TaskEvent,
    TaskFilter,
    TaskPriority,
    TaskStatus,
    TaskTemplate,
    TaskUpdate,
    Trigger,
)


# ── Enum coverage ──────────────────────────────────────────────────────────


class TestTaskStatus:
    def test_has_10_members(self) -> None:
        assert len(TaskStatus) == 10

    def test_values(self) -> None:
        expected = {
            "submitted", "queued", "in_progress", "review",
            "input_required", "blocked", "completed", "failed",
            "canceled", "timed_out",
        }
        assert {s.value for s in TaskStatus} == expected

    def test_str_enum_comparison(self) -> None:
        assert TaskStatus.SUBMITTED == "submitted"


class TestTaskPriority:
    def test_has_4_members(self) -> None:
        assert len(TaskPriority) == 4

    def test_ordering(self) -> None:
        values = [p.value for p in TaskPriority]
        assert values == ["low", "medium", "high", "critical"]


class TestTrigger:
    def test_has_15_members(self) -> None:
        assert len(Trigger) == 15

    def test_all_trigger_names(self) -> None:
        expected = {
            "submit", "enqueue", "claim", "request_input", "resume",
            "block", "unblock", "send_review", "approve", "reject",
            "complete", "fail", "cancel", "timeout", "reopen",
        }
        assert {t.value for t in Trigger} == expected


class TestDependencyType:
    def test_has_2_members(self) -> None:
        assert len(DependencyType) == 2


# ── Task model ─────────────────────────────────────────────────────────────


class TestTask:
    def test_minimal_creation(self) -> None:
        task = Task(title="Do something")
        assert task.title == "Do something"
        assert task.status == TaskStatus.SUBMITTED
        assert task.priority == TaskPriority.MEDIUM
        assert task.version == 1
        assert task.id  # auto-generated UUID

    def test_auto_generated_fields(self) -> None:
        task = Task(title="A")
        assert isinstance(task.id, str)
        assert len(task.id) == 36  # UUID4
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_all_fields(self) -> None:
        now = datetime.now(timezone.utc)
        task = Task(
            title="Full task",
            description="desc",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            parent_id="parent-1",
            context_id="ctx-1",
            owner_id="alice",
            assigned_to="agent-1",
            assigned_type="cursor",
            parameters={"key": "val"},
            output="result",
            error=None,
            tags=["backend"],
            labels={"team": "core"},
            template_id="tpl-1",
            max_steps=10,
            version=3,
            created_at=now,
            updated_at=now,
            started_at=now,
            completed_at=None,
        )
        assert task.assigned_type == "cursor"
        assert task.parameters == {"key": "val"}
        assert task.tags == ["backend"]

    def test_serialization_roundtrip(self) -> None:
        task = Task(title="Roundtrip")
        data = task.model_dump()
        restored = Task.model_validate(data)
        assert restored.id == task.id
        assert restored.title == task.title

    def test_json_roundtrip(self) -> None:
        task = Task(title="JSON")
        json_str = task.model_dump_json()
        restored = Task.model_validate_json(json_str)
        assert restored.id == task.id

    def test_agent_capability_fields(self) -> None:
        task = Task(
            title="Agent task",
            capabilities=["python", "testing"],
            required_tools=["pytest"],
            estimated_complexity="medium",
        )
        assert task.capabilities == ["python", "testing"]
        assert task.required_tools == ["pytest"]
        assert task.estimated_complexity == "medium"

    def test_agent_fields_default_empty(self) -> None:
        task = Task(title="Simple")
        assert task.capabilities == []
        assert task.required_tools == []
        assert task.estimated_complexity is None

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Task(title="Bad", status="nonexistent")


# ── TaskCreate ─────────────────────────────────────────────────────────────


class TestTaskCreate:
    def test_minimal(self) -> None:
        tc = TaskCreate(title="New task")
        assert tc.priority == TaskPriority.MEDIUM
        assert tc.owner_id == "system"

    def test_with_all_optional(self) -> None:
        tc = TaskCreate(
            title="Full",
            description="d",
            priority=TaskPriority.CRITICAL,
            parent_id="p",
            context_id="c",
            owner_id="alice",
            tags=["a"],
            labels={"k": "v"},
            parameters={"x": 1},
            template_id="t",
            max_steps=5,
        )
        assert tc.max_steps == 5

    def test_agent_fields_defaults(self) -> None:
        tc = TaskCreate(title="Agent test")
        assert tc.capabilities == []
        assert tc.required_tools == []
        assert tc.estimated_complexity is None

    def test_agent_fields_populated(self) -> None:
        tc = TaskCreate(
            title="Complex task",
            capabilities=["code_review", "testing"],
            required_tools=["pytest", "ruff"],
            estimated_complexity="high",
        )
        assert tc.capabilities == ["code_review", "testing"]
        assert tc.required_tools == ["pytest", "ruff"]
        assert tc.estimated_complexity == "high"


# ── TaskUpdate ─────────────────────────────────────────────────────────────


class TestTaskUpdate:
    def test_all_none_by_default(self) -> None:
        tu = TaskUpdate()
        assert tu.title is None
        assert tu.priority is None

    def test_partial_update(self) -> None:
        tu = TaskUpdate(title="New title", priority=TaskPriority.HIGH)
        non_none = {k: v for k, v in tu.model_dump().items() if v is not None}
        assert set(non_none.keys()) == {"title", "priority"}


# ── TaskFilter ─────────────────────────────────────────────────────────────


class TestTaskFilter:
    def test_defaults(self) -> None:
        tf = TaskFilter()
        assert tf.limit == 50
        assert tf.offset == 0
        assert tf.status is None

    def test_with_filters(self) -> None:
        tf = TaskFilter(
            status=[TaskStatus.QUEUED, TaskStatus.IN_PROGRESS],
            priority=[TaskPriority.HIGH],
            tags=["backend"],
            limit=10,
        )
        assert len(tf.status) == 2


# ── TaskEvent ──────────────────────────────────────────────────────────────


class TestTaskEvent:
    def test_creation(self) -> None:
        evt = TaskEvent(
            task_id="task-1",
            trigger=Trigger.CLAIM,
            from_status=TaskStatus.QUEUED,
            to_status=TaskStatus.IN_PROGRESS,
            actor="agent-1",
        )
        assert evt.event_id  # auto UUID
        assert evt.trigger == Trigger.CLAIM
        assert isinstance(evt.timestamp, datetime)


# ── Dependency ─────────────────────────────────────────────────────────────


class TestDependency:
    def test_defaults(self) -> None:
        dep = Dependency(from_task_id="a", to_task_id="b")
        assert dep.dep_type == DependencyType.BLOCKS

    def test_relates_to(self) -> None:
        dep = Dependency(from_task_id="a", to_task_id="b", dep_type=DependencyType.RELATES_TO)
        assert dep.dep_type == DependencyType.RELATES_TO


# ── TaskTemplate ───────────────────────────────────────────────────────────


class TestTaskTemplate:
    def test_minimal(self) -> None:
        tpl = TaskTemplate(name="bug-fix")
        assert tpl.id
        assert tpl.default_priority == TaskPriority.MEDIUM
        assert tpl.checklist == []

    def test_full(self) -> None:
        tpl = TaskTemplate(
            name="feature",
            description="Feature template",
            default_priority=TaskPriority.HIGH,
            default_tags=["feature"],
            default_labels={"type": "feature"},
            parameter_schema={"type": "object"},
            checklist=["Design", "Implement", "Test"],
        )
        assert len(tpl.checklist) == 3


# ── PoolStats ──────────────────────────────────────────────────────────────


class TestPoolStats:
    def test_defaults(self) -> None:
        ps = PoolStats()
        assert ps.total == 0
        assert ps.by_status == {}
        assert ps.oldest_queued_age_seconds is None

    def test_populated(self) -> None:
        ps = PoolStats(
            total=100,
            by_status={"queued": 30, "in_progress": 20},
            by_priority={"high": 50},
            oldest_queued_age_seconds=120.5,
            avg_completion_seconds=3600.0,
        )
        assert ps.total == 100

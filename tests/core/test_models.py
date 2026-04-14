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

    def test_enriched_fields_defaults(self) -> None:
        task = Task(title="Defaults check")
        assert task.task_type is None
        assert task.kind == "task"
        assert task.timeout_seconds is None
        assert task.max_retries == 0
        assert task.deadline is None
        assert task.budget_tokens is None
        assert task.input_schema == {}
        assert task.output_schema == {}
        assert task.acceptance_criteria == []
        assert task.constraints == []
        assert task.context_refs == []
        assert task.subtask_ids == []
        assert task.quality_thresholds == {}
        assert task.estimated_effort_minutes is None
        assert task.agent_instructions is None
        assert task.preferred_agent_type is None
        assert task.retry_count == 0

    def test_enriched_fields_populated(self) -> None:
        now = datetime.now(timezone.utc)
        task = Task(
            title="Enriched task",
            task_type="feature",
            kind="task",
            timeout_seconds=7200,
            max_retries=3,
            deadline=now,
            budget_tokens=100000,
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
            output_schema={"type": "object"},
            acceptance_criteria=["tests pass", "coverage > 80%", "no lint errors"],
            constraints=["must use RS256", "backward compatible"],
            context_refs=[
                {"type": "file", "path": "src/main.py", "description": "entry point"},
                {"type": "url", "url": "https://docs.example.com", "description": "docs"},
            ],
            subtask_ids=["sub-1", "sub-2"],
            quality_thresholds={"coverage_pct": 80, "quality_score": 85},
            estimated_effort_minutes=120,
            agent_instructions="Use pytest for testing",
            preferred_agent_type="code",
            retry_count=1,
        )
        assert task.task_type == "feature"
        assert task.kind == "task"
        assert task.timeout_seconds == 7200
        assert task.max_retries == 3
        assert task.deadline == now
        assert task.budget_tokens == 100000
        assert "type" in task.input_schema
        assert len(task.acceptance_criteria) == 3
        assert len(task.constraints) == 2
        assert len(task.context_refs) == 2
        assert task.context_refs[0]["type"] == "file"
        assert task.subtask_ids == ["sub-1", "sub-2"]
        assert task.quality_thresholds["coverage_pct"] == 80
        assert task.estimated_effort_minutes == 120
        assert task.agent_instructions == "Use pytest for testing"
        assert task.preferred_agent_type == "code"
        assert task.retry_count == 1

    def test_enriched_fields_json_roundtrip(self) -> None:
        task = Task(
            title="Roundtrip enriched",
            task_type="bugfix",
            acceptance_criteria=["fix the bug", "add regression test"],
            context_refs=[{"type": "task", "id": "parent-1", "description": "parent"}],
            quality_thresholds={"coverage_pct": 90},
            timeout_seconds=3600,
        )
        json_str = task.model_dump_json()
        restored = Task.model_validate_json(json_str)
        assert restored.task_type == "bugfix"
        assert restored.acceptance_criteria == ["fix the bug", "add regression test"]
        assert restored.context_refs[0]["type"] == "task"
        assert restored.quality_thresholds == {"coverage_pct": 90}
        assert restored.timeout_seconds == 3600

    def test_enriched_field_count(self) -> None:
        assert len(Task.model_fields) >= 42


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

    def test_enriched_create_defaults(self) -> None:
        tc = TaskCreate(title="Enriched defaults")
        assert tc.task_type is None
        assert tc.kind == "task"
        assert tc.timeout_seconds is None
        assert tc.max_retries == 0
        assert tc.acceptance_criteria == []
        assert tc.constraints == []
        assert tc.context_refs == []
        assert tc.subtask_ids == []
        assert tc.quality_thresholds == {}
        assert tc.estimated_effort_minutes is None
        assert tc.agent_instructions is None
        assert tc.preferred_agent_type is None

    def test_enriched_create_populated(self) -> None:
        tc = TaskCreate(
            title="Feature",
            task_type="feature",
            kind="task",
            timeout_seconds=3600,
            acceptance_criteria=["it works"],
            constraints=["no breaking changes"],
            context_refs=[{"type": "file", "path": "README.md", "description": "readme"}],
            quality_thresholds={"coverage_pct": 80},
            estimated_effort_minutes=60,
            agent_instructions="Be thorough",
            preferred_agent_type="code",
        )
        assert tc.task_type == "feature"
        assert tc.timeout_seconds == 3600
        assert len(tc.acceptance_criteria) == 1
        assert tc.quality_thresholds["coverage_pct"] == 80


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

    def test_enriched_update_fields(self) -> None:
        tu = TaskUpdate(
            task_type="bugfix",
            timeout_seconds=1800,
            acceptance_criteria=["bug is fixed"],
            retry_count=2,
        )
        data = tu.model_dump(exclude_unset=True)
        assert data["task_type"] == "bugfix"
        assert data["timeout_seconds"] == 1800
        assert data["acceptance_criteria"] == ["bug is fixed"]
        assert data["retry_count"] == 2


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

    def test_enriched_filter_fields(self) -> None:
        tf = TaskFilter(
            task_type="feature",
            kind="task",
            preferred_agent_type="code",
        )
        assert tf.task_type == "feature"
        assert tf.kind == "task"
        assert tf.preferred_agent_type == "code"


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

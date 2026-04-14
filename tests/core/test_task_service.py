"""Tests for arktower.core.task_service.TaskService."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from arktower.core.event_bus import EventBus
from arktower.core.models import (
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
from arktower.core.state_machine import InvalidTransition
from arktower.core.task_service import (
    TASK_TRANSITION_EVENT,
    TaskNotFoundError,
    TaskService,
    TemplateNotFoundError,
)
from arktower.store.sqlite_repository import SqliteTaskRepository
from arktower.store.sqlite_repository import TaskNotFoundError as RepoTaskNotFoundError


@pytest.fixture()
def bus() -> EventBus:
    return EventBus()


@pytest.fixture()
def service(repo: SqliteTaskRepository, bus: EventBus) -> TaskService:
    return TaskService(repo, bus)


def _make_task(**overrides) -> Task:
    defaults = {
        "id": str(uuid.uuid4()),
        "title": "T",
        "description": "",
        "status": TaskStatus.SUBMITTED,
        "priority": TaskPriority.MEDIUM,
    }
    defaults.update(overrides)
    return Task(**defaults)


class TestCreateAndGet:
    async def test_create_task_submits_and_records_history(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        created = await service.create_task(
            TaskCreate(title="Hello", owner_id="owner-1"), actor="owner-1"
        )
        assert created.status == TaskStatus.SUBMITTED
        hist = repo.get_history(created.id)
        assert len(hist) == 1
        assert hist[0].trigger == Trigger.SUBMIT

    async def test_create_task_publishes_event(
        self, service: TaskService, repo: SqliteTaskRepository, bus: EventBus
    ) -> None:
        received: list[TaskEvent] = []

        async def capture(evt: TaskEvent) -> None:
            received.append(evt)

        bus.subscribe(TASK_TRANSITION_EVENT, capture)
        t = await service.create_task(TaskCreate(title="x"))
        assert len(received) == 1
        assert received[0].task_id == t.id

    def test_get_task_found(self, service: TaskService, repo: SqliteTaskRepository) -> None:
        t = _make_task(title="G")
        repo.create(t)
        got = service.get_task(t.id)
        assert got.id == t.id

    def test_get_task_missing_raises(self, service: TaskService) -> None:
        with pytest.raises(TaskNotFoundError):
            service.get_task("missing-id")


class TestUpdate:
    def test_update_task(self, service: TaskService, repo: SqliteTaskRepository) -> None:
        t = _make_task()
        repo.create(t)
        u = service.update_task(t.id, TaskUpdate(title="New"))
        assert u.title == "New"

    def test_update_missing_raises(
        self, service: TaskService
    ) -> None:
        with pytest.raises(RepoTaskNotFoundError):
            service.update_task("nope", TaskUpdate(title="x"))


@pytest.mark.asyncio
class TestAdvance:
    async def test_advance_enqueue(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = await service.create_task(TaskCreate(title="q"))
        out = await service.advance_task(t.id, Trigger.ENQUEUE, actor="sys")
        assert out.status == TaskStatus.QUEUED
        hist = repo.get_history(t.id)
        assert any(e.trigger == Trigger.ENQUEUE for e in hist)

    async def test_advance_invalid_raises(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.COMPLETED)
        repo.create(t)
        with pytest.raises(InvalidTransition):
            await service.advance_task(t.id, Trigger.ENQUEUE, actor="a")

    async def test_advance_claim_via_advance_rejected(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.QUEUED)
        repo.create(t)
        with pytest.raises(ValueError, match="claim_task"):
            await service.advance_task(t.id, Trigger.CLAIM, actor="a")

    async def test_cancel_from_submitted(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = await service.create_task(TaskCreate(title="c"))
        out = await service.advance_task(t.id, Trigger.CANCEL, actor="admin")
        assert out.status == TaskStatus.CANCELED

    async def test_send_review_and_approve(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.IN_PROGRESS)
        repo.create(t)
        r = await service.advance_task(t.id, Trigger.SEND_REVIEW, actor="dev")
        assert r.status == TaskStatus.REVIEW
        a = await service.advance_task(t.id, Trigger.APPROVE, actor="lead")
        assert a.status == TaskStatus.COMPLETED

    async def test_reject_review_back_to_in_progress(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.REVIEW)
        repo.create(t)
        r = await service.advance_task(t.id, Trigger.REJECT, actor="lead")
        assert r.status == TaskStatus.IN_PROGRESS

    async def test_request_input_and_resume(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.IN_PROGRESS)
        repo.create(t)
        r1 = await service.advance_task(t.id, Trigger.REQUEST_INPUT, actor="a")
        assert r1.status == TaskStatus.INPUT_REQUIRED
        r2 = await service.advance_task(t.id, Trigger.RESUME, actor="a")
        assert r2.status == TaskStatus.IN_PROGRESS

    async def test_block_and_unblock(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.IN_PROGRESS)
        repo.create(t)
        b = await service.advance_task(t.id, Trigger.BLOCK, actor="a")
        assert b.status == TaskStatus.BLOCKED
        u = await service.advance_task(t.id, Trigger.UNBLOCK, actor="a")
        assert u.status == TaskStatus.IN_PROGRESS

    async def test_reopen_completed(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.COMPLETED, completed_at=datetime.utcnow())
        repo.create(t)
        r = await service.advance_task(t.id, Trigger.REOPEN, actor="a")
        assert r.status == TaskStatus.QUEUED
        assert r.completed_at is None


@pytest.mark.asyncio
class TestClaimCompleteFail:
    async def test_claim_task(
        self, service: TaskService, repo: SqliteTaskRepository, bus: EventBus
    ) -> None:
        t = _make_task(status=TaskStatus.QUEUED)
        repo.create(t)
        events: list[TaskEvent] = []
        bus.subscribe(TASK_TRANSITION_EVENT, lambda e: events.append(e))
        c = await service.claim_task(t.id, "agent-1", agent_type="bot", actor="agent-1")
        assert c.status == TaskStatus.IN_PROGRESS
        assert c.assigned_to == "agent-1"
        assert any(e.trigger == Trigger.CLAIM for e in events)

    async def test_claim_wrong_status_raises_invalid_transition(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.SUBMITTED)
        repo.create(t)
        with pytest.raises(InvalidTransition):
            await service.claim_task(t.id, "agent-1")

    async def test_complete_task(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.IN_PROGRESS, started_at=datetime.utcnow())
        repo.create(t)
        done = await service.complete_task(
            t.id, actor="a", output="ok", notes="done"
        )
        assert done.status == TaskStatus.COMPLETED
        assert done.output == "ok"
        assert done.completed_at is not None

    async def test_fail_task(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.IN_PROGRESS)
        repo.create(t)
        f = await service.fail_task(t.id, actor="a", error="boom")
        assert f.status == TaskStatus.FAILED
        assert f.error == "boom"


class TestListAndStats:
    def test_list_tasks(self, service: TaskService, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task(title="a"))
        repo.create(_make_task(title="b"))
        rows = service.list_tasks(TaskFilter(limit=10))
        assert len(rows) >= 2

    def test_get_stats(self, service: TaskService, repo: SqliteTaskRepository) -> None:
        repo.create(_make_task())
        stats = service.get_stats()
        assert stats.total >= 1


class TestNextTask:
    def test_get_next_task_priority(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        low = _make_task(
            title="low",
            status=TaskStatus.QUEUED,
            priority=TaskPriority.LOW,
        )
        crit = _make_task(
            title="crit",
            status=TaskStatus.QUEUED,
            priority=TaskPriority.CRITICAL,
        )
        repo.create(low)
        repo.create(crit)
        nxt = service.get_next_task()
        assert nxt is not None
        assert nxt.priority == TaskPriority.CRITICAL

    def test_get_next_task_empty(self, service: TaskService) -> None:
        assert service.get_next_task() is None

    def test_get_next_task_for_agent_empty_caps_falls_back(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.QUEUED, title="fallback")
        repo.create(t)
        nxt = service.get_next_task_for_agent([])
        assert nxt is not None
        assert nxt.title == "fallback"

    def test_get_next_task_for_agent_matches_capabilities(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t1 = _make_task(
            title="needs python",
            status=TaskStatus.QUEUED,
            priority=TaskPriority.HIGH,
            capabilities=["python", "testing"],
        )
        t2 = _make_task(
            title="needs rust",
            status=TaskStatus.QUEUED,
            priority=TaskPriority.CRITICAL,
            capabilities=["rust"],
        )
        repo.create(t1)
        repo.create(t2)
        nxt = service.get_next_task_for_agent(["python", "testing", "code_review"])
        assert nxt is not None
        assert nxt.title == "needs python"

    def test_get_next_task_for_agent_no_match_returns_none(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(
            status=TaskStatus.QUEUED,
            capabilities=["rust", "wasm"],
        )
        repo.create(t)
        nxt = service.get_next_task_for_agent(["python"])
        assert nxt is None

    def test_get_next_task_for_agent_empty_task_caps_matches_any(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = _make_task(status=TaskStatus.QUEUED, title="no caps required")
        repo.create(t)
        nxt = service.get_next_task_for_agent(["python"])
        assert nxt is not None
        assert nxt.title == "no caps required"


@pytest.mark.asyncio
class TestTemplates:
    async def test_create_template(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        tpl = TaskTemplate(name="tpl-a", default_priority=TaskPriority.HIGH)
        out = service.create_template(tpl)
        assert repo.get_template(out.id) is not None

    async def test_create_from_template(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        tpl = TaskTemplate(
            name="bug",
            description="filed",
            default_tags=["bug"],
            default_labels={"area": "core"},
        )
        tpl = service.create_template(tpl)
        task = await service.create_from_template(
            tpl.id, "Fix leak", parameters={"cid": "99"}, actor="bob"
        )
        assert task.template_id == tpl.id
        assert "bug" in task.tags
        assert task.labels.get("area") == "core"
        assert task.parameters == {"cid": "99"}

    async def test_create_from_missing_template(
        self, service: TaskService
    ) -> None:
        with pytest.raises(TemplateNotFoundError):
            await service.create_from_template(str(uuid.uuid4()), "x")


@pytest.mark.asyncio
class TestHistoryIntegrity:
    async def test_each_transition_appends_event(
        self, service: TaskService, repo: SqliteTaskRepository
    ) -> None:
        t = await service.create_task(TaskCreate(title="h"))
        await service.advance_task(t.id, Trigger.ENQUEUE, actor="s")
        await service.claim_task(t.id, "worker")
        hist = repo.get_history(t.id)
        triggers = {e.trigger for e in hist}
        assert Trigger.SUBMIT in triggers
        assert Trigger.ENQUEUE in triggers
        assert Trigger.CLAIM in triggers

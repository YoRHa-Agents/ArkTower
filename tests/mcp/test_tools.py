"""Tests for MCP tool handlers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from arktower.core.event_bus import EventBus
from arktower.core.models import TaskCreate, Trigger
from arktower.core.task_service import TaskService
from arktower.mcp.tools import (
    handle_advance_task,
    handle_complete_task,
    handle_create_from_template,
    handle_create_task,
    handle_fail_task,
    handle_get_next_task,
    handle_get_pool_stats,
    handle_get_task,
    handle_list_tasks,
    handle_search_tasks,
)
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


@pytest.fixture()
def svc():
    db = DatabaseConnection(":memory:")
    db.connect()
    MigrationRunner(db, MIGRATIONS_DIR).run_migrations()
    repo = SqliteTaskRepository(db)
    bus = EventBus()
    return TaskService(repo, bus)


@pytest.mark.asyncio
async def test_create_task(svc):
    result = await handle_create_task(svc, {"title": "MCP task", "description": "Test"})
    data = json.loads(result)
    assert data["title"] == "MCP task"
    assert data["status"] == "submitted"


@pytest.mark.asyncio
async def test_list_tasks_empty(svc):
    result = await handle_list_tasks(svc, {})
    data = json.loads(result)
    assert data == []


@pytest.mark.asyncio
async def test_list_tasks_with_data(svc):
    await handle_create_task(svc, {"title": "T1"})
    await handle_create_task(svc, {"title": "T2"})
    result = await handle_list_tasks(svc, {})
    data = json.loads(result)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_task(svc):
    create_result = await handle_create_task(svc, {"title": "Get me"})
    task_id = json.loads(create_result)["id"]
    result = await handle_get_task(svc, {"task_id": task_id})
    data = json.loads(result)
    assert data["id"] == task_id
    assert data["title"] == "Get me"


@pytest.mark.asyncio
async def test_get_pool_stats(svc):
    result = await handle_get_pool_stats(svc, {})
    data = json.loads(result)
    assert "total" in data


@pytest.mark.asyncio
async def test_get_pool_stats_with_tasks(svc):
    await handle_create_task(svc, {"title": "T1"})
    result = await handle_get_pool_stats(svc, {})
    data = json.loads(result)
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_next_task_empty(svc):
    result = await handle_get_next_task(svc, {})
    data = json.loads(result)
    assert "message" in data


@pytest.mark.asyncio
async def test_search_tasks(svc):
    await handle_create_task(svc, {"title": "Authentication module"})
    await handle_create_task(svc, {"title": "Database schema"})
    result = await handle_search_tasks(svc, {"query": "Authentication"})
    data = json.loads(result)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_complete_task_flow(svc):
    create_result = await handle_create_task(svc, {"title": "Complete me"})
    task_id = json.loads(create_result)["id"]
    await svc.advance_task(task_id, Trigger.ENQUEUE)
    await svc.claim_task(task_id, "test-agent")
    result = await handle_complete_task(svc, {
        "task_id": task_id, "output": "All done", "actor": "test-agent"
    })
    data = json.loads(result)
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_advance_task_enqueue(svc):
    create_result = await handle_create_task(svc, {"title": "Advance me"})
    task_id = json.loads(create_result)["id"]
    result = await handle_advance_task(svc, {
        "task_id": task_id, "trigger": "enqueue", "actor": "sys"
    })
    data = json.loads(result)
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_fail_task_handler(svc):
    create_result = await handle_create_task(svc, {"title": "Fail me"})
    task_id = json.loads(create_result)["id"]
    await svc.advance_task(task_id, Trigger.ENQUEUE)
    await svc.claim_task(task_id, "agent-1")
    result = await handle_fail_task(svc, {
        "task_id": task_id, "error": "something broke", "actor": "agent-1"
    })
    data = json.loads(result)
    assert data["status"] == "failed"
    assert data["error"] == "something broke"


@pytest.mark.asyncio
async def test_create_from_template_handler(svc):
    from arktower.core.models import TaskTemplate, TaskPriority
    tpl = TaskTemplate(
        name="test-template",
        description="A test template",
        default_priority=TaskPriority.HIGH,
        default_tags=["templated"],
    )
    svc.create_template(tpl)
    result = await handle_create_from_template(svc, {
        "template_id": tpl.id, "title": "From template"
    })
    data = json.loads(result)
    assert data["title"] == "From template"
    assert data["priority"] == "high"
    assert "templated" in data["tags"]

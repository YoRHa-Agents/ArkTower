"""MCP tool handler implementations for ArkTower."""

from __future__ import annotations

import json
from typing import Any

from arktower.core.models import (
    TaskCreate,
    TaskFilter,
    TaskPriority,
    TaskStatus,
    TaskUpdate,
    Trigger,
)
from arktower.core.task_service import TaskService, TemplateNotFoundError


async def handle_create_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    create = TaskCreate(
        title=arguments["title"],
        description=arguments.get("description", ""),
        priority=TaskPriority(arguments.get("priority", "medium")),
        tags=arguments.get("tags", []),
    )
    task = await svc.create_task(create)
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_list_tasks(svc: TaskService, arguments: dict[str, Any]) -> str:
    filters = TaskFilter(
        status=[TaskStatus(s) for s in arguments["status"]] if "status" in arguments else None,
        priority=[TaskPriority(p) for p in arguments["priority"]] if "priority" in arguments else None,
        search=arguments.get("search"),
        limit=arguments.get("limit", 20),
    )
    tasks = svc.list_tasks(filters)
    return json.dumps(
        [t.model_dump(mode="json") for t in tasks],
        indent=2,
    )


async def handle_get_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = svc.get_task(arguments["task_id"])
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_claim_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = await svc.claim_task(arguments["task_id"], arguments["agent_id"])
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_complete_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = await svc.complete_task(
        arguments["task_id"],
        actor=arguments.get("actor", "mcp-agent"),
        output=arguments.get("output"),
    )
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_search_tasks(svc: TaskService, arguments: dict[str, Any]) -> str:
    filters = TaskFilter(search=arguments["query"], limit=arguments.get("limit", 20))
    tasks = svc.list_tasks(filters)
    return json.dumps(
        [t.model_dump(mode="json") for t in tasks],
        indent=2,
    )


async def handle_get_pool_stats(svc: TaskService, arguments: dict[str, Any]) -> str:
    stats = svc.get_stats()
    return json.dumps(stats.model_dump(mode="json"), indent=2)


async def handle_get_next_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = svc.get_next_task()
    if task is None:
        return json.dumps({"message": "No queued tasks available"})
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_advance_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = await svc.advance_task(
        arguments["task_id"],
        Trigger(arguments["trigger"]),
        actor=arguments.get("actor", "mcp-agent"),
        notes=arguments.get("notes"),
    )
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_fail_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = await svc.fail_task(
        arguments["task_id"],
        actor=arguments.get("actor", "mcp-agent"),
        error=arguments.get("error", "Task failed"),
        notes=arguments.get("notes"),
    )
    return json.dumps(task.model_dump(mode="json"), indent=2)


async def handle_archive_task(svc: TaskService, arguments: dict[str, Any]) -> str:
    from arktower.archive.archive_service import ArchiveService
    from arktower.archive.snapshot_writer import SnapshotWriter

    archive_dir = arguments.get("archive_dir", "archives")
    writer = SnapshotWriter(archive_dir)
    archive_svc = ArchiveService(svc._repo, writer)
    path = archive_svc.archive_task(arguments["task_id"])
    return json.dumps({"task_id": arguments["task_id"], "path": str(path)})


async def handle_create_from_template(svc: TaskService, arguments: dict[str, Any]) -> str:
    task = await svc.create_from_template(
        arguments["template_id"],
        arguments["title"],
        description=arguments.get("description"),
        parameters=arguments.get("parameters"),
        actor=arguments.get("actor", "mcp-agent"),
    )
    return json.dumps(task.model_dump(mode="json"), indent=2)


TOOL_HANDLERS: dict[str, Any] = {
    "create_task": handle_create_task,
    "list_tasks": handle_list_tasks,
    "get_task": handle_get_task,
    "claim_task": handle_claim_task,
    "complete_task": handle_complete_task,
    "search_tasks": handle_search_tasks,
    "get_pool_stats": handle_get_pool_stats,
    "get_next_task": handle_get_next_task,
    "advance_task": handle_advance_task,
    "fail_task": handle_fail_task,
    "archive_task": handle_archive_task,
    "create_from_template": handle_create_from_template,
}

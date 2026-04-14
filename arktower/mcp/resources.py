"""MCP resource providers for ArkTower."""

from __future__ import annotations

import json

from arktower.core.task_service import TaskService


async def read_pool_stats(svc: TaskService) -> str:
    stats = svc.get_stats()
    return json.dumps(stats.model_dump(mode="json"), indent=2)


async def read_task(svc: TaskService, task_id: str) -> str:
    task = svc.get_task(task_id)
    history = svc.get_task_history(task_id)
    return json.dumps(
        {
            "task": task.model_dump(mode="json"),
            "history": [e.model_dump(mode="json") for e in history],
        },
        indent=2,
    )

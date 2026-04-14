"""CLI output formatting (Rich tables and JSON)."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

from rich.console import Console
from rich.table import Table

from arktower.core.models import PoolStats, Task


def format_task_table(tasks: list[Task]) -> str:
    """Render *tasks* as a Rich table string."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", overflow="fold")
    table.add_column("Title", overflow="fold")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Tags", overflow="fold")
    table.add_column("Created")

    for t in tasks:
        tags = ", ".join(t.tags) if t.tags else ""
        created = t.created_at.isoformat() if t.created_at else ""
        table.add_row(
            t.id,
            t.title,
            t.status.value,
            t.priority.value,
            tags,
            created,
        )

    buf = StringIO()
    console = Console(file=buf, width=120, soft_wrap=True)
    console.print(table)
    return buf.getvalue()


def format_task_detail(task: Task) -> str:
    """Render a single *task* with all fields (human-readable lines)."""
    lines = [
        f"id: {task.id}",
        f"title: {task.title}",
        f"description: {task.description}",
        f"status: {task.status.value}",
        f"priority: {task.priority.value}",
        f"parent_id: {task.parent_id}",
        f"context_id: {task.context_id}",
        f"owner_id: {task.owner_id}",
        f"assigned_to: {task.assigned_to}",
        f"assigned_type: {task.assigned_type}",
        f"parameters: {json.dumps(task.parameters, sort_keys=True)}",
        f"output: {task.output}",
        f"error: {task.error}",
        f"tags: {task.tags}",
        f"labels: {dict(task.labels)}",
        f"template_id: {task.template_id}",
        f"max_steps: {task.max_steps}",
        f"version: {task.version}",
        f"created_at: {task.created_at.isoformat() if task.created_at else None}",
        f"updated_at: {task.updated_at.isoformat() if task.updated_at else None}",
        f"started_at: {task.started_at.isoformat() if task.started_at else None}",
        f"completed_at: {task.completed_at.isoformat() if task.completed_at else None}",
    ]
    return "\n".join(lines) + "\n"


def format_stats(stats: PoolStats) -> str:
    """Render pool statistics."""
    lines = [
        f"total: {stats.total}",
        "by_status:",
    ]
    for k in sorted(stats.by_status):
        lines.append(f"  {k}: {stats.by_status[k]}")
    lines.append("by_priority:")
    for k in sorted(stats.by_priority):
        lines.append(f"  {k}: {stats.by_priority[k]}")
    lines.append(f"oldest_queued_age_seconds: {stats.oldest_queued_age_seconds}")
    lines.append(f"avg_completion_seconds: {stats.avg_completion_seconds}")
    return "\n".join(lines) + "\n"


def format_json(data: Any) -> str:
    """Pretty-print JSON (supports Pydantic models via model_dump)."""
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        payload = [x.model_dump(mode="json") for x in data]
    else:
        payload = data
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

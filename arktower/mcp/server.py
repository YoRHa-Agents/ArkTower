"""MCP server setup for ArkTower task pool."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

from arktower.core.event_bus import EventBus
from arktower.core.task_service import TaskNotFoundError, TaskService
from arktower.mcp.prompts import ANALYZE_TASK_PROMPT, CREATE_TASK_PROMPT
from arktower.mcp.resources import read_pool_stats, read_task
from arktower.mcp.tools import TOOL_HANDLERS
from arktower.store.connection import DatabaseConnection
from arktower.store.migration import MigrationRunner
from arktower.store.sqlite_repository import SqliteTaskRepository

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "create_task",
        "description": "Create a new task in the ArkTower task pool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Detailed task description"},
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Task priority",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task tags for categorization",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks in the pool with optional filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by status values",
                },
                "priority": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by priority values",
                },
                "search": {"type": "string", "description": "Full-text search query"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "get_task",
        "description": "Get full details of a specific task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "claim_task",
        "description": "Claim a queued task for an agent to work on",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to claim"},
                "agent_id": {"type": "string", "description": "ID of the claiming agent"},
            },
            "required": ["task_id", "agent_id"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed with optional output",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to complete"},
                "output": {"type": "string", "description": "Task output/result"},
                "actor": {"type": "string", "description": "Who is completing the task"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "search_tasks",
        "description": "Full-text search across task titles and descriptions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_pool_stats",
        "description": "Get pool statistics (counts by status, priority, etc.)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_next_task",
        "description": "Get the highest-priority queued task ready for claiming",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "advance_task",
        "description": "Advance a task through a state-machine trigger (enqueue, send_review, approve, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to advance"},
                "trigger": {
                    "type": "string",
                    "enum": [
                        "submit", "enqueue", "request_input", "resume",
                        "block", "unblock", "send_review", "approve",
                        "reject", "complete", "fail", "cancel", "timeout", "reopen",
                    ],
                    "description": "State-machine trigger name",
                },
                "actor": {"type": "string", "description": "Who is performing the action"},
                "notes": {"type": "string", "description": "Optional notes for audit trail"},
            },
            "required": ["task_id", "trigger"],
        },
    },
    {
        "name": "fail_task",
        "description": "Mark a task as failed with an error message",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to fail"},
                "error": {"type": "string", "description": "Error description"},
                "actor": {"type": "string", "description": "Who is reporting the failure"},
                "notes": {"type": "string", "description": "Optional notes"},
            },
            "required": ["task_id", "error"],
        },
    },
    {
        "name": "archive_task",
        "description": "Archive a completed/failed/canceled task to a JSON snapshot and remove from pool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to archive"},
                "archive_dir": {
                    "type": "string",
                    "description": "Archive directory (default: archives)",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "create_from_template",
        "description": "Create a new task from an existing template",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template_id": {"type": "string", "description": "Template ID to use"},
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Optional description override"},
                "parameters": {
                    "type": "object",
                    "description": "Parameters to merge with template defaults",
                },
                "actor": {"type": "string", "description": "Who is creating the task"},
            },
            "required": ["template_id", "title"],
        },
    },
]


def create_mcp_server(db_path: str = "arktower.db") -> Server:
    """Create and configure the ArkTower MCP server."""
    server = Server("arktower")

    db = DatabaseConnection(db_path)
    db.connect()
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations"
    if migrations_dir.is_dir():
        MigrationRunner(db, migrations_dir).run_migrations()
    repo = SqliteTaskRepository(db)
    bus = EventBus()
    svc = TaskService(repo, bus)

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [Tool(**td) for td in TOOL_DEFINITIONS]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        arguments = arguments or {}
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = await handler(svc, arguments)
            return [TextContent(type="text", text=result)]
        except TaskNotFoundError as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]
        except Exception as exc:
            logger.error("Tool %s failed: %s", name, exc, exc_info=True)
            return [TextContent(type="text", text=f"Error: {exc}")]

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        return [
            Resource(
                uri="arktower://pool/stats",
                name="Pool Statistics",
                description="Current task pool statistics",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        parsed = urlparse(str(uri))
        path = parsed.netloc + parsed.path if parsed.netloc else parsed.path

        if path == "pool/stats":
            return await read_pool_stats(svc)

        if path.startswith("tasks/"):
            task_id = path.split("/", 1)[1]
            return await read_task(svc, task_id)

        raise ValueError(f"Unknown resource: {uri}")

    @server.list_prompts()
    async def handle_list_prompts() -> list[dict]:
        return [
            {
                "name": "create-task",
                "description": "Guided task creation prompt",
            },
            {
                "name": "analyze-task",
                "description": "Task analysis prompt",
                "arguments": [
                    {
                        "name": "task_id",
                        "description": "ID of the task to analyze",
                        "required": True,
                    }
                ],
            },
        ]

    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        if name == "create-task":
            return GetPromptResult(
                description="Guided task creation",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=CREATE_TASK_PROMPT),
                    )
                ],
            )
        if name == "analyze-task":
            task_id = (arguments or {}).get("task_id", "<task_id>")
            return GetPromptResult(
                description="Task analysis",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=ANALYZE_TASK_PROMPT.format(task_id=task_id),
                        ),
                    )
                ],
            )
        raise ValueError(f"Unknown prompt: {name}")

    return server


async def run_stdio() -> None:
    """Run the MCP server over stdio transport."""
    server = create_mcp_server()
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


def main() -> None:
    """Entry point for running the MCP server."""
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()

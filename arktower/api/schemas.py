"""Pydantic models for HTTP request and response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from arktower.core.models import (
    PoolStats,
    Task,
    TaskCreate,
    TaskPriority,
    TaskStatus,
    TaskTemplate,
    TaskUpdate,
    Trigger,
)


class TaskCreateRequest(TaskCreate):
    """Body for creating a task via the REST API."""

    model_config = ConfigDict(extra="forbid")


class TaskUpdateRequest(TaskUpdate):
    """Body for patching a task."""

    model_config = ConfigDict(extra="forbid")


class TaskAdvanceRequest(BaseModel):
    """Body for advancing task state with a named trigger."""

    trigger: Trigger
    actor: str = "system"
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class TaskClaimRequest(BaseModel):
    """Body for claiming a queued task."""

    agent_id: str
    agent_type: str | None = None
    actor: str | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class TaskCompleteRequest(BaseModel):
    """Body for completing a task."""

    actor: str
    output: str | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class TaskResponse(Task):
    """API representation of a task (same shape as the domain model)."""

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Paginated task list."""

    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskEventResponse(BaseModel):
    """Single audit event in task history."""

    event_id: str
    task_id: str
    trigger: Trigger
    from_status: TaskStatus
    to_status: TaskStatus
    actor: str
    notes: str | None = None
    timestamp: datetime


class TaskHistoryResponse(BaseModel):
    """Task transition history."""

    task_id: str
    events: list[TaskEventResponse]


class PoolStatsResponse(PoolStats):
    """Pool statistics for the dashboard / API."""

    model_config = ConfigDict(from_attributes=True)


class NextTaskResponse(BaseModel):
    """Next queued task candidate, if any."""

    task: TaskResponse | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str
    detail: str | None = None


class TemplateCreateRequest(BaseModel):
    """Body for creating a task template."""

    name: str
    description: str = ""
    default_priority: TaskPriority = TaskPriority.MEDIUM
    default_tags: list[str] = Field(default_factory=list)
    default_labels: dict[str, str] = Field(default_factory=dict)
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    checklist: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class TemplateResponse(TaskTemplate):
    """Stored template returned by the API."""

    model_config = ConfigDict(from_attributes=True)


class ArchiveTaskResponse(BaseModel):
    """Result of archiving a terminal task."""

    task_id: str
    path: str

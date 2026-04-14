"""REST API routes and FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request, WebSocket, status
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect

from arktower.api.dependencies import get_archive_service, get_repository, get_task_service
from arktower.api.schemas import (
    ArchiveTaskResponse,
    ErrorResponse,
    NextTaskResponse,
    PoolStatsResponse,
    TaskAdvanceRequest,
    TaskClaimRequest,
    TaskCompleteRequest,
    TaskCreateRequest,
    TaskEventResponse,
    TaskHistoryResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdateRequest,
    TemplateCreateRequest,
    TemplateResponse,
)
from arktower.api.ws_manager import ConnectionManager
from arktower.archive.archive_service import ArchiveError, ArchiveService
from arktower.core.event_bus import EventBus
from arktower.core.models import (
    Task,
    TaskFilter,
    TaskPriority,
    TaskStatus,
    TaskTemplate,
    TaskUpdate,
)
from arktower.core.state_machine import InvalidTransition
from arktower.core.task_service import TaskNotFoundError, TaskService
from arktower.store.sqlite_repository import ClaimFailedError, SqliteTaskRepository
from arktower.store.sqlite_repository import TaskNotFoundError as RepoTaskNotFound

router = APIRouter(prefix="/api/v1")

_VERSION = "0.1.0"


@router.get("/health")
async def health_check(
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
) -> dict:
    db_ok = False
    try:
        repo._conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception:
        pass
    return {"status": "ok" if db_ok else "degraded", "version": _VERSION, "db_ok": db_ok}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.event_bus = EventBus()
    app.state.ws_manager = ConnectionManager(app.state.event_bus)
    yield
    app.state.event_bus.clear()


def create_app() -> FastAPI:
    app = FastAPI(title="ArkTower API", lifespan=_lifespan)
    app.include_router(router)

    @app.exception_handler(TaskNotFoundError)
    async def _not_found_service(_request: Request, exc: TaskNotFoundError) -> JSONResponse:
        body = ErrorResponse(error="not_found", detail=str(exc)).model_dump()
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=body)

    @app.exception_handler(RepoTaskNotFound)
    async def _not_found_repo(_request: Request, exc: RepoTaskNotFound) -> JSONResponse:
        body = ErrorResponse(error="not_found", detail=str(exc)).model_dump()
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=body)

    @app.exception_handler(InvalidTransition)
    async def _invalid_transition(_request: Request, exc: InvalidTransition) -> JSONResponse:
        body = ErrorResponse(error="invalid_transition", detail=str(exc)).model_dump()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @app.exception_handler(ClaimFailedError)
    async def _claim_failed(_request: Request, exc: ClaimFailedError) -> JSONResponse:
        body = ErrorResponse(error="claim_failed", detail=str(exc)).model_dump()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body)

    @app.exception_handler(ArchiveError)
    async def _archive_error(_request: Request, exc: ArchiveError) -> JSONResponse:
        body = ErrorResponse(error="archive_error", detail=str(exc)).model_dump()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError) -> JSONResponse:
        body = ErrorResponse(error="bad_request", detail=str(exc)).model_dump()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body)

    @app.websocket("/ws")
    async def task_events_ws(websocket: WebSocket) -> None:
        manager: ConnectionManager = websocket.app.state.ws_manager
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(websocket)

    return app


def _task_to_response(task) -> TaskResponse:
    return TaskResponse.model_validate(task)


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreateRequest,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    return await service.create_task(body, actor=body.owner_id)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
    status_q: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    priority: Annotated[list[TaskPriority] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    filters = TaskFilter(
        status=status_q,
        priority=priority,
        tags=tags,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = repo.count(filters)
    tasks = service.list_tasks(filters)
    return TaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    return service.get_task(task_id)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    body: TaskUpdateRequest,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    return service.update_task(task_id, TaskUpdate(**body.model_dump(exclude_unset=True)))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
) -> None:
    deleted = repo.delete(task_id)
    if not deleted:
        raise RepoTaskNotFound(task_id)


@router.post("/tasks/{task_id}/advance", response_model=TaskResponse)
async def advance_task(
    task_id: str,
    body: TaskAdvanceRequest,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    return await service.advance_task(
        task_id,
        body.trigger,
        actor=body.actor,
        notes=body.notes,
    )


@router.post("/tasks/{task_id}/claim", response_model=TaskResponse)
async def claim_task(
    task_id: str,
    body: TaskClaimRequest,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    return await service.claim_task(
        task_id,
        body.agent_id,
        agent_type=body.agent_type,
        actor=body.actor,
        notes=body.notes,
    )


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    body: TaskCompleteRequest,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> Task:
    return await service.complete_task(
        task_id,
        actor=body.actor,
        output=body.output,
        notes=body.notes,
    )


@router.get("/tasks/{task_id}/history", response_model=TaskHistoryResponse)
async def get_task_history(
    task_id: str,
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
) -> TaskHistoryResponse:
    if repo.get(task_id) is None:
        raise RepoTaskNotFound(task_id)
    events = repo.get_history(task_id)
    return TaskHistoryResponse(
        task_id=task_id,
        events=[
            TaskEventResponse(
                event_id=e.event_id,
                task_id=e.task_id,
                trigger=e.trigger,
                from_status=e.from_status,
                to_status=e.to_status,
                actor=e.actor,
                notes=e.notes,
                timestamp=e.timestamp,
            )
            for e in events
        ],
    )


@router.get("/pool/stats", response_model=PoolStatsResponse)
async def pool_stats(
    service: Annotated[TaskService, Depends(get_task_service)],
) -> PoolStatsResponse:
    return PoolStatsResponse.model_validate(service.get_stats())


@router.get("/pool/next", response_model=NextTaskResponse)
async def pool_next(
    service: Annotated[TaskService, Depends(get_task_service)],
) -> NextTaskResponse:
    nxt = service.get_next_task()
    return NextTaskResponse(task=_task_to_response(nxt) if nxt is not None else None)


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreateRequest,
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
) -> TaskTemplate:
    template = TaskTemplate(**body.model_dump())
    return repo.create_template(template)


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    repo: Annotated[SqliteTaskRepository, Depends(get_repository)],
) -> list[TaskTemplate]:
    return repo.list_templates()


@router.post("/archives/{task_id}", response_model=ArchiveTaskResponse)
async def archive_task_endpoint(
    task_id: str,
    archive: Annotated[ArchiveService, Depends(get_archive_service)],
) -> ArchiveTaskResponse:
    path = archive.archive_task(task_id)
    return ArchiveTaskResponse(task_id=task_id, path=str(path))


"""WebSocket fan-out for task lifecycle events."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from arktower.core.event_bus import EventBus
from arktower.core.models import TaskEvent
from arktower.core.task_service import TASK_TRANSITION_EVENT

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks WebSocket clients and forwards :data:`TASK_TRANSITION_EVENT` payloads."""

    def __init__(self, event_bus: EventBus) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        event_bus.subscribe(TASK_TRANSITION_EVENT, self._on_task_transition)

    async def _on_task_transition(self, event: Any) -> None:
        if isinstance(event, TaskEvent):
            payload = {
                "type": TASK_TRANSITION_EVENT,
                "event": event.model_dump(mode="json"),
            }
        else:
            payload = {"type": TASK_TRANSITION_EVENT, "event": event}
        await self.broadcast_json(payload)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        """Send JSON to every connected client; broken sockets are dropped."""
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                logger.exception("WebSocket send failed; disconnecting client")
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

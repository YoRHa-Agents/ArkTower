"""Tests for arktower.core.event_bus — sync and async pub/sub."""

from __future__ import annotations

import asyncio

import pytest

from arktower.core.event_bus import EventBus


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


class TestSubscribePublish:
    async def test_sync_handler_called(self, bus: EventBus) -> None:
        received: list[str] = []
        bus.subscribe("test.event", lambda data: received.append(data))
        await bus.publish("test.event", "payload")
        assert received == ["payload"]

    async def test_async_handler_called(self, bus: EventBus) -> None:
        received: list[str] = []

        async def handler(data: str) -> None:
            received.append(data)

        bus.subscribe("test.event", handler)
        await bus.publish("test.event", "async_payload")
        assert received == ["async_payload"]

    async def test_multiple_handlers(self, bus: EventBus) -> None:
        results: list[int] = []
        bus.subscribe("multi", lambda d: results.append(1))
        bus.subscribe("multi", lambda d: results.append(2))
        await bus.publish("multi", None)
        assert results == [1, 2]

    async def test_mixed_sync_async_handlers(self, bus: EventBus) -> None:
        order: list[str] = []

        def sync_handler(data: str) -> None:
            order.append("sync")

        async def async_handler(data: str) -> None:
            order.append("async")

        bus.subscribe("mixed", sync_handler)
        bus.subscribe("mixed", async_handler)
        await bus.publish("mixed", "data")
        assert order == ["sync", "async"]

    async def test_no_cross_talk_between_event_types(self, bus: EventBus) -> None:
        a_received: list[str] = []
        b_received: list[str] = []
        bus.subscribe("a", lambda d: a_received.append(d))
        bus.subscribe("b", lambda d: b_received.append(d))
        await bus.publish("a", "only_a")
        assert a_received == ["only_a"]
        assert b_received == []

    async def test_publish_to_nonexistent_event_type(self, bus: EventBus) -> None:
        await bus.publish("nobody.listening", "data")


class TestUnsubscribe:
    async def test_unsubscribe_removes_handler(self, bus: EventBus) -> None:
        received: list[str] = []
        handler = lambda d: received.append(d)  # noqa: E731
        bus.subscribe("evt", handler)
        bus.unsubscribe("evt", handler)
        await bus.publish("evt", "ignored")
        assert received == []

    async def test_unsubscribe_nonexistent_is_silent(self, bus: EventBus) -> None:
        bus.unsubscribe("evt", lambda d: None)

    async def test_unsubscribe_only_target_handler(self, bus: EventBus) -> None:
        results: list[str] = []
        keep = lambda d: results.append("kept")  # noqa: E731
        remove = lambda d: results.append("removed")  # noqa: E731
        bus.subscribe("evt", keep)
        bus.subscribe("evt", remove)
        bus.unsubscribe("evt", remove)
        await bus.publish("evt", None)
        assert results == ["kept"]


class TestClear:
    async def test_clear_removes_all(self, bus: EventBus) -> None:
        received: list[str] = []
        bus.subscribe("a", lambda d: received.append("a"))
        bus.subscribe("b", lambda d: received.append("b"))
        bus.clear()
        await bus.publish("a", None)
        await bus.publish("b", None)
        assert received == []


class TestDuplicateSubscription:
    async def test_same_handler_not_added_twice(self, bus: EventBus) -> None:
        count: list[int] = []
        handler = lambda d: count.append(1)  # noqa: E731
        bus.subscribe("evt", handler)
        bus.subscribe("evt", handler)
        await bus.publish("evt", None)
        assert len(count) == 1


class TestErrorHandling:
    async def test_failing_handler_does_not_block_others(self, bus: EventBus) -> None:
        results: list[str] = []

        def bad_handler(data: str) -> None:
            raise RuntimeError("boom")

        bus.subscribe("evt", bad_handler)
        bus.subscribe("evt", lambda d: results.append("ok"))
        await bus.publish("evt", "data")
        assert results == ["ok"]

    async def test_failing_async_handler_does_not_block_others(self, bus: EventBus) -> None:
        results: list[str] = []

        async def bad_handler(data: str) -> None:
            raise RuntimeError("async boom")

        bus.subscribe("evt", bad_handler)
        bus.subscribe("evt", lambda d: results.append("ok"))
        await bus.publish("evt", "data")
        assert results == ["ok"]

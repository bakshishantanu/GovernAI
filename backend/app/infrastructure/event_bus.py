from __future__ import annotations
"""In-process async event bus for SSE streaming (FRD-12).

Uses asyncio.Queue per subscriber. Services publish events; the SSE endpoint
(P1) subscribes and streams them to the frontend.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Event:
    """A single event emitted by any service."""

    id: UUID
    type: str  # e.g. "agent.created", "tool_call.allowed", "cost.recorded"
    timestamp: datetime
    payload: dict[str, Any]

    @classmethod
    def create(cls, event_type: str, payload: dict[str, Any]) -> "Event":
        return cls(
            id=uuid4(),
            type=event_type,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
        )


class EventBus:
    """Simple pub/sub built on asyncio.Queue.

    Usage:
        bus = EventBus()

        # Publisher (any service):
        await bus.publish(Event.create("agent.created", {"agent_id": "..."}))

        # Subscriber (SSE endpoint):
        async for event in bus.subscribe():
            yield format_sse(event)
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event]] = []

    async def publish(self, event: Event) -> None:
        """Send an event to all current subscribers."""
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop events for slow consumers rather than blocking publishers
                pass

    def subscribe(self, maxsize: int = 256) -> "Subscription":
        """Create a new subscription. Use as an async iterator."""
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(queue)
        return Subscription(queue, self._subscribers)


class Subscription:
    """Async iterator that yields events. Cleans up on exit."""

    def __init__(
        self,
        queue: asyncio.Queue[Event],
        subscriber_list: list[asyncio.Queue[Event]],
    ) -> None:
        self._queue = queue
        self._subscriber_list = subscriber_list

    def __aiter__(self):
        return self

    async def __anext__(self) -> Event:
        return await self._queue.get()

    async def __aexit__(self, *_):
        """Remove this subscriber when the SSE connection closes."""
        if self._queue in self._subscriber_list:
            self._subscriber_list.remove(self._queue)


# Global singleton — imported by services and the SSE endpoint.
event_bus = EventBus()

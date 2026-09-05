"""Server-Sent Events plumbing shared by the streaming endpoints.

One place for the wire format and the subscribe/heartbeat/cleanup loop, so
`/executions/{id}/stream` and `/events/stream` cannot drift apart.

Why a heartbeat: an idle SSE connection looks dead to proxies and load
balancers, which close it after 30–60s. A comment frame every few seconds keeps
it open and costs nothing. It also gives the loop a regular chance to re-check
anything that is not itself published as an event.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Awaitable, Callable, Iterable

from app.infrastructure.event_bus import Event, event_bus

#: Seconds between keep-alive frames when no event has arrived.
HEARTBEAT_SECONDS = 10.0

#: Headers that stop a proxy buffering the stream and serving it as one blob.
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def format_sse(event_type: str, data: Any) -> str:
    """Render one SSE frame. `data` is JSON-encoded on a single line."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


def format_comment(text: str = "keep-alive") -> str:
    """A comment frame. Clients ignore it; proxies see traffic."""
    return f": {text}\n\n"


#: What a heartbeat callback returns: an optional frame to send, and whether
#: the stream should carry on afterwards.
HeartbeatResult = tuple[str | None, bool]


async def stream(
    *,
    initial: Iterable[str] = (),
    matches: Callable[[Event], bool],
    render: Callable[[Event], str],
    on_heartbeat: Callable[[], Awaitable[HeartbeatResult]] | None = None,
) -> AsyncGenerator[str, None]:
    """Subscribe to the bus and yield SSE frames until finished or disconnected.

    - `initial`   frames sent once, before any live event, so a client that
                  joins late is not staring at a blank screen.
    - `matches`   decides whether an event belongs on this stream. Anything
                  that cannot be positively matched is dropped, never guessed.
    - `render`    turns a matched event into a frame.
    - `on_heartbeat` runs on every quiet tick and returns
                  `(frame_or_None, keep_going)`. It exists to notice state that
                  no service publishes as an event — a finished run, say — and
                  to close the stream when there will never be another event.

    The subscription is always removed on exit — including when Starlette
    throws into this generator because the client went away. Without that the
    bus keeps a queue per dead connection and every publish grows more
    expensive.
    """
    for frame in initial:
        yield frame

    subscription = event_bus.subscribe()
    try:
        while True:
            try:
                event = await asyncio.wait_for(
                    subscription.__anext__(), timeout=HEARTBEAT_SECONDS
                )
            except asyncio.TimeoutError:
                if on_heartbeat is None:
                    yield format_comment()
                    continue

                frame, keep_going = await on_heartbeat()
                yield frame if frame is not None else format_comment()
                if not keep_going:
                    return
                continue

            if matches(event):
                yield render(event)
    finally:
        # `Subscription` has no __aenter__, so it cannot be used with
        # `async with`; calling its cleanup directly is the supported path.
        await subscription.__aexit__()

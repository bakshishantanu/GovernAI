import asyncio
import json

import pytest

from app.api import sse
from app.infrastructure.event_bus import Event, event_bus


@pytest.fixture(autouse=True)
def fast_heartbeat(monkeypatch):
    """Keep the tests quick without changing the behaviour under test."""
    monkeypatch.setattr(sse, "HEARTBEAT_SECONDS", 0.02)


@pytest.fixture(autouse=True)
def clean_bus():
    """The bus is a module-level singleton, so leaked subscribers cross tests."""
    event_bus._subscribers.clear()
    yield
    event_bus._subscribers.clear()


def parse(frame: str) -> tuple[str, dict]:
    lines = frame.strip().splitlines()
    event_type = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event_type, data


async def collect(generator, count: int, timeout: float = 2.0) -> list[str]:
    """Pull `count` frames, failing loudly rather than hanging forever."""
    frames = []
    for _ in range(count):
        frames.append(await asyncio.wait_for(generator.__anext__(), timeout=timeout))
    return frames


def test_format_sse_is_one_frame_with_a_blank_line_terminator():
    frame = sse.format_sse("audit.tool.denied", {"tool": "run_sql_query"})

    assert frame.startswith("event: audit.tool.denied\n")
    assert frame.endswith("\n\n")
    assert "\n" not in frame[len("event: audit.tool.denied\ndata: ") : -2]


@pytest.mark.asyncio
async def test_initial_frames_are_sent_before_any_event():
    gen = sse.stream(
        initial=[sse.format_sse("status", {"status": "RUNNING"})],
        matches=lambda e: True,
        render=lambda e: sse.format_sse(e.type, e.payload),
    )

    (first,) = await collect(gen, 1)
    assert parse(first) == ("status", {"status": "RUNNING"})

    await gen.aclose()


@pytest.mark.asyncio
async def test_only_matching_events_are_forwarded():
    gen = sse.stream(
        initial=(),
        matches=lambda e: e.payload.get("execution_id") == "run-1",
        render=lambda e: sse.format_sse(e.type, e.payload),
    )

    consumer = asyncio.create_task(collect(gen, 1))
    await asyncio.sleep(0.01)  # let the generator subscribe

    await event_bus.publish(Event.create("audit.tool.denied", {"execution_id": "run-2"}))
    await event_bus.publish(Event.create("audit.tool.denied", {"execution_id": "run-1"}))

    (frame,) = await asyncio.wait_for(consumer, timeout=2.0)
    event_type, data = parse(frame)

    assert event_type == "audit.tool.denied"
    assert data["execution_id"] == "run-1"  # the other run never appears

    await gen.aclose()


@pytest.mark.asyncio
async def test_event_without_the_id_is_dropped_not_guessed():
    gen = sse.stream(
        initial=(),
        matches=lambda e: e.payload.get("execution_id") == "run-1",
        render=lambda e: sse.format_sse(e.type, e.payload),
        on_heartbeat=lambda: _heartbeat(None, True),
    )

    consumer = asyncio.create_task(collect(gen, 1))
    await asyncio.sleep(0.01)

    await event_bus.publish(Event.create("audit.tool.allowed", {"tool": "no_id_here"}))

    # The only frame that arrives is the keep-alive, never the unmatched event.
    (frame,) = await asyncio.wait_for(consumer, timeout=2.0)
    assert frame.startswith(":")

    await gen.aclose()


@pytest.mark.asyncio
async def test_heartbeat_can_close_the_stream():
    """A finished run must end the stream, not repeat 'done' forever."""

    async def on_heartbeat():
        return sse.format_sse("done", {"status": "COMPLETED"}), False

    gen = sse.stream(
        initial=(),
        matches=lambda e: False,
        render=lambda e: "",
        on_heartbeat=on_heartbeat,
    )

    frames = [frame async for frame in gen]

    assert len(frames) == 1
    assert parse(frames[0]) == ("done", {"status": "COMPLETED"})


@pytest.mark.asyncio
async def test_subscription_is_removed_when_the_client_goes_away():
    """Without cleanup the bus keeps a queue per dead connection forever."""
    gen = sse.stream(
        initial=(),
        matches=lambda e: True,
        render=lambda e: sse.format_sse(e.type, e.payload),
    )

    consumer = asyncio.create_task(collect(gen, 1))
    await asyncio.sleep(0.01)
    assert len(event_bus._subscribers) == 1

    consumer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer  # let the cancellation actually land in the generator

    await gen.aclose()  # what Starlette does when the client disconnects

    assert event_bus._subscribers == []


async def _heartbeat(frame, keep_going):
    return frame, keep_going

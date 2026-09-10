"""Regression tests for GET /executions/{id}/stream's already-finished path.

A run that completes fast (the mock LLM provider often does, well under a
second) can already be terminal by the time a client opens this stream. The
route must send the real result immediately rather than making the client
wait out a heartbeat that would otherwise be the only thing carrying it -
found live, 2026-09-09: the console showed "No result was recorded" for a
run that had actually completed seconds earlier.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.schemas.auth import CurrentUser
from app.api.v1.executions import stream_execution_events
from app.domain.executions.models import Execution


@pytest.fixture
def current_user():
    return CurrentUser(id=uuid.uuid4(), org_id=uuid.uuid4(), role="agent_builder")


def make_execution(current_user, **overrides) -> Execution:
    defaults = dict(
        id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        org_id=current_user.org_id,
        goal="Resolve ticket #123",
        status="COMPLETED",
        result="Execution simulated successfully",
        error=None,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Execution(**defaults)


async def collect_frames(response) -> list[tuple[str, dict]]:
    frames = []
    async for chunk in response.body_iterator:
        text = chunk.decode() if isinstance(chunk, bytes) else chunk
        lines = text.strip().splitlines()
        event_type = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        frames.append((event_type, data))
    return frames


@pytest.mark.asyncio
async def test_already_completed_run_sends_the_real_result_immediately(current_user):
    """The bug, reproduced: without the fix this never sends `result` here at
    all - only a bare "status" frame, leaving a client to wait out a whole
    heartbeat interval for a "done" frame it might never think to expect."""
    execution = make_execution(current_user)
    exec_service = AsyncMock()
    exec_service.get_execution.return_value = execution

    response = await stream_execution_events(
        execution_id=execution.id,
        current_user=current_user,
        exec_service=exec_service,
    )
    frames = await collect_frames(response)

    event_types = [t for t, _ in frames]
    assert "done" in event_types, (
        "a finished run must carry its result without waiting on a heartbeat"
    )

    done_data = dict(frames)["done"]
    assert done_data["result"] == "Execution simulated successfully"
    assert done_data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_failed_run_sends_its_error_immediately_too(current_user):
    execution = make_execution(
        current_user, status="FAILED", result=None, error="The tool call was denied"
    )
    exec_service = AsyncMock()
    exec_service.get_execution.return_value = execution

    response = await stream_execution_events(
        execution_id=execution.id,
        current_user=current_user,
        exec_service=exec_service,
    )
    frames = await collect_frames(response)
    done_data = dict(frames)["done"]

    assert done_data["status"] == "FAILED"
    assert done_data["error"] == "The tool call was denied"


@pytest.mark.asyncio
async def test_still_running_execution_gets_no_done_frame_up_front(current_user):
    """A live run must not be told it's finished before it actually is."""
    execution = make_execution(current_user, status="RUNNING", result=None, completed_at=None)
    exec_service = AsyncMock()
    exec_service.get_execution.return_value = execution

    response = await stream_execution_events(
        execution_id=execution.id,
        current_user=current_user,
        exec_service=exec_service,
    )

    # Only the initial "status" frame should be queued up; the generator then
    # blocks waiting on the event bus / heartbeat, which this test does not
    # drive. Pulling exactly one frame proves no premature "done" was sent.
    agen = response.body_iterator
    first_chunk = await agen.__anext__()
    text = first_chunk.decode() if isinstance(first_chunk, bytes) else first_chunk
    assert text.startswith("event: status")
    assert "done" not in text

    await agen.aclose()

"""A live event and the same event re-read from the timeline must be
recognisable as one thing.

The console builds one timeline from two sources: `GET
/executions/{id}/timeline` (the persisted rows) and the SSE stream (live).
It de-duplicates them by id. `stream_execution_events` renders a frame as
`{"id": str(event.id), "at": ..., **event.payload}`, so the *bus* event's
uuid4 is what reaches the client unless the payload carries an `id` of its
own -- and that uuid is minted fresh at publish time, matching nothing in
the database.

Found live: a run that made one governed tool call showed it twice, or not
at all depending on which source landed last, because the two sources were
using disjoint id spaces and neither could see the other's events.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import app.domain.agents.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
from app.domain.audit.service import AuditService
from app.domain.costs.service import CostService

ORG, AGENT, EXECUTION = uuid4(), uuid4(), uuid4()


async def test_tool_call_event_is_published_with_its_persisted_row_id():
    repo, bus = AsyncMock(), AsyncMock()
    service = AuditService(repo, bus)

    await service.log_tool_call(ORG, AGENT, EXECUTION, "audit_website", True, "All policies passed")

    recorded = repo.record_event.await_args.args[0]
    published = bus.publish.await_args.args[0]

    assert published.payload["id"] == str(recorded.id)
    # The payload's id must be the one that survives the render, which spreads
    # the payload *after* the bus event's own id.
    assert published.payload["id"] != str(published.id)


async def test_a_denied_tool_call_carries_its_row_id_too():
    repo, bus = AsyncMock(), AsyncMock()
    service = AuditService(repo, bus)

    await service.log_tool_call(ORG, AGENT, EXECUTION, "sql_query", False, "Blocked by policy")

    recorded = repo.record_event.await_args.args[0]
    published = bus.publish.await_args.args[0]

    assert published.type == "audit.tool.denied"
    assert published.payload["id"] == str(recorded.id)


async def test_llm_cost_event_is_published_with_its_persisted_row_id():
    repo, bus = AsyncMock(), AsyncMock()
    service = CostService(cost_repo=repo, event_bus=bus)

    await service.record_llm_cost(
        org_id=ORG,
        agent_id=AGENT,
        execution_id=EXECUTION,
        model="openai/gpt-oss-20b",
        prompt_tokens=100,
        completion_tokens=50,
    )

    recorded = repo.record_cost.await_args.args[0]
    published = bus.publish.await_args.args[0]

    assert published.payload["id"] == str(recorded.id)


async def test_two_calls_in_one_run_get_distinct_ids():
    """The console drops an event whose id it has already seen, so two real
    tool calls sharing an id would silently collapse into one."""
    repo, bus = AsyncMock(), AsyncMock()
    service = AuditService(repo, bus)

    await service.log_tool_call(ORG, AGENT, EXECUTION, "search_solr", True, "")
    await service.log_tool_call(ORG, AGENT, EXECUTION, "audit_website", True, "")

    first, second = (call.args[0].payload["id"] for call in bus.publish.await_args_list)
    assert first != second

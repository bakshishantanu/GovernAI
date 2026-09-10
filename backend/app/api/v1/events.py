"""The org-wide live feed: one SSE stream per signed-in user, scoped by role,
so the console never needs a manual refresh anywhere.

`/executions/{id}/stream` (in `executions.py`) already proves the pattern for
one run. This is the same `sse.stream()` plumbing pointed at every event a
user is allowed to see rather than one execution's slice of them.

Scoping, per role:
- ``admin`` — every event in their org. Unscoped by design.
- ``agent_builder`` — events for agents they built (owner) or that were
  handed to them (assigned) — can be both, so this is an OR, not two
  separate cases — plus only their own requests (matches
  `agent_requests.py`'s existing claim restriction).

Agent ownership can change mid-connection — a request gets claimed, an agent
gets handed over — so the allowed agent-id set is refreshed on every
heartbeat tick rather than resolved once at connect time.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.auth import CurrentUser
from app.api.sse import SSE_HEADERS, format_sse
from app.api.sse import stream as sse_stream
from app.domain.agents.repository import AgentRepository
from app.domain.auth.middleware import get_current_user
from app.infrastructure.event_bus import Event

router = APIRouter(prefix="/events", tags=["events"])

#: Events that belong to a specific agent, and are therefore scoped by
#: ownership/handover for anyone who isn't an admin.
AGENT_SCOPED_EVENTS = frozenset(
    {
        "audit.agent.created",
        "audit.agent.suspended",
        "audit.agent.reactivated",
        "audit.compliance.passed",
        "audit.compliance.failed",
        "audit.tool.allowed",
        "audit.tool.denied",
        "cost.llm.incurred",
        "agent.suspended",
        "agent.reactivated",
    }
)

REQUEST_STATUS_EVENT = "request_status"


def is_event_visible(
    event: Event,
    *,
    org_id: str,
    role: str,
    user_id: str,
    allowed_agent_ids: set[str],
) -> bool:
    """Pure scoping rule, kept separate from the route so it is unit-testable
    without a database, an event bus, or an HTTP client.

    Positive match only, same rule as the per-execution stream
    (`executions.py`): an event that cannot be positively placed in this
    org, or this user's slice of it, is dropped rather than guessed into
    view.
    """
    if event.payload.get("org_id") != org_id:
        return False

    if event.type == REQUEST_STATUS_EVENT:
        if role == "agent_builder":
            return event.payload.get("requester_id") == user_id
        return True  # admin watches every request org-wide

    if event.type not in AGENT_SCOPED_EVENTS:
        return False
    if role == "admin":
        return True
    return event.payload.get("agent_id") in allowed_agent_ids


@router.get("/stream")
async def stream_global_events(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One live SSE feed of everything this user is allowed to see, org-wide."""
    agent_repo = AgentRepository(db)

    org_id = str(current_user.org_id)
    user_id = str(current_user.id)
    role = current_user.role

    # Populated for a non-admin caller only; admin never consults it.
    allowed_agent_ids: set[str] = set()

    async def refresh_scope() -> None:
        if role == "admin":
            return
        # Passing both owner_id and assigned_user_id together already ORs
        # them (see repository.list_agents_by_org) -- a merged agent_builder
        # watches agents they built and agents handed to them, since they
        # can be either or both.
        agents = await agent_repo.list_agents_by_org(
            current_user.org_id,
            limit=200,
            owner_id=current_user.id,
            assigned_user_id=current_user.id,
        )
        allowed_agent_ids.clear()
        allowed_agent_ids.update(str(agent.id) for agent in agents)

    await refresh_scope()

    def matches(event: Event) -> bool:
        return is_event_visible(
            event,
            org_id=org_id,
            role=role,
            user_id=user_id,
            allowed_agent_ids=allowed_agent_ids,
        )

    def render(event: Event) -> str:
        return format_sse(event.type, {"id": str(event.id), "at": event.timestamp, **event.payload})

    async def on_heartbeat() -> tuple[str | None, bool]:
        # Ownership/handover can change mid-connection (a request gets
        # claimed, an agent gets handed over) -- re-resolve rather than
        # trust a snapshot taken at connect time.
        await refresh_scope()
        return None, True  # never closes on its own; the client disconnects

    return StreamingResponse(
        sse_stream(matches=matches, render=render, on_heartbeat=on_heartbeat),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )

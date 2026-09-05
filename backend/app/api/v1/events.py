from __future__ import annotations

"""The organisation-wide event stream (#57).

One long-lived SSE connection carrying everything that happens in an org, so
the console can be live without every screen opening its own stream.

This was blocked for several cycles: `audit.tool.*`, `cost.*` and
`agent.suspended` carried an `execution_id` and nothing else identifying, so a
feed could not tell which organisation an event belonged to and could not be
filtered safely. Since [D-030] every published event carries `org_id` and
`agent_id`, which is what makes this route possible.

The filter is a **positive match only**: an event whose `org_id` does not
equal the caller's is dropped. An event with no `org_id` at all is also
dropped, never assumed to belong to the caller. Getting that backwards would
leak one organisation's tool calls into another's console, which is the worst
bug this product could have.

Unlike `/executions/{id}/stream`, this one never ends on its own — there is no
"done" for an organisation. It stays open until the client goes away, which is
why the SSE client's reconnect has to be switched on for it.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas.auth import CurrentUser
from app.api.sse import SSE_HEADERS, format_sse, stream as sse_stream
from app.domain.auth.middleware import get_current_user
from app.infrastructure.event_bus import Event

router = APIRouter(prefix="/events", tags=["events"])

#: Everything the console cares about org-wide. Anything not listed is not
#: forwarded, so adding a noisy internal event later cannot flood the browser.
ORG_SCOPED_EVENTS = (
    "audit.tool.allowed",
    "audit.tool.denied",
    "cost.llm.incurred",
    "agent.suspended",
    "agent.reactivated",
    "audit.agent.created",
)


@router.get("/stream")
async def stream_org_events(user: CurrentUser = Depends(get_current_user)):
    """Live feed of everything happening in the caller's organisation.

    Authorisation happens once, here. Afterwards the stream only forwards
    events whose `org_id` matches the already-authorised organisation.
    """
    wanted_org_id = str(user.org_id)

    def matches(event: Event) -> bool:
        if event.type not in ORG_SCOPED_EVENTS:
            return False
        # Positive match only — no org id means the event is dropped.
        return event.payload.get("org_id") == wanted_org_id

    def render(event: Event) -> str:
        return format_sse(
            event.type,
            {"id": str(event.id), "at": event.timestamp, **event.payload},
        )

    # Sent immediately so a client knows it is connected before anything
    # happens; an org can be quiet for a long time.
    initial = [format_sse("ready", {"org_id": wanted_org_id})]

    return StreamingResponse(
        sse_stream(initial=initial, matches=matches, render=render),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )

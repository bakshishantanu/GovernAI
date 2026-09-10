from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

TicketDraftStatus = Literal["PENDING_REVIEW", "POSTED", "REJECTED"]


class TicketDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    agent_id: UUID
    execution_id: UUID | None = None
    ticket_id: str
    body: str
    status: TicketDraftStatus
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime

    #: Resolved for the reviewer's benefit so the console does not have to
    #: join agents client-side just to label a row.
    agent_name: str | None = None
    #: Deep link to the ticket. Built from the server's configured ticketing
    #: base URL, which the frontend has no other way to know.
    ticket_url: str | None = None

    @classmethod
    def from_draft(cls, draft, *, ticket_base_url: str = "") -> "TicketDraftResponse":
        # getattr rather than draft.agent: drafts built in tests are transient
        # and have no relationship loaded.
        agent = getattr(draft, "agent", None)
        base = ticket_base_url.rstrip("/")
        return cls(
            id=draft.id,
            org_id=draft.org_id,
            agent_id=draft.agent_id,
            execution_id=draft.execution_id,
            ticket_id=draft.ticket_id,
            body=draft.body,
            status=draft.status,
            reviewed_by=draft.reviewed_by,
            reviewed_at=draft.reviewed_at,
            review_note=draft.review_note,
            created_at=draft.created_at,
            agent_name=getattr(agent, "name", None),
            ticket_url=f"{base}/browse/{draft.ticket_id}" if base else None,
        )


class TicketDraftReject(BaseModel):
    note: str | None = None

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


class TicketDraftReject(BaseModel):
    note: str | None = None

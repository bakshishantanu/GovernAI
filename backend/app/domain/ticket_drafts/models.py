from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class TicketDraft(Base):
    """A reply an agent composed for a ticket, held for human review.

    The agent never writes to the ticketing backend itself. It produces a
    row here, and the reply only reaches the real ticket when a human
    approves it (see TicketDraftService.approve).
    """

    __tablename__ = "ticket_drafts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"))
    execution_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("executions.id"), nullable=True
    )

    ticket_id: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    #: PENDING_REVIEW -> POSTED | REJECTED. A draft is only ever posted from
    #: PENDING_REVIEW, so approving twice cannot double-post.
    status: Mapped[str] = mapped_column(String(20), server_default="PENDING_REVIEW", nullable=False)

    #: Set when a human acts on the draft, not when the agent creates it.
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Free-text reason captured on rejection, so the audit trail says why.
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ticket_drafts.models import TicketDraft


class TicketDraftRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, draft: TicketDraft) -> TicketDraft:
        self.session.add(draft)
        return draft

    async def get(self, draft_id: UUID) -> TicketDraft | None:
        result = await self.session.execute(select(TicketDraft).where(TicketDraft.id == draft_id))
        return result.scalar_one_or_none()

    async def list_for_org(
        self,
        org_id: UUID,
        status: str | None = None,
        agent_ids: list[UUID] | None = None,
    ) -> list[TicketDraft]:
        query = select(TicketDraft).where(TicketDraft.org_id == org_id)
        if status:
            query = query.where(TicketDraft.status == status)
        if agent_ids is not None:
            # Empty list means "this reviewer owns no agents", which must
            # return nothing rather than degrading to "no filter at all".
            query = query.where(TicketDraft.agent_id.in_(agent_ids))
        result = await self.session.execute(query.order_by(TicketDraft.created_at.desc()))
        return list(result.scalars().all())

    async def mark_reviewed(
        self,
        draft_id: UUID,
        new_status: str,
        reviewer_id: UUID,
        note: str | None = None,
    ) -> bool:
        """Move a draft out of PENDING_REVIEW, once.

        Conditioned on the current status so two concurrent approvals cannot
        both post the same reply. Returns False if it was already acted on.
        """
        result = await self.session.execute(
            update(TicketDraft)
            .where(TicketDraft.id == draft_id, TicketDraft.status == "PENDING_REVIEW")
            .values(
                status=new_status,
                reviewed_by=reviewer_id,
                reviewed_at=datetime.now(timezone.utc),
                review_note=note,
            )
        )
        return result.rowcount > 0

    async def flush(self) -> None:
        await self.session.flush()

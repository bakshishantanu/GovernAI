from __future__ import annotations

import uuid
from uuid import UUID

from app.domain.ticket_drafts.models import TicketDraft
from app.domain.ticket_drafts.repository import TicketDraftRepository
from app.skills.ticketing import TicketingAdapter


class DraftNotFound(Exception):
    pass


class DraftAlreadyReviewed(Exception):
    """Raised when a draft has already been posted or rejected.

    Kept distinct from DraftNotFound so the API can answer 409 rather than
    404: the draft exists, it just is not actionable any more.
    """


class TicketingNotConfigured(Exception):
    """No real ticketing backend is wired up, so a draft cannot be posted."""


class TicketDraftService:
    def __init__(self, repo: TicketDraftRepository, adapter: TicketingAdapter | None = None):
        self.repo = repo
        self.adapter = adapter

    async def create_draft(
        self,
        *,
        org_id: UUID,
        agent_id: UUID,
        execution_id: UUID | None,
        ticket_id: str,
        body: str,
    ) -> TicketDraft:
        draft = TicketDraft(
            id=uuid.uuid4(),
            org_id=org_id,
            agent_id=agent_id,
            execution_id=execution_id,
            ticket_id=ticket_id,
            body=body,
            status="PENDING_REVIEW",
        )
        await self.repo.create(draft)
        await self.repo.flush()
        return draft

    async def list_drafts(
        self,
        org_id: UUID,
        status: str | None = None,
        agent_ids: list[UUID] | None = None,
    ) -> list[TicketDraft]:
        return await self.repo.list_for_org(org_id, status=status, agent_ids=agent_ids)

    async def approve(self, draft_id: UUID, org_id: UUID, reviewer_id: UUID) -> TicketDraft:
        """Post the draft to the real ticket, then record who released it.

        The status flip happens first and is conditional on PENDING_REVIEW, so
        a second concurrent approval is rejected before anything is sent. If
        the post then fails, the flip is rolled back by the caller's
        transaction and the draft stays reviewable rather than being marked
        posted when it never reached the ticket.
        """
        draft = await self._get_actionable(draft_id, org_id)

        if self.adapter is None:
            raise TicketingNotConfigured(
                "No ticketing backend is configured, so this draft cannot be posted."
            )

        claimed = await self.repo.mark_reviewed(draft_id, "POSTED", reviewer_id)
        if not claimed:
            raise DraftAlreadyReviewed(f"Draft {draft_id} is no longer pending review")

        await self.adapter.add_reply(draft.ticket_id, draft.body)

        refreshed = await self.repo.get(draft_id)
        if refreshed is None:  # pragma: no cover - defensive
            raise DraftNotFound(str(draft_id))
        return refreshed

    async def reject(
        self, draft_id: UUID, org_id: UUID, reviewer_id: UUID, note: str | None = None
    ) -> TicketDraft:
        await self._get_actionable(draft_id, org_id)

        rejected = await self.repo.mark_reviewed(draft_id, "REJECTED", reviewer_id, note=note)
        if not rejected:
            raise DraftAlreadyReviewed(f"Draft {draft_id} is no longer pending review")

        refreshed = await self.repo.get(draft_id)
        if refreshed is None:  # pragma: no cover - defensive
            raise DraftNotFound(str(draft_id))
        return refreshed

    async def _get_actionable(self, draft_id: UUID, org_id: UUID) -> TicketDraft:
        draft = await self.repo.get(draft_id)
        # An out-of-org draft is reported as missing, not forbidden, so this
        # endpoint cannot be used to probe which draft ids exist elsewhere.
        if draft is None or draft.org_id != org_id:
            raise DraftNotFound(str(draft_id))
        if draft.status != "PENDING_REVIEW":
            raise DraftAlreadyReviewed(f"Draft {draft_id} is already {draft.status}")
        return draft

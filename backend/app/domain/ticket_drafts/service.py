from __future__ import annotations

import uuid
from uuid import UUID

from app.domain.ticket_drafts.models import TicketDraft
from app.domain.ticket_drafts.repository import TicketDraftRepository
from app.skills.ticketing import TicketingAdapter


class DraftNotFound(Exception):
    pass


class DraftAlreadyReviewed(Exception):
    """Raised when a draft has already been posted or escalated.

    Kept distinct from DraftNotFound so the API can answer 409 rather than
    404: the draft exists, it just is not actionable any more.
    """


class TicketingNotConfigured(Exception):
    """No real ticketing backend is wired up, so a draft cannot be posted."""


#: Posted back onto the ticket the moment a draft is escalated, so the
#: person who raised it is never left silent while it waits for a more
#: senior reviewer. Deliberately generic and reassuring rather than
#: apologetic or specific — the actual fix still has to come from whoever
#: picks it up next.
UNDER_REVIEW_MESSAGE = (
    "Thanks for reaching out. Your issue has been escalated to our team for further review — "
    "it will be fixed, and we will connect with you as soon as possible. This ticket is "
    "currently under review."
)


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

    async def escalate(
        self, draft_id: UUID, org_id: UUID, reviewer_id: UUID, note: str | None = None
    ) -> TicketDraft:
        """Send a drafted reply up for higher-authority review, instead of discarding it.

        Unlike the old reject (a silent discard), this still writes to the
        ticket: a fixed, reassuring message goes out immediately so the
        requester knows their issue is being handled, then the draft is
        parked UNDER_REVIEW rather than closed. Same optimistic-concurrency
        shape as approve() — the status flip is conditional on
        PENDING_REVIEW and happens before the ticket write, so two
        concurrent escalations cannot both post the message.
        """
        draft = await self._get_actionable(draft_id, org_id)

        if self.adapter is None:
            raise TicketingNotConfigured(
                "No ticketing backend is configured, so the requester cannot be notified."
            )

        escalated = await self.repo.mark_reviewed(draft_id, "UNDER_REVIEW", reviewer_id, note=note)
        if not escalated:
            raise DraftAlreadyReviewed(f"Draft {draft_id} is no longer pending review")

        await self.adapter.add_reply(draft.ticket_id, UNDER_REVIEW_MESSAGE)

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

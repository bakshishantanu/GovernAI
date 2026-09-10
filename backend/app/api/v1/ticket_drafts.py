from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_agent_service, get_db, get_ticket_draft_service
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.ticket_draft import TicketDraftReject, TicketDraftResponse
from app.config import settings
from app.domain.agents.service import AgentService
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_builder_or_admin
from app.domain.ticket_drafts.service import (
    DraftAlreadyReviewed,
    DraftNotFound,
    TicketDraftService,
    TicketingNotConfigured,
)

router = APIRouter(prefix="/ticket-drafts", tags=["Ticket Drafts"])


def _to_response(draft) -> TicketDraftResponse:
    return TicketDraftResponse.from_draft(draft, ticket_base_url=settings.JIRA_BASE_URL)


async def _visible_agent_ids(user: CurrentUser, agent_service: AgentService) -> list[UUID] | None:
    """Which agents' drafts this caller may see.

    None means "no restriction" (admins). A builder is scoped to the agents
    they own or are assigned, matching how agents and executions are already
    filtered elsewhere.
    """
    if not user.is_builder:
        return None
    agents = await agent_service.agent_repo.list_agents_by_org(
        user.org_id, owner_id=user.id, assigned_user_id=user.id
    )
    return [a.id for a in agents]


@router.get("/", response_model=Envelope[list[TicketDraftResponse]])
async def list_ticket_drafts(
    draft_status: Optional[str] = "PENDING_REVIEW",
    user: CurrentUser = Depends(get_current_user),
    service: TicketDraftService = Depends(get_ticket_draft_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    """Replies an agent has composed and parked for review.

    Defaults to the pending ones, since that is the queue a reviewer acts on.
    Pass `draft_status=` (empty) to see every draft including posted and
    rejected ones.
    """
    agent_ids = await _visible_agent_ids(user, agent_service)
    drafts = await service.list_drafts(
        user.org_id, status=draft_status or None, agent_ids=agent_ids
    )
    return Envelope(data=[_to_response(d) for d in drafts])


@router.post("/{draft_id}/approve", response_model=Envelope[TicketDraftResponse])
async def approve_ticket_draft(
    draft_id: UUID,
    user: CurrentUser = Depends(require_builder_or_admin),
    db: AsyncSession = Depends(get_db),
    service: TicketDraftService = Depends(get_ticket_draft_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    """Release a drafted reply: post it to the real ticket, under this user.

    This is the only path that writes a reply to the ticketing backend. The
    agent itself can never do it.
    """
    await _assert_may_review(draft_id, user, service, agent_service)

    try:
        draft = await service.approve(draft_id, org_id=user.org_id, reviewer_id=user.id)
    except DraftNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    except DraftAlreadyReviewed as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except TicketingNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    # Committed only once the reply actually reached the ticket, so a failed
    # post leaves the draft pending rather than marked POSTED.
    await db.commit()
    return Envelope(data=_to_response(draft))


@router.post("/{draft_id}/reject", response_model=Envelope[TicketDraftResponse])
async def reject_ticket_draft(
    draft_id: UUID,
    payload: TicketDraftReject | None = None,
    user: CurrentUser = Depends(require_builder_or_admin),
    db: AsyncSession = Depends(get_db),
    service: TicketDraftService = Depends(get_ticket_draft_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    """Discard a drafted reply. Nothing is sent to the ticket."""
    await _assert_may_review(draft_id, user, service, agent_service)

    try:
        draft = await service.reject(
            draft_id,
            org_id=user.org_id,
            reviewer_id=user.id,
            note=payload.note if payload else None,
        )
    except DraftNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    except DraftAlreadyReviewed as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    await db.commit()
    return Envelope(data=_to_response(draft))


async def _assert_may_review(
    draft_id: UUID,
    user: CurrentUser,
    service: TicketDraftService,
    agent_service: AgentService,
) -> None:
    """A builder may only act on drafts from their own agents.

    Answers 404 rather than 403 for someone else's draft, so this cannot be
    used to discover which draft ids exist.
    """
    draft = await service.repo.get(draft_id)
    if draft is None or draft.org_id != user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    agent_ids = await _visible_agent_ids(user, agent_service)
    if agent_ids is not None and draft.agent_id not in agent_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.ticket_drafts import (
    approve_ticket_draft,
    list_ticket_drafts,
    reject_ticket_draft,
)
from app.domain.agents.models import Agent
from app.domain.ticket_drafts.models import TicketDraft
from app.domain.ticket_drafts.service import DraftAlreadyReviewed, TicketingNotConfigured

ORG = uuid.uuid4()


def _user(role: str, user_id=None) -> CurrentUser:
    return CurrentUser(id=user_id or uuid.uuid4(), org_id=ORG, role=role)


def _agent(owner_id) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        org_id=ORG,
        owner_id=owner_id,
        name="Triage Bot",
        description="d",
        status="ACTIVE",
    )


def _draft(agent_id, status="PENDING_REVIEW") -> TicketDraft:
    return TicketDraft(
        id=uuid.uuid4(),
        org_id=ORG,
        agent_id=agent_id,
        execution_id=None,
        ticket_id="SCRUM-1",
        body="Proposed reply.",
        status=status,
    )


def _agent_service(agents):
    svc = AsyncMock()
    svc.agent_repo.list_agents_by_org.return_value = agents
    return svc


@pytest.mark.asyncio
async def test_builder_only_sees_drafts_from_their_own_agents():
    builder = _user("agent_builder")
    mine = _agent(builder.id)
    service = AsyncMock()
    service.list_drafts.return_value = []

    await list_ticket_drafts(
        draft_status="PENDING_REVIEW",
        user=builder,
        service=service,
        agent_service=_agent_service([mine]),
    )

    # The scoping must reach the query, not be applied after the fact.
    assert service.list_drafts.call_args.kwargs["agent_ids"] == [mine.id]


@pytest.mark.asyncio
async def test_admin_is_not_scoped_to_particular_agents():
    service = AsyncMock()
    service.list_drafts.return_value = []

    await list_ticket_drafts(
        draft_status="PENDING_REVIEW",
        user=_user("admin"),
        service=service,
        agent_service=_agent_service([]),
    )

    assert service.list_drafts.call_args.kwargs["agent_ids"] is None


@pytest.mark.asyncio
async def test_builder_cannot_approve_a_draft_from_someone_elses_agent():
    builder = _user("agent_builder")
    someone_elses = _agent(uuid.uuid4())
    draft = _draft(someone_elses.id)

    service = AsyncMock()
    service.repo.get.return_value = draft

    with pytest.raises(HTTPException) as exc:
        await approve_ticket_draft(
            draft_id=draft.id,
            user=builder,
            db=AsyncMock(),
            service=service,
            # This builder owns no agents, so the draft's agent is out of scope.
            agent_service=_agent_service([]),
        )

    assert exc.value.status_code == 404
    service.approve.assert_not_awaited()


@pytest.mark.asyncio
async def test_approving_an_already_reviewed_draft_is_a_conflict():
    admin = _user("admin")
    draft = _draft(uuid.uuid4(), status="POSTED")

    service = AsyncMock()
    service.repo.get.return_value = draft
    service.approve.side_effect = DraftAlreadyReviewed("already POSTED")

    with pytest.raises(HTTPException) as exc:
        await approve_ticket_draft(
            draft_id=draft.id,
            user=admin,
            db=AsyncMock(),
            service=service,
            agent_service=_agent_service([]),
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_approve_without_ticketing_configured_is_service_unavailable():
    admin = _user("admin")
    draft = _draft(uuid.uuid4())

    service = AsyncMock()
    service.repo.get.return_value = draft
    service.approve.side_effect = TicketingNotConfigured("no backend")

    with pytest.raises(HTTPException) as exc:
        await approve_ticket_draft(
            draft_id=draft.id,
            user=admin,
            db=AsyncMock(),
            service=service,
            agent_service=_agent_service([]),
        )

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_approve_commits_only_after_the_reply_is_posted():
    """A failed post must not leave the draft marked POSTED."""
    admin = _user("admin")
    draft = _draft(uuid.uuid4())
    db = AsyncMock()

    service = AsyncMock()
    service.repo.get.return_value = draft
    service.approve.return_value = _draft(draft.agent_id, status="POSTED")

    await approve_ticket_draft(
        draft_id=draft.id,
        user=admin,
        db=db,
        service=service,
        agent_service=_agent_service([]),
    )

    service.approve.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_records_the_note_and_posts_nothing():
    from app.api.schemas.ticket_draft import TicketDraftReject

    admin = _user("admin")
    draft = _draft(uuid.uuid4())

    service = AsyncMock()
    service.repo.get.return_value = draft
    service.reject.return_value = _draft(draft.agent_id, status="REJECTED")

    await reject_ticket_draft(
        draft_id=draft.id,
        payload=TicketDraftReject(note="Tone is off"),
        user=admin,
        db=AsyncMock(),
        service=service,
        agent_service=_agent_service([]),
    )

    assert service.reject.call_args.kwargs["note"] == "Tone is off"
    service.approve.assert_not_awaited()

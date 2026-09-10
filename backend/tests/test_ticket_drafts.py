from __future__ import annotations

import uuid

import pytest

from app.domain.ticket_drafts.models import TicketDraft
from app.domain.ticket_drafts.service import (
    DraftAlreadyReviewed,
    DraftNotFound,
    TicketDraftService,
    TicketingNotConfigured,
)
from app.domain.ticket_drafts.store import ExecutionScopedDraftStore
from app.skills.ticketing import MockTicketingAdapter


class FakeRepo:
    """In-memory stand-in for TicketDraftRepository.

    mark_reviewed keeps the real one's conditional-update behaviour, since
    that is exactly what stops a draft being posted twice.
    """

    def __init__(self, drafts: list[TicketDraft] | None = None):
        self.drafts = {d.id: d for d in (drafts or [])}
        self.flushed = False

    async def create(self, draft: TicketDraft) -> TicketDraft:
        self.drafts[draft.id] = draft
        return draft

    async def get(self, draft_id):
        return self.drafts.get(draft_id)

    async def list_for_org(self, org_id, status=None, agent_ids=None):
        out = [d for d in self.drafts.values() if d.org_id == org_id]
        if status:
            out = [d for d in out if d.status == status]
        if agent_ids is not None:
            out = [d for d in out if d.agent_id in agent_ids]
        return out

    async def mark_reviewed(self, draft_id, new_status, reviewer_id, note=None):
        draft = self.drafts.get(draft_id)
        if draft is None or draft.status != "PENDING_REVIEW":
            return False
        draft.status = new_status
        draft.reviewed_by = reviewer_id
        draft.review_note = note
        return True

    async def flush(self) -> None:
        self.flushed = True


def _draft(**overrides) -> TicketDraft:
    d = TicketDraft(
        id=overrides.get("id", uuid.uuid4()),
        org_id=overrides.get("org_id", uuid.uuid4()),
        agent_id=overrides.get("agent_id", uuid.uuid4()),
        execution_id=None,
        ticket_id=overrides.get("ticket_id", "TCK-1001"),
        body=overrides.get("body", "Proposed reply."),
        status=overrides.get("status", "PENDING_REVIEW"),
    )
    return d


@pytest.mark.asyncio
async def test_agent_drafting_creates_a_pending_row_and_posts_nothing():
    repo = FakeRepo()
    adapter = MockTicketingAdapter()
    service = TicketDraftService(repo=repo, adapter=adapter)
    org_id, agent_id, exec_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    store = ExecutionScopedDraftStore(
        service, org_id=org_id, agent_id=agent_id, execution_id=exec_id
    )
    draft_id = await store.save_draft("TCK-1001", "Try clearing your cache.")

    saved = await repo.get(uuid.UUID(draft_id))
    assert saved.status == "PENDING_REVIEW"
    assert saved.org_id == org_id and saved.agent_id == agent_id
    assert saved.execution_id == exec_id

    # Nothing reached the ticket.
    ticket = await adapter.get("TCK-1001")
    assert ticket.replies == []


@pytest.mark.asyncio
async def test_approve_posts_the_reply_and_marks_it_posted():
    draft = _draft(body="Here is the fix.")
    repo = FakeRepo([draft])
    adapter = MockTicketingAdapter()
    service = TicketDraftService(repo=repo, adapter=adapter)
    reviewer = uuid.uuid4()

    result = await service.approve(draft.id, org_id=draft.org_id, reviewer_id=reviewer)

    assert result.status == "POSTED"
    assert result.reviewed_by == reviewer
    ticket = await adapter.get("TCK-1001")
    assert ticket.replies == ["Here is the fix."]


@pytest.mark.asyncio
async def test_approving_twice_does_not_post_twice():
    draft = _draft(body="Only once please.")
    repo = FakeRepo([draft])
    adapter = MockTicketingAdapter()
    service = TicketDraftService(repo=repo, adapter=adapter)

    await service.approve(draft.id, org_id=draft.org_id, reviewer_id=uuid.uuid4())

    with pytest.raises(DraftAlreadyReviewed):
        await service.approve(draft.id, org_id=draft.org_id, reviewer_id=uuid.uuid4())

    ticket = await adapter.get("TCK-1001")
    assert ticket.replies == ["Only once please."]


@pytest.mark.asyncio
async def test_reject_marks_rejected_and_posts_nothing():
    draft = _draft()
    repo = FakeRepo([draft])
    adapter = MockTicketingAdapter()
    service = TicketDraftService(repo=repo, adapter=adapter)

    result = await service.reject(
        draft.id, org_id=draft.org_id, reviewer_id=uuid.uuid4(), note="Tone is wrong"
    )

    assert result.status == "REJECTED"
    assert result.review_note == "Tone is wrong"
    ticket = await adapter.get("TCK-1001")
    assert ticket.replies == []


@pytest.mark.asyncio
async def test_a_rejected_draft_cannot_later_be_approved():
    draft = _draft(status="REJECTED")
    repo = FakeRepo([draft])
    service = TicketDraftService(repo=repo, adapter=MockTicketingAdapter())

    with pytest.raises(DraftAlreadyReviewed):
        await service.approve(draft.id, org_id=draft.org_id, reviewer_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_draft_from_another_org_reads_as_missing():
    """Not 'forbidden': that would confirm the id exists."""
    draft = _draft()
    repo = FakeRepo([draft])
    service = TicketDraftService(repo=repo, adapter=MockTicketingAdapter())

    with pytest.raises(DraftNotFound):
        await service.approve(draft.id, org_id=uuid.uuid4(), reviewer_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_approve_without_a_ticketing_backend_is_refused():
    """Better to refuse than to mark POSTED when nothing was sent."""
    draft = _draft()
    repo = FakeRepo([draft])
    service = TicketDraftService(repo=repo, adapter=None)

    with pytest.raises(TicketingNotConfigured):
        await service.approve(draft.id, org_id=draft.org_id, reviewer_id=uuid.uuid4())

    assert (await repo.get(draft.id)).status == "PENDING_REVIEW"


@pytest.mark.asyncio
async def test_listing_filters_to_pending_for_the_given_agents():
    org = uuid.uuid4()
    mine, theirs = uuid.uuid4(), uuid.uuid4()
    drafts = [
        _draft(org_id=org, agent_id=mine, status="PENDING_REVIEW"),
        _draft(org_id=org, agent_id=mine, status="POSTED"),
        _draft(org_id=org, agent_id=theirs, status="PENDING_REVIEW"),
    ]
    service = TicketDraftService(repo=FakeRepo(drafts), adapter=None)

    visible = await service.list_drafts(org, status="PENDING_REVIEW", agent_ids=[mine])

    assert len(visible) == 1
    assert visible[0].agent_id == mine

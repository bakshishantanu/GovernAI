"""Every significant agent lifecycle transition must leave a trace.
log_agent_created already existed but was never called from anywhere in the
app (confirmed live: creating, activating, and deleting a real agent left
zero audit entries, unlike submit-for-review's compliance check). This
covers the two missing log methods (activated, deleted) plus wiring
log_agent_created in for the first time."""

from unittest.mock import AsyncMock
from uuid import uuid4

import app.domain.agents.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
from app.domain.audit.service import AuditService

ORG, ACTOR, AGENT = uuid4(), uuid4(), uuid4()


def _service():
    repo, bus = AsyncMock(), AsyncMock()
    return AuditService(repo, bus), repo, bus


async def test_agent_created_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_agent_created(ORG, ACTOR, AGENT)

    event = repo.record_event.await_args.args[0]
    assert event.action == "agent_created"
    assert event.policy_decision == "ALLOW"
    assert event.org_id == ORG
    assert event.actor_id == ACTOR
    assert event.agent_id == AGENT
    bus.publish.assert_awaited_once()


async def test_agent_activated_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_agent_activated(ORG, ACTOR, AGENT)

    event = repo.record_event.await_args.args[0]
    assert event.action == "agent_activated"
    assert event.policy_decision == "ALLOW"
    assert event.org_id == ORG
    assert event.actor_id == ACTOR
    assert event.agent_id == AGENT
    bus.publish.assert_awaited_once()


async def test_agent_deleted_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_agent_deleted(ORG, ACTOR, AGENT)

    event = repo.record_event.await_args.args[0]
    assert event.action == "agent_deleted"
    assert event.policy_decision == "ALLOW"
    assert event.org_id == ORG
    assert event.actor_id == ACTOR
    assert event.agent_id == AGENT
    bus.publish.assert_awaited_once()

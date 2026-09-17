"""Governance requires every meaningful action to leave a trace -- saving,
changing, or deleting a shared org credential (e.g. Jira) is exactly that
kind of action, so it must be audited the same way agent lifecycle
transitions already are."""

from unittest.mock import AsyncMock
from uuid import uuid4

# See test_compliance_events.py: constructing any mapped class configures
# every mapper in the declarative registry, and some models reference others
# by string name across modules -- a focused test run has to import every
# model main.py does, or mapper configuration fails.
import app.domain.agents.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
from app.domain.audit.service import AuditService

ORG, ACTOR = uuid4(), uuid4()


def _service():
    repo, bus = AsyncMock(), AsyncMock()
    return AuditService(repo, bus), repo, bus


async def test_connection_saved_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_connection_saved(ORG, ACTOR, requirement_key="jira", label="Jira account")

    event = repo.record_event.await_args.args[0]
    assert event.action == "connection_saved"
    assert event.policy_decision == "ALLOW"
    assert event.org_id == ORG
    assert event.actor_id == ACTOR
    assert event.agent_id is None
    assert event.resource == "jira"
    assert "Jira account" in event.reason
    bus.publish.assert_awaited_once()


async def test_connection_deleted_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_connection_deleted(ORG, ACTOR, requirement_key="jira")

    event = repo.record_event.await_args.args[0]
    assert event.action == "connection_deleted"
    assert event.policy_decision == "ALLOW"
    assert event.resource == "jira"
    bus.publish.assert_awaited_once()

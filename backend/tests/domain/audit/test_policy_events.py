"""Governance policies are the rules that constrain every agent in the org --
creating, changing, disabling, or deleting one must leave a trace, the same
as every other governance-relevant action. Confirmed live before this fix:
none of the 5 policy-mutating routes logged anything at all."""

from unittest.mock import AsyncMock
from uuid import uuid4

import app.domain.agents.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
from app.domain.audit.service import AuditService

ORG, ACTOR, POLICY, RULE = uuid4(), uuid4(), uuid4(), uuid4()


def _service():
    repo, bus = AsyncMock(), AsyncMock()
    return AuditService(repo, bus), repo, bus


async def test_policy_created_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_policy_created(ORG, ACTOR, POLICY, name="Blocklist Policy")

    event = repo.record_event.await_args.args[0]
    assert event.action == "policy_created"
    assert event.policy_decision == "ALLOW"
    assert event.resource == str(POLICY)
    assert "Blocklist Policy" in event.reason
    bus.publish.assert_awaited_once()


async def test_policy_updated_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_policy_updated(ORG, ACTOR, POLICY, reason="enabled: True -> False")

    event = repo.record_event.await_args.args[0]
    assert event.action == "policy_updated"
    assert event.resource == str(POLICY)
    assert event.reason == "enabled: True -> False"
    bus.publish.assert_awaited_once()


async def test_policy_deleted_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_policy_deleted(ORG, ACTOR, POLICY, name="Blocklist Policy")

    event = repo.record_event.await_args.args[0]
    assert event.action == "policy_deleted"
    assert event.resource == str(POLICY)
    assert "Blocklist Policy" in event.reason
    bus.publish.assert_awaited_once()


async def test_policy_rule_added_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_policy_rule_added(ORG, ACTOR, POLICY, RULE, rule_type="DENY_LIST")

    event = repo.record_event.await_args.args[0]
    assert event.action == "policy_rule_added"
    assert event.resource == str(RULE)
    assert "DENY_LIST" in event.reason
    assert str(POLICY) in event.reason
    bus.publish.assert_awaited_once()


async def test_policy_rule_toggled_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_policy_rule_toggled(ORG, ACTOR, POLICY, RULE, enabled=False)

    event = repo.record_event.await_args.args[0]
    assert event.action == "policy_rule_disabled"
    assert event.resource == str(RULE)
    bus.publish.assert_awaited_once()

    await service.log_policy_rule_toggled(ORG, ACTOR, POLICY, RULE, enabled=True)
    event = repo.record_event.await_args.args[0]
    assert event.action == "policy_rule_enabled"

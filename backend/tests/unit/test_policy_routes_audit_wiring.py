"""Confirms the 5 policy-mutating routes actually call the audit service,
not just that the AuditService methods work in isolation
(test_policy_events.py covers that). Live-tested before this fix: none of
create/update/delete a policy, or add/toggle a rule, left any audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.schemas.auth import CurrentUser
from app.api.schemas.policy import PolicyCreate, PolicyRuleCreate
from app.api.v1.policies import add_rule, create_policy, delete_policy, toggle_rule, update_policy
from app.domain.policies.models import Policy, PolicyRule


def _policy(org_id, name="Test Policy"):
    now = datetime.now(timezone.utc)
    policy = Policy(
        id=uuid.uuid4(), org_id=org_id, name=name, description="d", enabled=True,
        created_at=now, updated_at=now,
    )
    policy.rules = []
    return policy


@pytest.mark.asyncio
async def test_create_policy_writes_an_audit_event():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")
    created = _policy(org_id, name="New Policy")

    repo = AsyncMock()
    repo.create_policy.return_value = created
    repo.get_policy.return_value = created
    db = AsyncMock()
    audit_service = AsyncMock()

    await create_policy(
        policy_in=PolicyCreate(name="New Policy", description="d", enabled=True, rules=[]),
        current_user=admin, db=db, repo=repo, audit_service=audit_service,
    )

    audit_service.log_policy_created.assert_awaited_once_with(
        org_id, admin.id, created.id, name="New Policy"
    )


@pytest.mark.asyncio
async def test_update_policy_writes_an_audit_event():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")
    policy = _policy(org_id)

    repo = AsyncMock()
    repo.get_policy.return_value = policy
    db = AsyncMock()
    audit_service = AsyncMock()

    await update_policy(
        policy_id=policy.id, enabled=False, name=None, description=None,
        current_user=admin, db=db, repo=repo, audit_service=audit_service,
    )

    audit_service.log_policy_updated.assert_awaited_once()
    call_args = audit_service.log_policy_updated.await_args.args
    assert call_args[0] == org_id
    assert call_args[1] == admin.id
    assert call_args[2] == policy.id


@pytest.mark.asyncio
async def test_delete_policy_writes_an_audit_event():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")
    policy = _policy(org_id, name="Doomed Policy")

    repo = AsyncMock()
    repo.get_policy.return_value = policy
    db = AsyncMock()
    audit_service = AsyncMock()

    await delete_policy(
        policy_id=policy.id, current_user=admin, db=db, repo=repo, audit_service=audit_service
    )

    audit_service.log_policy_deleted.assert_awaited_once_with(
        org_id, admin.id, policy.id, name="Doomed Policy"
    )


@pytest.mark.asyncio
async def test_add_rule_writes_an_audit_event():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")
    policy = _policy(org_id)

    repo = AsyncMock()
    repo.get_policy.return_value = policy
    db = AsyncMock()
    audit_service = AsyncMock()

    await add_rule(
        policy_id=policy.id,
        rule_in=PolicyRuleCreate(
            name="r", rule_type="DENY_LIST", config={"blocked_tools": ["sql_query"]}, priority=1
        ),
        current_user=admin, db=db, repo=repo, audit_service=audit_service,
    )

    audit_service.log_policy_rule_added.assert_awaited_once()
    call_args = audit_service.log_policy_rule_added.await_args
    assert call_args.args[0] == org_id
    assert call_args.args[1] == admin.id
    assert call_args.args[2] == policy.id
    assert call_args.kwargs["rule_type"] == "DENY_LIST"


@pytest.mark.asyncio
async def test_toggle_rule_writes_an_audit_event():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")
    policy_id = uuid.uuid4()
    rule = PolicyRule(
        id=uuid.uuid4(), policy_id=policy_id, name="r", rule_type="DENY_LIST",
        config={"blocked_tools": ["sql_query"]}, priority=1, enabled=True,
    )

    repo = AsyncMock()
    repo.get_rule.return_value = rule
    db = AsyncMock()
    audit_service = AsyncMock()

    await toggle_rule(
        policy_id=policy_id, rule_id=rule.id, enabled=False,
        current_user=admin, db=db, repo=repo, audit_service=audit_service,
    )

    audit_service.log_policy_rule_toggled.assert_awaited_once_with(
        org_id, admin.id, policy_id, rule.id, enabled=False
    )

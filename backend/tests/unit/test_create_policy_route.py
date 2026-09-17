"""Regression test for a real, live-confirmed 500: POST /policies/ crashed
every time, even with zero rules. Root cause: the route returned the
freshly-created Policy object directly after db.refresh() (which only
refreshes scalar columns, not relationships), so serializing PolicyResponse
tried to lazy-load `.rules` outside of an async-safe context
(SQLAlchemy's MissingGreenlet). Every other route that returns a Policy
(get_policy, update_policy) re-fetches through repo.get_policy(), which
eager-loads rules via selectinload -- create_policy was the one route that
didn't.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.api.schemas.auth import CurrentUser
from app.api.schemas.policy import PolicyCreate, PolicyRuleCreate
from app.api.v1.policies import create_policy
from app.domain.policies.models import Policy, PolicyRule


@pytest.mark.asyncio
async def test_create_policy_returns_the_eager_loaded_refetch_not_the_raw_created_object():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")

    # What create_policy() hands back is a plain object whose .rules a real
    # async session would refuse to lazy-load outside a request-safe context
    # -- modeled here by making it a sentinel that must NOT end up in the
    # response, rather than trying to reproduce MissingGreenlet itself.
    raw_created = Policy(
        id=uuid.uuid4(), org_id=org_id, name="raw, not eager-loaded", description="d", enabled=True,
    )
    # The properly eager-loaded object a re-fetch through get_policy() returns.
    refetched = Policy(id=raw_created.id, org_id=org_id, name="Test Policy", description="d", enabled=True)
    refetched.rules = [
        PolicyRule(
            id=uuid.uuid4(), policy_id=raw_created.id, name="r", rule_type="DENY_LIST",
            config={"blocked_tools": ["sql_query"]}, priority=1, enabled=True,
        )
    ]

    repo = AsyncMock()
    repo.create_policy.return_value = raw_created
    repo.get_policy.return_value = refetched
    db = AsyncMock()
    audit_service = AsyncMock()

    result = await create_policy(
        policy_in=PolicyCreate(
            name="Test Policy", description="d", enabled=True,
            rules=[PolicyRuleCreate(
                name="r", rule_type="DENY_LIST", config={"blocked_tools": ["sql_query"]}, priority=1,
            )],
        ),
        current_user=admin, db=db, repo=repo, audit_service=audit_service,
    )

    repo.get_policy.assert_awaited_once_with(raw_created.id, org_id)
    assert result.data is refetched
    assert result.data is not raw_created

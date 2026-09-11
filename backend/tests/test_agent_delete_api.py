"""The delete route's ownership/state checks. Called directly, in the style
of tests/test_agent_compliance_api.py: what matters here is the shape of the
refusal, not FastAPI's routing.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import delete_agent
from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.service import AgentService, InvalidStateTransitionError


def _agent(org_id, owner_id, lifecycle_state="DRAFT"):
    now = datetime.now(timezone.utc)
    agent = Agent(
        id=uuid.uuid4(),
        org_id=org_id,
        owner_id=owner_id,
        name="Abandoned Draft",
        description="Never finished",
        status="DRAFT",
        created_at=now,
        updated_at=now,
    )
    agent.passport = AgentPassport(
        id=uuid.uuid4(),
        agent_id=agent.id,
        compliance_status="PENDING",
        lifecycle_state=lifecycle_state,
        created_at=now,
        updated_at=now,
    )
    agent.passport.permissions = []
    return agent


def _service_with(agent):
    service = AsyncMock(spec=AgentService)
    service.agent_repo = AsyncMock()
    service.agent_repo.get_agent.return_value = agent
    return service


@pytest.mark.asyncio
async def test_delete_rejects_agent_from_another_org():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(uuid.uuid4(), builder.id)  # different org
    service = _service_with(agent)

    with pytest.raises(HTTPException) as exc:
        await delete_agent(agent.id, user=builder, service=service, db=AsyncMock())

    assert exc.value.status_code == 404
    service.delete_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_rejects_non_owner_builder():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, uuid.uuid4())  # owned by someone else
    service = _service_with(agent)

    with pytest.raises(HTTPException) as exc:
        await delete_agent(agent.id, user=builder, service=service, db=AsyncMock())

    assert exc.value.status_code == 403
    service.delete_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_allows_admin_regardless_of_ownership():
    org_id = uuid.uuid4()
    admin = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")
    agent = _agent(org_id, uuid.uuid4())  # owned by someone else
    service = _service_with(agent)
    db = AsyncMock()

    await delete_agent(agent.id, user=admin, service=service, db=db)

    service.delete_agent.assert_awaited_once_with(agent.id)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_allows_the_owner():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id)
    service = _service_with(agent)
    db = AsyncMock()

    await delete_agent(agent.id, user=builder, service=service, db=db)

    service.delete_agent.assert_awaited_once_with(agent.id)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_rejects_non_draft_agent_as_conflict():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id, lifecycle_state="ACTIVE")
    service = _service_with(agent)
    service.delete_agent.side_effect = InvalidStateTransitionError(
        "Only a DRAFT agent can be deleted"
    )
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await delete_agent(agent.id, user=builder, service=service, db=db)

    assert exc.value.status_code == 409
    db.commit.assert_not_awaited()

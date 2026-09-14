"""The delete route's ownership/state checks. Called directly, in the style
of tests/test_agent_compliance_api.py: what matters here is the shape of the
refusal, not FastAPI's routing.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.schemas.agent import AgentUpdate
from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import delete_agent, update_agent
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
async def test_delete_allows_active_agent():
    """Delete is no longer DRAFT-only: an owner can delete an ACTIVE agent."""
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id, lifecycle_state="ACTIVE")
    service = _service_with(agent)
    db = AsyncMock()

    await delete_agent(agent.id, user=builder, service=service, db=db)

    service.delete_agent.assert_awaited_once_with(agent.id)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_rejects_already_deleted_agent_as_conflict():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id, lifecycle_state="REVOKED")
    service = _service_with(agent)
    service.delete_agent.side_effect = InvalidStateTransitionError(
        "This agent has already been deleted"
    )
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await delete_agent(agent.id, user=builder, service=service, db=db)

    assert exc.value.status_code == 409
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_rejects_already_deleted_agent_at_the_route_as_not_found():
    """Once `deleted_at` is set, the route's own lookup treats it as gone
    (404) before ever calling the service — matching GET's behaviour."""
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id, lifecycle_state="REVOKED")
    agent.deleted_at = datetime.now(timezone.utc)
    service = _service_with(agent)

    with pytest.raises(HTTPException) as exc:
        await delete_agent(agent.id, user=builder, service=service, db=AsyncMock())

    assert exc.value.status_code == 404
    service.delete_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_rejects_a_deleted_agent_as_not_found():
    """Regression: PATCH had no `deleted_at` check at all, so a deleted
    agent's name/description could still be silently rewritten."""
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id, lifecycle_state="REVOKED")
    agent.deleted_at = datetime.now(timezone.utc)
    service = _service_with(agent)

    with pytest.raises(HTTPException) as exc:
        await update_agent(
            agent.id,
            payload=AgentUpdate(name="New name"),
            user=builder,
            db=AsyncMock(),
            service=service,
        )

    assert exc.value.status_code == 404

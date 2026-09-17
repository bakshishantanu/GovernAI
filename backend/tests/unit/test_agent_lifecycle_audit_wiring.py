"""Confirms the three previously-silent agent lifecycle routes actually call
the audit service now, not just that the AuditService methods exist in
isolation (test_agent_lifecycle_events.py covers that). Live-tested before
this fix: creating, activating, and deleting a real agent produced zero
audit entries except the pre-existing compliance-check one."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.schemas.agent import AgentCreate
from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import activate_agent, create_agent, delete_agent
from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.service import AgentService


def _agent(org_id, owner_id, lifecycle_state="DRAFT"):
    # Agent.status and AgentPassport.lifecycle_state are separate enums --
    # status has no "APPROVED" value, only lifecycle_state does.
    now = datetime.now(timezone.utc)
    agent = Agent(
        id=uuid.uuid4(), org_id=org_id, owner_id=owner_id,
        name="Test Agent", description="d",
        status="ACTIVE" if lifecycle_state == "ACTIVE" else "DRAFT",
        created_at=now, updated_at=now,
    )
    agent.passport = AgentPassport(
        id=uuid.uuid4(), agent_id=agent.id, compliance_status="PASSED",
        lifecycle_state=lifecycle_state, created_at=now, updated_at=now,
    )
    agent.passport.permissions = []
    return agent


@pytest.mark.asyncio
async def test_create_agent_writes_an_audit_event():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    created = _agent(org_id, builder.id)

    service = AsyncMock(spec=AgentService)
    service.create_agent.return_value = created
    db = AsyncMock()
    audit_service = AsyncMock()

    await create_agent(
        payload=AgentCreate(name="Test Agent", description="d", skills=["ticketing"]),
        user=builder, service=service, db=db, audit_service=audit_service,
    )

    audit_service.log_agent_created.assert_awaited_once_with(org_id, builder.id, created.id)


@pytest.mark.asyncio
async def test_activate_agent_writes_an_audit_event():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id, lifecycle_state="APPROVED")

    service = AsyncMock(spec=AgentService)
    service.agent_repo = AsyncMock()
    service.agent_repo.get_agent.return_value = agent
    db = AsyncMock()
    audit_service = AsyncMock()

    await activate_agent(agent.id, user=builder, service=service, db=db, audit_service=audit_service)

    audit_service.log_agent_activated.assert_awaited_once_with(org_id, builder.id, agent.id)


@pytest.mark.asyncio
async def test_delete_agent_writes_an_audit_event():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id)

    service = AsyncMock(spec=AgentService)
    service.agent_repo = AsyncMock()
    service.agent_repo.get_agent.return_value = agent
    db = AsyncMock()
    audit_service = AsyncMock()

    await delete_agent(agent.id, user=builder, service=service, db=db, audit_service=audit_service)

    audit_service.log_agent_deleted.assert_awaited_once_with(org_id, builder.id, agent.id)

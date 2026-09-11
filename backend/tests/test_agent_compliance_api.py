"""The submit route's answer when the compliance check refuses.

Called directly, in the style of tests/test_agent_requests_api.py: what matters
here is the shape of the refusal, not FastAPI's routing.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import submit_agent_for_review
from app.domain.agents.compliance import Violation
from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.service import AgentService, ComplianceError


def _agent(org_id, owner_id):
    """A fully-populated agent: the success path serialises it, and
    created_at/updated_at are database server defaults that a bare instance
    does not have."""
    now = datetime.now(timezone.utc)
    agent = Agent(
        id=uuid.uuid4(),
        org_id=org_id,
        owner_id=owner_id,
        name="Payroll Reporter",
        description="Reports on payroll",
        status="DRAFT",
        created_at=now,
        updated_at=now,
    )
    agent.passport = AgentPassport(
        id=uuid.uuid4(),
        agent_id=agent.id,
        compliance_status="PENDING",
        lifecycle_state="DRAFT",
        created_at=now,
        updated_at=now,
    )
    agent.passport.permissions = []
    return agent


@pytest.mark.asyncio
async def test_submit_returns_every_violation():
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id)

    service = AsyncMock(spec=AgentService)
    service.agent_repo = AsyncMock()
    service.agent_repo.get_agent.return_value = agent
    service.submit_for_review.side_effect = ComplianceError(
        [
            Violation(rule="skills", message="Agent must have at least one skill."),
            Violation(rule="forbidden_pair", message="Forbidden permission combination: …"),
        ]
    )

    audit = AsyncMock()

    # A plain AsyncMock, not an AsyncSession: the route commits the FAILED
    # verdict only for a real session, and this asserts the refusal shape.
    with pytest.raises(HTTPException) as exc:
        await submit_agent_for_review(
            agent.id, user=builder, service=service, audit=audit, db=AsyncMock()
        )

    # FRD-02: the refusal is recorded before it is reported. Asserting the call
    # here is what stops the audit write being silently dropped later.
    audit.log_compliance_failed.assert_awaited_once_with(
        builder.org_id, builder.id, agent.id, service.submit_for_review.side_effect.violations
    )
    audit.log_compliance_passed.assert_not_awaited()

    assert exc.value.status_code == 400
    assert exc.value.detail["message"] == "This agent does not pass the compliance check."
    assert [v["rule"] for v in exc.value.detail["violations"]] == ["skills", "forbidden_pair"]
    assert exc.value.detail["violations"][0]["message"] == "Agent must have at least one skill."


@pytest.mark.asyncio
async def test_submit_records_the_pass_as_well_as_the_refusal():
    """An audit log that records only what was stopped cannot answer
    "who approved this agent, and when"."""
    org_id = uuid.uuid4()
    builder = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")
    agent = _agent(org_id, builder.id)

    service = AsyncMock(spec=AgentService)
    service.agent_repo = AsyncMock()
    service.agent_repo.get_agent.return_value = agent
    audit = AsyncMock()

    # The success path reloads the agent and its skills, so db.execute() has to
    # return something with a synchronous .all().
    db = AsyncMock()
    db.execute.return_value = MagicMock(all=MagicMock(return_value=[]))

    await submit_agent_for_review(agent.id, user=builder, service=service, audit=audit, db=db)

    audit.log_compliance_passed.assert_awaited_once_with(builder.org_id, builder.id, agent.id)
    audit.log_compliance_failed.assert_not_awaited()

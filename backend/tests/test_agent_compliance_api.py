"""The submit route's answer when the compliance check refuses.

Called directly, in the style of tests/test_agent_requests_api.py: what matters
here is the shape of the refusal, not FastAPI's routing.
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import submit_agent_for_review
from app.domain.agents.compliance import Violation
from app.domain.agents.models import Agent
from app.domain.agents.service import AgentService, ComplianceError


def _agent(org_id, owner_id):
    return Agent(
        id=uuid.uuid4(),
        org_id=org_id,
        owner_id=owner_id,
        name="Payroll Reporter",
        description="Reports on payroll",
        status="DRAFT",
    )


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

    # A plain AsyncMock, not an AsyncSession: the route commits the FAILED
    # verdict only for a real session, and this asserts the refusal shape.
    with pytest.raises(HTTPException) as exc:
        await submit_agent_for_review(agent.id, user=builder, service=service, db=AsyncMock())

    assert exc.value.status_code == 400
    assert exc.value.detail["message"] == "This agent does not pass the compliance check."
    assert [v["rule"] for v in exc.value.detail["violations"]] == ["skills", "forbidden_pair"]
    assert exc.value.detail["violations"][0]["message"] == "Agent must have at least one skill."

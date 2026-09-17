from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.service import AgentService, InvalidStateTransitionError


def _agent_with_approved_passport(org_id):
    agent = Agent(id=uuid.uuid4(), org_id=org_id, owner_id=uuid.uuid4(), name="a", description="d")
    agent.passport = AgentPassport(
        id=uuid.uuid4(), agent_id=agent.id, compliance_status="PASSED", lifecycle_state="APPROVED"
    )
    return agent


@pytest.mark.asyncio
async def test_activate_agent_blocked_when_a_requirement_is_unmet():
    org_id = uuid.uuid4()
    agent = _agent_with_approved_passport(org_id)

    agent_repo = MagicMock()
    agent_repo.get_agent = AsyncMock(return_value=agent)
    agent_repo.list_skill_ids = AsyncMock(return_value=["ticketing"])
    agent_repo.session = MagicMock()

    service = AgentService(agent_repo=agent_repo, perm_repo=MagicMock(), skill_repo=MagicMock())

    unmet_status = MagicMock(satisfied=False, label="Jira account")
    with patch(
        "app.domain.agents.service.resolve_requirements",
        new=AsyncMock(return_value=[unmet_status]),
    ):
        with pytest.raises(InvalidStateTransitionError, match="Jira account"):
            await service.activate_agent(agent.id)

    assert agent.passport.lifecycle_state == "APPROVED"


@pytest.mark.asyncio
async def test_activate_agent_succeeds_when_all_requirements_met():
    org_id = uuid.uuid4()
    agent = _agent_with_approved_passport(org_id)

    agent_repo = MagicMock()
    agent_repo.get_agent = AsyncMock(return_value=agent)
    agent_repo.list_skill_ids = AsyncMock(return_value=["ticketing"])
    agent_repo.session = MagicMock()

    service = AgentService(agent_repo=agent_repo, perm_repo=MagicMock(), skill_repo=MagicMock())

    met_status = MagicMock(satisfied=True, label="Jira account")
    with patch(
        "app.domain.agents.service.resolve_requirements",
        new=AsyncMock(return_value=[met_status]),
    ):
        updated = await service.activate_agent(agent.id)

    assert updated.passport.lifecycle_state == "ACTIVE"

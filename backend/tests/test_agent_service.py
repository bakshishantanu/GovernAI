from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.service import (
    AgentService,
    ComplianceError,
    InvalidStateTransitionError,
    SkillNotFoundError,
)


def _service():
    agent_repo = AsyncMock()
    perm_repo = AsyncMock()
    skill_repo = AsyncMock()
    return AgentService(agent_repo, perm_repo, skill_repo), agent_repo, skill_repo


def _agent_with_passport(lifecycle_state: str, owner_id=None) -> Agent:
    agent = Agent(
        id=uuid4(),
        org_id=uuid4(),
        owner_id=owner_id or uuid4(),
        name="Support Bot",
        description="Handles L1 tickets",
        status="DRAFT",
    )
    agent.passport = AgentPassport(
        id=uuid4(),
        agent=agent,
        compliance_status="PENDING",
        lifecycle_state=lifecycle_state,
    )
    return agent


async def test_create_agent_rejects_unknown_skill():
    """Regression: the mock API never validated skill IDs at all, so a typo'd
    skill would silently be accepted instead of failing the request."""
    service, agent_repo, skill_repo = _service()
    skill_repo.get_skill.return_value = None

    with pytest.raises(SkillNotFoundError):
        await service.create_agent(
            org_id=uuid4(),
            owner_id=uuid4(),
            name="Support Bot",
            description="Handles L1 tickets",
            skill_ids=["not_a_real_skill"],
        )

    agent_repo.create_agent.assert_not_called()


async def test_create_agent_links_validated_skills():
    service, agent_repo, skill_repo = _service()
    skill_repo.get_skill.return_value = object()

    agent = await service.create_agent(
        org_id=uuid4(),
        owner_id=uuid4(),
        name="Support Bot",
        description="Handles L1 tickets",
        skill_ids=["ticketing"],
    )

    assert agent.id is not None
    agent_repo.add_skill.assert_awaited_once_with(agent.id, "ticketing")
    agent_repo.create_passport.assert_awaited_once()


async def test_submit_for_review_rejects_non_draft():
    """Regression: PR #8's service had no state guard at all -- an already
    APPROVED or ACTIVE agent could be resubmitted and silently re-approved."""
    service, agent_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="APPROVED")
    agent_repo.get_agent.return_value = agent

    with pytest.raises(InvalidStateTransitionError):
        await service.submit_for_review(agent.id)


async def test_submit_for_review_approves_draft_agent():
    service, agent_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT")
    agent_repo.get_agent.return_value = agent

    passport = await service.submit_for_review(agent.id)

    assert passport.lifecycle_state == "APPROVED"
    assert passport.compliance_status == "PASSED"


async def test_submit_for_review_fails_compliance_without_owner():
    service, agent_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT")
    agent.owner_id = None
    agent_repo.get_agent.return_value = agent

    with pytest.raises(ComplianceError):
        await service.submit_for_review(agent.id)

    assert agent.passport.compliance_status == "FAILED"


async def test_activate_agent_rejects_non_approved():
    service, agent_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT")
    agent_repo.get_agent.return_value = agent

    with pytest.raises(InvalidStateTransitionError):
        await service.activate_agent(agent.id)


async def test_activate_agent_activates_approved_agent():
    service, agent_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="APPROVED")
    agent_repo.get_agent.return_value = agent

    activated = await service.activate_agent(agent.id)

    assert activated.status == "ACTIVE"
    assert activated.passport.lifecycle_state == "ACTIVE"

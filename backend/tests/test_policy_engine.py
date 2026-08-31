import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from app.domain.policies.engine import PolicyEngine, PolicyDecision
from app.domain.agents.models import Agent, AgentPassport
from app.domain.permissions.models import Permission

@pytest.mark.asyncio
async def test_policy_engine_allow():
    agent_repo = AsyncMock()
    perm_repo = AsyncMock()
    policy_repo = AsyncMock()
    
    agent_id = uuid4()
    agent = Agent(id=agent_id, status="ACTIVE")
    agent.passport = AgentPassport(id=uuid4(), lifecycle_state="ACTIVE")
    agent_repo.get_agent.return_value = agent
    
    perm_repo.get_permissions_for_passport.return_value = [
        Permission(permission="ticket.read"),
        Permission(permission="document.search")
    ]
    
    engine = PolicyEngine(agent_repo, perm_repo, policy_repo)
    decision = await engine.evaluate(agent_id, "read_ticket", {"ticket_id": "123"}, "ticket.read")
    
    assert decision.allowed is True
    assert decision.reason == "All checks passed"

@pytest.mark.asyncio
async def test_policy_engine_deny_missing_permission():
    agent_repo = AsyncMock()
    perm_repo = AsyncMock()
    policy_repo = AsyncMock()
    
    agent_id = uuid4()
    agent = Agent(id=agent_id, status="ACTIVE")
    agent.passport = AgentPassport(id=uuid4(), lifecycle_state="ACTIVE")
    agent_repo.get_agent.return_value = agent
    
    perm_repo.get_permissions_for_passport.return_value = [
        Permission(permission="document.search")
    ]
    
    engine = PolicyEngine(agent_repo, perm_repo, policy_repo)
    decision = await engine.evaluate(agent_id, "read_ticket", {"ticket_id": "123"}, "ticket.read")
    
    assert decision.allowed is False
    assert "Missing required permission: ticket.read" in decision.reason

@pytest.mark.asyncio
async def test_policy_engine_deny_suspended_agent():
    agent_repo = AsyncMock()
    perm_repo = AsyncMock()
    policy_repo = AsyncMock()
    
    agent_id = uuid4()
    agent = Agent(id=agent_id, status="SUSPENDED")
    agent.passport = AgentPassport(id=uuid4(), lifecycle_state="SUSPENDED")
    agent_repo.get_agent.return_value = agent
    
    engine = PolicyEngine(agent_repo, perm_repo, policy_repo)
    decision = await engine.evaluate(agent_id, "read_ticket", {"ticket_id": "123"}, "ticket.read")
    
    assert decision.allowed is False
    assert "Agent is not ACTIVE" in decision.reason
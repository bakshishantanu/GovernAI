import pytest
import uuid
from unittest.mock import AsyncMock

from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.kill_switch import KillSwitchService
from app.domain.policies.engine import PolicyEngine

@pytest.mark.asyncio
async def test_kill_switch_integration():
    # 1. Setup mocks
    session = AsyncMock()
    agent_repo = AsyncMock()
    audit_service = AsyncMock()
    event_bus = AsyncMock()
    policy_repo = AsyncMock()
    perm_repo = AsyncMock()
    
    # 2. Setup agent
    agent_id = uuid.uuid4()
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    
    agent = Agent(id=agent_id, org_id=org_id, status="ACTIVE")
    passport = AgentPassport(agent_id=agent_id, lifecycle_state="ACTIVE", permissions=[])
    agent.passport = passport
    
    agent_repo.get_agent.return_value = agent
    
    kill_switch = KillSwitchService(session, agent_repo, audit_service, event_bus)
    
    # 3. Test PolicyEngine before suspension (Assuming no policy restricts it)
    policy_engine = PolicyEngine(agent_repo, perm_repo, policy_repo)
    # Mock policies to return empty for simplicity so it falls through to passport state check
    policy_repo.get_active_policies.return_value = []
    
    decision_before = await policy_engine.evaluate(agent_id, "test_tool", {}, "test:perm")
    # Actually, if the passport has no permissions, it might be denied anyway depending on the implementation.
    # But let's check what happens AFTER suspension.
    
    # 4. Suspend Agent
    await kill_switch.suspend_agent(agent_id, actor_id, org_id, "Security violation")
    
    assert agent.status == "SUSPENDED"
    assert passport.lifecycle_state == "SUSPENDED"
    audit_service.log_agent_suspended.assert_called_once()
    session.commit.assert_called_once()
    
    # 5. Test PolicyEngine after suspension
    decision_after = await policy_engine.evaluate(agent_id, "test_tool", {}, "test:perm")
    assert not decision_after.allowed
    assert decision_after.reason == "Agent is not ACTIVE (current state: SUSPENDED)"

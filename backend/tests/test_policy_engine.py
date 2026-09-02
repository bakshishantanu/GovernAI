import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.domain.policies.engine import PolicyEngine, PolicyDecision
from app.domain.policies.models import Policy, PolicyRule

@pytest.fixture
def mock_agent_repo():
    return AsyncMock()

@pytest.fixture
def mock_perm_repo():
    return AsyncMock()

@pytest.fixture
def mock_policy_repo():
    return AsyncMock()

@pytest.fixture
def policy_engine(mock_agent_repo, mock_perm_repo, mock_policy_repo):
    return PolicyEngine(mock_agent_repo, mock_perm_repo, mock_policy_repo)


@pytest.mark.asyncio
async def test_inactive_agent_blocked(policy_engine, mock_agent_repo):
    # Setup: Agent is in DRAFT state
    mock_agent = MagicMock()
    mock_agent.passport.lifecycle_state = "DRAFT"
    mock_agent_repo.get_agent.return_value = mock_agent

    # Act
    decision = await policy_engine.evaluate(
        agent_id=uuid.uuid4(),
        tool_name="some_tool",
        tool_args={},
        required_permission="some:perm"
    )

    # Assert
    assert decision.allowed is False
    assert "not ACTIVE" in decision.reason


@pytest.mark.asyncio
async def test_missing_permission_blocked(policy_engine, mock_agent_repo, mock_perm_repo):
    # Setup: Agent is ACTIVE, but missing the specific permission
    mock_agent = MagicMock()
    mock_agent.passport.lifecycle_state = "ACTIVE"
    mock_agent_repo.get_agent.return_value = mock_agent

    # Agent only has "other:perm", but the tool requires "db:read"
    mock_perm = MagicMock()
    mock_perm.permission = "other:perm"
    mock_perm_repo.get_permissions_for_passport.return_value = [mock_perm]

    decision = await policy_engine.evaluate(
        agent_id=uuid.uuid4(),
        tool_name="sql_query",
        tool_args={},
        required_permission="db:read"
    )

    assert decision.allowed is False
    assert "Missing required permission" in decision.reason


@pytest.mark.asyncio
async def test_destructive_sql_policy_blocked(policy_engine, mock_agent_repo, mock_perm_repo, mock_policy_repo):
    # Setup: Agent is ACTIVE and HAS the permission
    mock_agent = MagicMock()
    mock_agent.passport.lifecycle_state = "ACTIVE"
    mock_agent_repo.get_agent.return_value = mock_agent

    mock_perm = MagicMock()
    mock_perm.permission = "db:read"
    mock_perm_repo.get_permissions_for_passport.return_value = [mock_perm]

    # Setup: The database has a rule blocking "DROP"
    rule = PolicyRule(rule_type="sql_blocklist", enabled=True, config={"keywords": ["DROP", "DELETE"]})
    policy = Policy(name="Safe SQL", enabled=True, rules=[rule])
    mock_policy_repo.get_active_policies_for_org.return_value = [policy]

    # Act: Agent attempts to run a DROP TABLE command
    decision = await policy_engine.evaluate(
        agent_id=uuid.uuid4(),
        tool_name="sql_query",
        tool_args={"query": "DROP TABLE users;"},
        required_permission="db:read"
    )

    # Assert: Should be blocked by the policy engine!
    assert decision.allowed is False
    assert "Disallowed keyword 'DROP' detected" in decision.reason


@pytest.mark.asyncio
async def test_valid_action_allowed(policy_engine, mock_agent_repo, mock_perm_repo, mock_policy_repo):
    # Setup: ACTIVE agent, HAS permission, NO blocked keywords in query
    mock_agent = MagicMock()
    mock_agent.passport.lifecycle_state = "ACTIVE"
    mock_agent_repo.get_agent.return_value = mock_agent

    mock_perm = MagicMock()
    mock_perm.permission = "db:read"
    mock_perm_repo.get_permissions_for_passport.return_value = [mock_perm]

    rule = PolicyRule(rule_type="sql_blocklist", enabled=True, config={"keywords": ["DROP"]})
    policy = Policy(name="Safe SQL", enabled=True, rules=[rule])
    mock_policy_repo.get_active_policies_for_org.return_value = [policy]

    # Act: Safe query
    decision = await policy_engine.evaluate(
        agent_id=uuid.uuid4(),
        tool_name="sql_query",
        tool_args={"query": "SELECT * FROM tickets;"},
        required_permission="db:read"
    )

    # Assert: Should be allowed!
    assert decision.allowed is True
    assert "checks passed" in decision.reason
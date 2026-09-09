import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.domain.agents.models import Agent, AgentPassport
from app.domain.auth.rbac import require_admin
from app.api.v1.agents import (
    get_agent,
    kill_agent,
    activate_agent,
)
from app.api.v1.costs import cost_summary

@pytest.fixture
def org_id():
    return uuid.uuid4()

@pytest.fixture
def admin_user(org_id):
    return CurrentUser(id=uuid.uuid4(), org_id=org_id, role="admin")

@pytest.fixture
def builder_user(org_id):
    return CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")

@pytest.fixture
def assigned_builder(org_id):
    return CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")

def make_agent(agent_id, org_id, owner_id, assigned_user_id=None, status="ACTIVE", lifecycle="ACTIVE"):
    now = datetime.now(timezone.utc)
    agent = Agent(
        id=agent_id,
        org_id=org_id,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
        name="Test Agent",
        description="A test agent",
        status=status,
        created_at=now,
        updated_at=now,
    )
    passport = AgentPassport(
        id=uuid.uuid4(),
        agent_id=agent_id,
        agent=agent,
        compliance_status="PASSED",
        lifecycle_state=lifecycle,
        created_at=now,
        updated_at=now,
    )
    agent.passport = passport
    return agent

# 1. Kill switch / Kill agent endpoint is ADMIN ONLY
@pytest.mark.asyncio
async def test_kill_agent_admin(admin_user):
    agent_id = uuid.uuid4()
    agent_service = AsyncMock()
    kill_switch_service = AsyncMock()
    
    agent = make_agent(agent_id, admin_user.org_id, admin_user.id, status="SUSPENDED", lifecycle="SUSPENDED")
    agent_service.agent_repo.get_agent.return_value = agent
    
    res = await kill_agent(
        agent_id=agent_id, 
        reason="Admin emergency stop", 
        user=admin_user, 
        service=agent_service, 
        kill_switch=kill_switch_service
    )
    assert res.data.status == "SUSPENDED"

@pytest.mark.asyncio
async def test_kill_agent_forbidden_for_builder(builder_user):
    with pytest.raises(HTTPException) as exc:
        await require_admin(builder_user)
    assert exc.value.status_code == 403

# 2. Builder cannot access another builder's agent (404)
@pytest.mark.asyncio
async def test_builder_cannot_access_another_builder_agent(builder_user):
    agent_id = uuid.uuid4()
    other_builder_id = uuid.uuid4()
    agent = make_agent(agent_id, builder_user.org_id, other_builder_id)

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await get_agent(agent_id=agent_id, service=agent_service, user=builder_user)

    assert exc.value.status_code == 404

# 3. Builder cannot access unrelated agent (neither owner nor assigned) (404)
@pytest.mark.asyncio
async def test_builder_cannot_access_unrelated_agent(assigned_builder):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, assigned_builder.org_id, uuid.uuid4(), assigned_user_id=None)

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await get_agent(agent_id=agent_id, service=agent_service, user=assigned_builder)

    assert exc.value.status_code == 404

# 4. Builder CAN access assigned agent (200)
@pytest.mark.asyncio
async def test_builder_can_access_assigned_agent(assigned_builder):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, assigned_builder.org_id, uuid.uuid4(), assigned_user_id=assigned_builder.id)

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    res = await get_agent(agent_id=agent_id, service=agent_service, user=assigned_builder)
    assert res.data.id == agent_id

# 5. Admin can access ANY agent (200)
@pytest.mark.asyncio
async def test_admin_can_access_any_agent(admin_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, admin_user.org_id, uuid.uuid4(), assigned_user_id=uuid.uuid4())

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    res = await get_agent(agent_id=agent_id, service=agent_service, user=admin_user)
    assert res.data.id == agent_id

# 6. Request creation: Builder CAN create agent requests (merged permission)
@pytest.mark.asyncio
async def test_builder_can_create_agent_request(builder_user):
    from app.api.v1.agent_requests import create_request
    from app.api.schemas.agent_requests import AgentRequestCreate
    from app.domain.agent_requests.models import AgentRequest

    service = AsyncMock()
    req_id = uuid.uuid4()
    service.create_request.return_value = AgentRequest(
        id=req_id,
        org_id=builder_user.org_id,
        requester_id=builder_user.id,
        title="New Request",
        description="Desc",
        requested_skills=[],
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    payload = AgentRequestCreate(title="New Request", description="Desc", requested_skills=[])
    res = await create_request(request=payload, service=service, user=builder_user)
    assert res.id == req_id
    assert res.requester_id == builder_user.id

# 7. Listing agents: Builder sees own + assigned agents (OR filter)
@pytest.mark.asyncio
async def test_builder_sees_own_and_assigned_agents(builder_user):
    from app.api.v1.agents import list_agents

    service = AsyncMock()
    service.agent_repo.list_agents_by_org.return_value = []
    service.agent_repo.count_agents_by_org.return_value = 0
    db = AsyncMock()

    await list_agents(user=builder_user, service=service, db=db, limit=50, offset=0)
    service.agent_repo.list_agents_by_org.assert_awaited_once_with(
        builder_user.org_id,
        limit=50,
        offset=0,
        owner_id=builder_user.id,
        assigned_user_id=builder_user.id,
    )
    service.agent_repo.count_agents_by_org.assert_awaited_once_with(
        builder_user.org_id,
        owner_id=builder_user.id,
        assigned_user_id=builder_user.id,
    )

# 8. Execution access: Builder can execute assigned agent even if not owner
@pytest.mark.asyncio
async def test_builder_can_execute_assigned_agent(assigned_builder):
    from app.api.v1.executions import create_and_run_execution
    from app.api.schemas.execution import ExecutionCreate
    from app.domain.executions.models import Execution
    from fastapi import BackgroundTasks

    agent_id = uuid.uuid4()
    other_owner = uuid.uuid4()
    agent = make_agent(agent_id, assigned_builder.org_id, other_owner, assigned_user_id=assigned_builder.id, status="ACTIVE", lifecycle="ACTIVE")

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    exec_service = AsyncMock()
    mock_exec = Execution(
        id=uuid.uuid4(),
        agent_id=agent_id,
        org_id=assigned_builder.org_id,
        goal="Do work",
        status="RUNNING",
    )
    exec_service.create_execution.return_value = mock_exec

    db = AsyncMock()
    llm_service = AsyncMock()
    bg_tasks = BackgroundTasks()

    payload = ExecutionCreate(agent_id=agent_id, goal="Do work")
    res = await create_and_run_execution(
        payload=payload,
        background_tasks=bg_tasks,
        current_user=assigned_builder,
        db=db,
        agent_service=agent_service,
        exec_service=exec_service,
        llm_service=llm_service,
    )
    assert res.data.id == mock_exec.id

# 9. Cost summary: Scoped to builder_id for agent_builder
@pytest.mark.asyncio
async def test_builder_gets_scoped_cost_summary(builder_user):
    repo = AsyncMock()
    repo.get_costs_summary.return_value = []
    res = await cost_summary(user=builder_user, repo=repo)
    repo.get_costs_summary.assert_awaited_once_with(builder_user.org_id, builder_id=builder_user.id)
    assert res.data.total_cost_usd == 0.0

# 10. Agent activation: Builder can activate their own agent
@pytest.mark.asyncio
async def test_builder_can_activate_own_agent(builder_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, builder_user.org_id, builder_user.id, status="ACTIVE", lifecycle="ACTIVE")

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent
    agent_service.activate_agent.return_value = agent

    res = await activate_agent(
        agent_id=agent_id,
        user=builder_user,
        service=agent_service,
    )
    assert res.data.id == agent_id
    agent_service.activate_agent.assert_awaited_once_with(agent_id)

# 11. Agent activation: Builder CANNOT activate another builder's agent (403)
@pytest.mark.asyncio
async def test_builder_cannot_activate_another_agent(builder_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, builder_user.org_id, uuid.uuid4())
    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await activate_agent(
            agent_id=agent_id,
            user=builder_user,
            service=agent_service,
        )
    assert exc.value.status_code == 403

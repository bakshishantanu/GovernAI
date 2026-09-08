import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import (
    activate_agent,
    get_agent,
    kill_agent,
)
from app.api.v1.costs import cost_summary
from app.api.v1.policies import list_policies
from app.domain.agents.models import Agent, AgentPassport
from app.domain.auth.rbac import require_admin, require_builder_or_admin


def make_db():
    """A session stub for the routes that enrich a response with its skills.

    `origin/main` added a per-request skills lookup to every route returning an
    AgentResponse, so these direct calls now need a session that can answer one.
    Returning no rows is correct here: these tests assert role scoping, not
    which skills come back.
    """
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    db.execute.return_value = result
    return db


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
def standard_user(org_id):
    return CurrentUser(id=uuid.uuid4(), org_id=org_id, role="user")


def make_agent(
    agent_id, org_id, owner_id, assigned_user_id=None, status="ACTIVE", lifecycle="ACTIVE"
):
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

    agent = make_agent(
        agent_id, admin_user.org_id, admin_user.id, status="SUSPENDED", lifecycle="SUSPENDED"
    )
    agent_service.agent_repo.get_agent.return_value = agent

    res = await kill_agent(
        agent_id=agent_id,
        reason="Admin emergency stop",
        user=admin_user,
        service=agent_service,
        kill_switch=kill_switch_service,
        db=make_db(),
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
        await get_agent(agent_id=agent_id, service=agent_service, user=builder_user, db=make_db())

    assert exc.value.status_code == 404


# 3. User cannot access unassigned agent (404)
@pytest.mark.asyncio
async def test_user_cannot_access_unassigned_agent(standard_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, standard_user.org_id, uuid.uuid4(), assigned_user_id=None)

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await get_agent(agent_id=agent_id, service=agent_service, user=standard_user, db=make_db())

    assert exc.value.status_code == 404


# 4. User CAN access assigned agent (200)
@pytest.mark.asyncio
async def test_user_can_access_assigned_agent(standard_user):
    agent_id = uuid.uuid4()
    agent = make_agent(
        agent_id, standard_user.org_id, uuid.uuid4(), assigned_user_id=standard_user.id
    )

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    res = await get_agent(
        agent_id=agent_id, service=agent_service, user=standard_user, db=make_db()
    )
    assert res.data.id == agent_id


# 5. Admin can access ANY agent (200)
@pytest.mark.asyncio
async def test_admin_can_access_any_agent(admin_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, admin_user.org_id, uuid.uuid4(), assigned_user_id=uuid.uuid4())

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    res = await get_agent(agent_id=agent_id, service=agent_service, user=admin_user, db=make_db())
    assert res.data.id == agent_id


# 6. Policy access: User is blocked from listing policies (403 via require_builder_or_admin)
@pytest.mark.asyncio
async def test_user_cannot_list_policies(standard_user):
    with pytest.raises(HTTPException) as exc:
        await require_builder_or_admin(standard_user)
    assert exc.value.status_code == 403


# 7. Policy access: Builder CAN list policies (200)
@pytest.mark.asyncio
async def test_builder_can_list_policies(builder_user):
    assert await require_builder_or_admin(builder_user) is builder_user
    repo = AsyncMock()
    repo.get_policies_for_org.return_value = []
    res = await list_policies(current_user=builder_user, repo=repo)
    assert res.data == []


# 8. Cost access: User is blocked from listing costs (403 via require_builder_or_admin)
@pytest.mark.asyncio
async def test_user_cannot_list_costs(standard_user):
    with pytest.raises(HTTPException) as exc:
        await require_builder_or_admin(standard_user)
    assert exc.value.status_code == 403


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
    agent = make_agent(
        agent_id, builder_user.org_id, builder_user.id, status="ACTIVE", lifecycle="ACTIVE"
    )

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent
    agent_service.activate_agent.return_value = agent

    res = await activate_agent(
        agent_id=agent_id,
        user=builder_user,
        service=agent_service,
        db=make_db(),
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
            db=make_db(),
        )
    assert exc.value.status_code == 403

"""Two-role governance tests (file name kept for history; the model itself
collapsed from three roles to two — admin and user — with agent_builder's
capabilities merged into user. See D-052 in .project-memory/DECISIONS.md."""

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
def standard_user(org_id):
    return CurrentUser(id=uuid.uuid4(), org_id=org_id, role="agent_builder")


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
async def test_kill_agent_forbidden_for_a_plain_user(standard_user):
    with pytest.raises(HTTPException) as exc:
        await require_admin(standard_user)
    assert exc.value.status_code == 403


# 2. A user cannot access an agent they neither own nor are assigned (404)
@pytest.mark.asyncio
async def test_user_cannot_access_someone_elses_owned_agent(standard_user):
    agent_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    agent = make_agent(agent_id, standard_user.org_id, other_owner_id)

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await get_agent(agent_id=agent_id, service=agent_service, user=standard_user, db=make_db())

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


# 4b. User CAN access an agent they own even without being assigned (the
# OR-ownership fix this merge required — the two are independent, not
# mutually exclusive, for the same person post-merge).
@pytest.mark.asyncio
async def test_user_can_access_owned_agent_they_built(standard_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, standard_user.org_id, standard_user.id, assigned_user_id=None)

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


# 6. Policy access: a user CAN list policies now (agent_builder's read
# access merged in) — the old three-role model blocked plain "user" here.
@pytest.mark.asyncio
async def test_user_can_list_policies(standard_user):
    assert await require_builder_or_admin(standard_user) is standard_user
    repo = AsyncMock()
    repo.get_policies_for_org.return_value = []
    res = await list_policies(current_user=standard_user, repo=repo)
    assert res.data == []


# 7. Cost access: a user CAN list costs now (agent_builder's access merged
# in, per the confirmed decision to widen this) — scoped to their own agents.
@pytest.mark.asyncio
async def test_user_gets_scoped_cost_summary(standard_user):
    repo = AsyncMock()
    repo.get_costs_summary.return_value = []
    res = await cost_summary(user=standard_user, window="all", repo=repo)
    repo.get_costs_summary.assert_awaited_once_with(
        standard_user.org_id, visible_to_user_id=standard_user.id, since=None
    )
    assert res.data.total_cost_usd == 0.0


@pytest.mark.asyncio
async def test_admin_gets_unscoped_cost_summary(admin_user):
    repo = AsyncMock()
    repo.get_costs_summary.return_value = []
    res = await cost_summary(user=admin_user, window="all", repo=repo)
    repo.get_costs_summary.assert_awaited_once_with(
        admin_user.org_id, visible_to_user_id=None, since=None
    )
    assert res.data.total_cost_usd == 0.0


# 8. Agent activation: a user can activate their own (owned) agent
@pytest.mark.asyncio
async def test_user_can_activate_own_agent(standard_user):
    agent_id = uuid.uuid4()
    agent = make_agent(
        agent_id, standard_user.org_id, standard_user.id, status="ACTIVE", lifecycle="ACTIVE"
    )

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent
    agent_service.activate_agent.return_value = agent

    res = await activate_agent(
        agent_id=agent_id,
        user=standard_user,
        service=agent_service,
        db=make_db(),
    )
    assert res.data.id == agent_id
    agent_service.activate_agent.assert_awaited_once_with(agent_id)


# 9. Agent activation: a user CANNOT activate someone else's agent (403) —
# and, critically, not even one merely *assigned* to them: activation is an
# owner-only build action, deliberately not OR'd with assignment.
@pytest.mark.asyncio
async def test_user_cannot_activate_another_users_owned_agent(standard_user):
    agent_id = uuid.uuid4()
    agent = make_agent(agent_id, standard_user.org_id, uuid.uuid4())
    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await activate_agent(
            agent_id=agent_id,
            user=standard_user,
            service=agent_service,
            db=make_db(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_activate_an_agent_only_assigned_to_them(standard_user):
    agent_id = uuid.uuid4()
    agent = make_agent(
        agent_id, standard_user.org_id, uuid.uuid4(), assigned_user_id=standard_user.id
    )
    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await activate_agent(
            agent_id=agent_id,
            user=standard_user,
            service=agent_service,
            db=make_db(),
        )
    assert exc.value.status_code == 403

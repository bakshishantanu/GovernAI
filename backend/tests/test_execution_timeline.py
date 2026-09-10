from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.executions import get_execution_timeline
from app.domain.agents.models import Agent
from app.domain.audit.models import AuditEvent
from app.domain.costs.models import CostEvent
from app.domain.executions.models import Execution


@pytest.fixture
def current_user():
    return CurrentUser(id=uuid.uuid4(), org_id=uuid.uuid4(), role="admin")


def _execution(current_user, **overrides) -> Execution:
    return Execution(
        id=overrides.get("id", uuid.uuid4()),
        agent_id=overrides.get("agent_id", uuid.uuid4()),
        org_id=overrides.get("org_id", current_user.org_id),
        goal="g",
        status="COMPLETED",
    )


@pytest.mark.asyncio
async def test_timeline_404s_for_an_execution_in_another_org(current_user):
    exec_service = AsyncMock()
    exec_service.get_execution.return_value = _execution(current_user, org_id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc:
        await get_execution_timeline(
            execution_id=uuid.uuid4(),
            current_user=current_user,
            exec_service=exec_service,
            cost_repo=AsyncMock(),
            db=AsyncMock(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_timeline_403s_for_a_user_who_neither_owns_nor_is_assigned_the_agent(current_user):
    other_user = CurrentUser(id=uuid.uuid4(), org_id=current_user.org_id, role="agent_builder")
    execution = _execution(other_user)
    agent = Agent(
        id=execution.agent_id,
        org_id=other_user.org_id,
        owner_id=uuid.uuid4(),  # someone else
        name="a",
        description="d",
        status="ACTIVE",
    )

    exec_service = AsyncMock()
    exec_service.get_execution.return_value = execution
    exec_service.exec_repo.session.get.return_value = agent

    with pytest.raises(HTTPException) as exc:
        await get_execution_timeline(
            execution_id=execution.id,
            current_user=other_user,
            exec_service=exec_service,
            cost_repo=AsyncMock(),
            db=AsyncMock(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_timeline_merges_governance_and_cost_history_chronologically(current_user, monkeypatch):
    execution = _execution(current_user)
    t0 = datetime.now(timezone.utc)

    allowed_event = AuditEvent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        actor_type="agent",
        actor_id=uuid.uuid4(),
        execution_id=execution.id,
        action="tool_call",
        tool="search_tickets",
        policy_decision="ALLOW",
        reason="All policies passed",
        timestamp=t0,
    )
    denied_event = AuditEvent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        actor_type="agent",
        actor_id=uuid.uuid4(),
        execution_id=execution.id,
        action="tool_call",
        tool="database.customer.export",
        policy_decision="DENY",
        reason="Policy 'Export Restriction': tool is on the deny list.",
        timestamp=t0 + timedelta(seconds=1),
    )
    cost_event = CostEvent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        agent_id=uuid.uuid4(),
        execution_id=execution.id,
        event_type="LLM_CALL",
        model="openai/gpt-oss-20b",
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        cost_usd=0.0009,
        timestamp=t0 + timedelta(milliseconds=500),
    )

    exec_service = AsyncMock()
    exec_service.get_execution.return_value = execution
    exec_service.exec_repo.session.get.return_value = None

    audit_repo = AsyncMock()
    # Repository returns newest-first, matching the real ordering.
    audit_repo.get_events_for_org.return_value = [denied_event, allowed_event]
    monkeypatch.setattr("app.api.v1.executions.AuditRepository", lambda db: audit_repo)

    cost_repo = AsyncMock()
    cost_repo.list_costs.return_value = [cost_event]

    response = await get_execution_timeline(
        execution_id=execution.id,
        current_user=current_user,
        exec_service=exec_service,
        cost_repo=cost_repo,
        db=AsyncMock(),
    )

    audit_repo.get_events_for_org.assert_awaited_once_with(
        org_id=current_user.org_id, execution_id=execution.id, limit=1000
    )
    cost_repo.list_costs.assert_awaited_once_with(
        org_id=current_user.org_id, execution_id=execution.id, limit=1000
    )

    timeline = response.data
    assert timeline.execution_id == execution.id
    # Oldest first, despite the repository handing back newest-first.
    assert [e.id for e in timeline.governance_events] == [allowed_event.id, denied_event.id]
    assert timeline.governance_events[1].policy_decision == "DENY"
    assert timeline.cost_events[0].total_tokens == 120


@pytest.mark.asyncio
async def test_timeline_empty_run_returns_empty_lists_not_an_error(current_user):
    """A run with no tool calls and no LLM calls yet (or ever) is a real,
    valid state -- not an error."""
    execution = _execution(current_user)

    exec_service = AsyncMock()
    exec_service.get_execution.return_value = execution
    exec_service.exec_repo.session.get.return_value = None

    audit_repo = AsyncMock()
    audit_repo.get_events_for_org.return_value = []

    import app.api.v1.executions as executions_module

    original = executions_module.AuditRepository
    executions_module.AuditRepository = lambda db: audit_repo
    try:
        cost_repo = AsyncMock()
        cost_repo.list_costs.return_value = []

        response = await get_execution_timeline(
            execution_id=execution.id,
            current_user=current_user,
            exec_service=exec_service,
            cost_repo=cost_repo,
            db=AsyncMock(),
        )
    finally:
        executions_module.AuditRepository = original

    assert response.data.governance_events == []
    assert response.data.cost_events == []

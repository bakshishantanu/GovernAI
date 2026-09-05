from __future__ import annotations
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from app.domain.agents.models import Agent, AgentPassport
from app.domain.executions.models import Execution
from app.domain.executions.service import ExecutionService
from app.api.v1.executions import (
    create_and_run_execution,
    list_executions,
    get_execution_detail,
    cancel_execution,
)
from app.api.schemas.execution import ExecutionCreate
from app.api.schemas.auth import CurrentUser
from app.api.execution_runner import run_execution
from fastapi import BackgroundTasks, HTTPException


@pytest.fixture
def current_user():
    return CurrentUser(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        role="admin",
    )


@pytest.fixture
def active_agent(current_user):
    agent = Agent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        owner_id=current_user.id,
        name="Security Auditor",
        description="Analyzes security logs",
        status="ACTIVE",
    )
    agent.passport = AgentPassport(
        id=uuid.uuid4(),
        agent=agent,
        compliance_status="APPROVED",
        lifecycle_state="ACTIVE",
    )
    return agent


@pytest.mark.asyncio
async def test_execution_fails_if_agent_not_found(current_user):
    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = None

    payload = ExecutionCreate(agent_id=uuid.uuid4(), goal="Run security scan")

    with pytest.raises(HTTPException) as exc:
        await create_and_run_execution(
            payload=payload,
            current_user=current_user,
            db=AsyncMock(),
            agent_service=agent_service,
            exec_service=AsyncMock(),
            llm_service=AsyncMock(),
            background_tasks=BackgroundTasks(),
        )

    assert exc.value.status_code == 404
    assert "Agent not found" in exc.value.detail


@pytest.mark.asyncio
async def test_execution_fails_if_agent_in_draft_state(current_user):
    draft_agent = Agent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        owner_id=current_user.id,
        name="Draft Bot",
        description="Under review",
        status="DRAFT",
    )
    draft_agent.passport = AgentPassport(
        id=uuid.uuid4(),
        agent=draft_agent,
        compliance_status="PENDING",
        lifecycle_state="DRAFT",
    )

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = draft_agent

    payload = ExecutionCreate(agent_id=draft_agent.id, goal="Run task")

    with pytest.raises(HTTPException) as exc:
        await create_and_run_execution(
            payload=payload,
            current_user=current_user,
            db=AsyncMock(),
            agent_service=agent_service,
            exec_service=AsyncMock(),
            llm_service=AsyncMock(),
            background_tasks=BackgroundTasks(),
        )

    assert exc.value.status_code == 400
    assert "Agent must be in 'ACTIVE' state" in exc.value.detail


@pytest.mark.asyncio
async def test_the_endpoint_returns_before_the_run_happens(current_user, active_agent):
    """The whole point of the change: the caller gets an id immediately, so it
    can open the stream and watch the run rather than waiting for the result."""
    exec_id = uuid.uuid4()
    queued = Execution(
        id=exec_id,
        agent_id=active_agent.id,
        org_id=current_user.org_id,
        goal="Count open tickets",
        status="PENDING",
    )

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = active_agent

    exec_service = AsyncMock()
    exec_service.create_execution.return_value = queued

    background_tasks = BackgroundTasks()
    payload = ExecutionCreate(agent_id=active_agent.id, goal="Count open tickets")

    response = await create_and_run_execution(
        payload=payload,
        current_user=current_user,
        db=AsyncMock(),
        agent_service=agent_service,
        exec_service=exec_service,
        llm_service=AsyncMock(),
        background_tasks=background_tasks,
    )

    assert response.data.id == exec_id

    # The run was queued, not executed.
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is run_execution
    assert background_tasks.tasks[0].kwargs["execution_id"] == exec_id

    # And the endpoint itself did none of the running.
    exec_service.mark_running.assert_not_awaited()
    exec_service.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_row_is_committed_before_the_task_is_queued(current_user, active_agent):
    """The background run opens its own session, so the row must already be
    visible to it. Committing after queueing would race."""
    db = AsyncMock()
    exec_id = uuid.uuid4()

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = active_agent

    exec_service = AsyncMock()
    exec_service.create_execution.return_value = Execution(
        id=exec_id,
        agent_id=active_agent.id,
        org_id=current_user.org_id,
        goal="g",
        status="PENDING",
    )

    await create_and_run_execution(
        payload=ExecutionCreate(agent_id=active_agent.id, goal="g"),
        current_user=current_user,
        db=db,
        agent_service=agent_service,
        exec_service=exec_service,
        llm_service=AsyncMock(),
        background_tasks=BackgroundTasks(),
    )

    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_kill_switch_cancels_running_execution(current_user):
    exec_id = uuid.uuid4()
    cancelled_exec = Execution(
        id=exec_id,
        agent_id=uuid.uuid4(),
        org_id=current_user.org_id,
        goal="Long running query",
        status="CANCELLED",
        error="Manually terminated by user (Kill Switch)",
    )

    exec_service = AsyncMock()
    exec_service.cancel.return_value = cancelled_exec

    response = await cancel_execution(
        execution_id=exec_id,
        current_user=current_user,
        db=AsyncMock(),
        exec_service=exec_service,
    )

    assert response.data.id == exec_id
    assert response.data.status == "CANCELLED"
    assert "Kill Switch" in response.data.error
    exec_service.cancel.assert_awaited_once_with(execution_id=exec_id, org_id=current_user.org_id)

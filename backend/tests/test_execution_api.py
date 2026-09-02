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
from fastapi import HTTPException


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
            policy_engine=AsyncMock(),
            audit_service=AsyncMock(),
            cost_service=AsyncMock(),
            skill_registry=AsyncMock(),
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
            policy_engine=AsyncMock(),
            audit_service=AsyncMock(),
            cost_service=AsyncMock(),
            skill_registry=AsyncMock(),
        )

    assert exc.value.status_code == 400
    assert "Agent must be in 'ACTIVE' state" in exc.value.detail


@pytest.mark.asyncio
async def test_successful_execution_flow(current_user, active_agent):
    exec_id = uuid.uuid4()
    mock_execution = Execution(
        id=exec_id,
        agent_id=active_agent.id,
        org_id=current_user.org_id,
        goal="Count open tickets",
        status="COMPLETED",
        result="Found 5 open tickets.",
    )

    agent_service = AsyncMock()
    agent_service.agent_repo.get_agent.return_value = active_agent

    exec_service = AsyncMock()
    exec_service.create_execution.return_value = mock_execution
    exec_service.get_execution.return_value = mock_execution

    payload = ExecutionCreate(agent_id=active_agent.id, goal="Count open tickets")

    with patch("app.api.v1.executions.load_agent_tools", new_callable=AsyncMock) as mock_load_tools, \
         patch("app.api.v1.executions.run_agent", new_callable=AsyncMock) as mock_run_agent:
        mock_load_tools.return_value = []
        mock_run_agent.return_value = {
            "final_answer": "Found 5 open tickets.",
            "steps": 1,
            "stopped_reason": "completed",
        }

        response = await create_and_run_execution(
            payload=payload,
            current_user=current_user,
            db=AsyncMock(),
            agent_service=agent_service,
            exec_service=exec_service,
            llm_service=AsyncMock(),
            policy_engine=AsyncMock(),
            audit_service=AsyncMock(),
            cost_service=AsyncMock(),
            skill_registry=AsyncMock(),
        )

        assert response.data.id == exec_id
        assert response.data.status == "COMPLETED"
        assert response.data.result == "Found 5 open tickets."
        exec_service.mark_running.assert_awaited_once_with(exec_id)
        exec_service.complete.assert_awaited_once_with(exec_id, result="Found 5 open tickets.")


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

from __future__ import annotations
import json
import asyncio
from uuid import UUID
from typing import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_agent_service,
    get_execution_service,
    get_llm_service,
    get_policy_engine,
    get_audit_service,
    get_cost_service,
    get_skill_registry,
    get_budget_guard,
)
from app.domain.auth.middleware import get_current_user
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.execution import ExecutionCreate, ExecutionResponse
from app.domain.agents.service import AgentService
from app.domain.executions.service import ExecutionService
from app.domain.policies.engine import PolicyEngine
from app.domain.audit.service import AuditService
from app.domain.costs.service import CostService
from app.domain.governance.budget import BudgetGuard
from app.domain.skills.registry import SkillRegistry
from app.runtime.llm.service import LLMService
from app.runtime.agent_loader import load_agent_tools
from app.api.execution_runner import run_execution

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post(
    "/",
    response_model=Envelope[ExecutionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_and_run_execution(
    payload: ExecutionCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
    exec_service: ExecutionService = Depends(get_execution_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Start an agent run and return straight away.

    Returns **202 Accepted** with the execution id. The run itself happens after
    the response is sent, so the caller can immediately open
    `GET /executions/{id}/stream` and watch each tool call, allow and denial as
    it happens.

    This used to `await` the whole run before responding, which meant the run
    was already over by the time the caller had an id — the live view had
    nothing left to show.
    """
    agent = await agent_service.agent_repo.get_agent(payload.agent_id)
    if not agent or agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in your organization",
        )

    if not agent.passport or agent.passport.lifecycle_state != "ACTIVE":
        state = agent.passport.lifecycle_state if agent.passport else "UNKNOWN"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Agent cannot be executed: lifecycle state is '{state}'. "
                "Agent must be in 'ACTIVE' state."
            ),
        )

    execution = await exec_service.create_execution(
        agent_id=agent.id,
        org_id=current_user.org_id,
        goal=payload.goal,
    )
    # Committed before the task is queued: the run opens its own session and
    # must be able to see this row.
    await db.commit()
    await db.refresh(execution)

    background_tasks.add_task(
        run_execution,
        execution_id=execution.id,
        agent_id=agent.id,
        org_id=current_user.org_id,
        goal=payload.goal,
        system_prompt=payload.system_prompt,
        max_steps=payload.max_steps,
        llm_service=llm_service,
    )

    return Envelope(data=execution)


@router.get("/", response_model=Envelope[list[ExecutionResponse]])
async def list_executions(
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    List all execution runs for the current user's organization (newest first).
    """
    executions = await exec_service.list_executions_for_org(current_user.org_id)
    return Envelope(data=executions)


@router.get("/{execution_id}", response_model=Envelope[ExecutionResponse])
async def get_execution_detail(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    Get detailed execution progress, status, and final answer.
    """
    execution = await exec_service.get_execution(execution_id)
    if not execution or execution.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )
    return Envelope(data=execution)


@router.post("/{execution_id}/cancel", response_model=Envelope[ExecutionResponse])
async def cancel_execution(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    Emergency Kill Switch: Immediately cancel/terminate an active execution.
    """
    try:
        updated = await exec_service.cancel(execution_id=execution_id, org_id=current_user.org_id)
        await db.commit()
        return Envelope(data=updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/{execution_id}/stream")
async def stream_execution_events(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    Server-Sent Events (SSE) live stream of execution status.
    """
    execution = await exec_service.get_execution(execution_id)
    if not execution or execution.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        # Stream initial status
        yield f"event: status\ndata: {json.dumps({'status': execution.status, 'goal': execution.goal})}\n\n"

        # Poll state until completion or cancel
        for _ in range(30):
            await asyncio.sleep(1)
            current = await exec_service.get_execution(execution_id)
            if not current:
                break

            data = {
                "status": current.status,
                "result": current.result,
                "error": current.error,
                "completed_at": current.completed_at.isoformat() if current.completed_at else None,
            }
            yield f"event: update\ndata: {json.dumps(data)}\n\n"

            if current.status in ("COMPLETED", "FAILED", "CANCELLED", "TERMINATED"):
                yield f"event: done\ndata: {json.dumps({'status': current.status})}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

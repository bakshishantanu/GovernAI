from __future__ import annotations
import json
import asyncio
from uuid import UUID
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
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
from app.domain.skills.registry import SkillRegistry
from app.runtime.llm.service import LLMService
from app.runtime.agent_loader import load_agent_tools
from app.runtime.agent_graph import run_agent

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("/", response_model=Envelope[ExecutionResponse], status_code=status.HTTP_201_CREATED)
async def create_and_run_execution(
    payload: ExecutionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
    exec_service: ExecutionService = Depends(get_execution_service),
    llm_service: LLMService = Depends(get_llm_service),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    audit_service: AuditService = Depends(get_audit_service),
    cost_service: CostService = Depends(get_cost_service),
    skill_registry: SkillRegistry = Depends(get_skill_registry),
):
    """
    Trigger an AI Agent execution.
    1. Validates agent ownership and ACTIVE lifecycle state.
    2. Loads bound skills and tools for the agent.
    3. Runs the agent reasoning loop guarded by Governance Middleware.
    4. Records execution status, audit events, and token costs in PostgreSQL.
    """
    # 1. Fetch & validate agent
    agent = await agent_service.get_agent(payload.agent_id)
    if not agent or agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in your organization",
        )

    if not agent.passport or agent.passport.lifecycle_state != "ACTIVE":
        state = agent.passport.lifecycle_state if agent.passport else "UNKNOWN"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent cannot be executed: lifecycle state is '{state}'. Agent must be in 'ACTIVE' state.",
        )

    # 2. Create execution record in DB
    execution = await exec_service.create_execution(
        agent_id=agent.id,
        org_id=current_user.org_id,
        goal=payload.goal,
    )
    await db.commit()
    await db.refresh(execution)

    # 3. Load agent-specific tools
    tools = await load_agent_tools(
        agent_id=agent.id,
        agent_repo=agent_service.agent_repo,
        skill_registry=skill_registry,
    )

    # 4. Mark execution as RUNNING and execute the agent graph
    await exec_service.mark_running(execution.id)
    await db.commit()

    try:
        result = await run_agent(
            llm_service=llm_service,
            tools=tools,
            agent_id=agent.id,
            org_id=current_user.org_id,
            execution_id=execution.id,
            policy_engine=policy_engine,
            audit_service=audit_service,
            cost_service=cost_service,
            goal=payload.goal,
            system_prompt=payload.system_prompt,
            max_steps=payload.max_steps,
        )

        final_answer = result.get("final_answer")
        stopped_reason = result.get("stopped_reason")

        if stopped_reason == "max_steps_reached":
            await exec_service.fail(
                execution.id, error="Execution stopped: Maximum reasoning steps reached."
            )
        else:
            await exec_service.complete(execution.id, result=final_answer or "Execution completed.")

    except Exception as exc:
        await exec_service.fail(execution.id, error=str(exc))

    await db.commit()
    updated_execution = await exec_service.get_execution(execution.id)
    return Envelope(data=updated_execution)


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

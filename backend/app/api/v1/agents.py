from __future__ import annotations
from typing import List
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from app.api.schemas.agent import AgentResponse, AgentCreate, AgentUpdate, PassportResponse
from app.api.schemas.common import Envelope, PaginatedResponse
from app.api.schemas.auth import CurrentUser
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_admin
from app.domain.agents.kill_switch import KillSwitchService
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_agent_service, get_db, get_kill_switch_service
from app.domain.agents.service import (
    AgentService,
    ComplianceError,
    InvalidStateTransitionError,
    SkillNotFoundError,
)

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/", response_model=Envelope[AgentResponse])
async def create_agent(
    payload: AgentCreate,
    user: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service)
):
    """Create a new agent draft."""
    try:
        agent = await service.create_agent(
            org_id=user.org_id,
            owner_id=user.id,
            name=payload.name,
            description=payload.description,
            skill_ids=payload.skills,
        )
    except SkillNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Envelope(data=AgentResponse.model_validate(agent))


@router.get("/", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    user: CurrentUser = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AgentService = Depends(get_agent_service)
):
    """List all agents for the current user's organization."""
    agents = await service.agent_repo.list_agents_by_org(user.org_id, limit=limit, offset=offset)
    count = await service.agent_repo.count_agents_by_org(user.org_id)
    
    # We must construct the response objects explicitly to ensure the passport is included.
    # The agent.passport is a joined load if the repo supports it, let's assume it does.
    return PaginatedResponse(
        data=[AgentResponse.model_validate(a) for a in agents],
        meta={"has_more": offset + limit < count, "total": count}
    )


@router.get("/{agent_id}", response_model=Envelope[AgentResponse])
async def get_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service)
):
    """Get specific agent details."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Envelope(data=AgentResponse.model_validate(agent))


@router.patch("/{agent_id}/submit", response_model=Envelope[AgentResponse])
async def submit_agent_for_review(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service)
):
    """Submit a draft agent for governance review."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        await service.submit_for_review(agent_id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ComplianceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reload agent to get the updated status
    updated_agent = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(updated_agent))


@router.patch("/{agent_id}/activate", response_model=Envelope[AgentResponse])
async def activate_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(require_admin),
    service: AgentService = Depends(get_agent_service)
):
    """Activate an approved agent."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        await service.activate_agent(agent_id)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reload agent to get the updated status
    updated_agent = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(updated_agent))


@router.patch("/{agent_id}", response_model=Envelope[AgentResponse])
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: AgentService = Depends(get_agent_service),
):
    """Edit an agent's name and description.

    Skills are deliberately **not** editable here. An agent's permissions are
    the union of its skills (FRD-02), so changing them after activation would
    silently widen what it may do without re-running the compliance check.
    There is no re-review flow yet, so the request is refused rather than
    quietly letting permissions drift.
    """
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    if payload.skills is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Skills cannot be changed after creation: an agent's permissions "
                "are derived from its skills and would bypass the compliance check. "
                "Create a new agent with the skills you need."
            ),
        )

    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description

    await db.commit()
    refreshed = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(refreshed))


@router.post("/{agent_id}/kill", response_model=Envelope[AgentResponse])
async def kill_agent(
    agent_id: UUID,
    reason: str = Body("Kill switch activated by an administrator", embed=True),
    user: CurrentUser = Depends(require_admin),
    service: AgentService = Depends(get_agent_service),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
):
    """Stop an agent immediately (FRD-12).

    Suspends the agent and its passport together, and writes the audit entry.
    Any run in flight stops at its next tool call, because the governance gate
    reads the passport before every call and will now find it suspended.
    """
    try:
        await kill_switch.suspend_agent(
            agent_id=agent_id, actor_id=user.id, org_id=user.org_id, reason=reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    agent = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(agent))


@router.post("/{agent_id}/reactivate", response_model=Envelope[AgentResponse])
async def reactivate_agent(
    agent_id: UUID,
    reason: str = Body("Reactivated by an administrator", embed=True),
    user: CurrentUser = Depends(require_admin),
    service: AgentService = Depends(get_agent_service),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
):
    """Bring a suspended agent back. Never automatic — FRD-12 requires a person."""
    try:
        await kill_switch.reactivate_agent(
            agent_id=agent_id, actor_id=user.id, org_id=user.org_id, reason=reason
        )
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=detail)

    agent = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(agent))

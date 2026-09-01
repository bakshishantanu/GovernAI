from __future__ import annotations
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas.agent import AgentResponse, AgentCreate, AgentUpdate, PassportResponse
from app.api.schemas.common import Envelope, PaginatedResponse
from app.api.schemas.auth import CurrentUser
from app.domain.auth.middleware import get_current_user
from app.api.deps import get_agent_service
from app.domain.agents.service import AgentService

router = APIRouter()

@router.post("/", response_model=Envelope[AgentResponse])
async def create_agent(
    payload: AgentCreate, 
    user: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service)
):
    """Create a new agent draft."""
    agent = await service.create_agent(
        org_id=user.org_id,
        owner_id=user.id,
        name=payload.name,
        description=payload.description
    )
    return Envelope(data=AgentResponse.model_validate(agent))


@router.get("/", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    user: CurrentUser = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
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
        
    await service.submit_for_review(agent_id)
    
    # Reload agent to get the updated status
    updated_agent = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(updated_agent))


@router.patch("/{agent_id}/activate", response_model=Envelope[AgentResponse])
async def activate_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service)
):
    """Activate an approved agent."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    await service.activate_agent(agent_id)
    
    # Reload agent to get the updated status
    updated_agent = await service.agent_repo.get_agent(agent_id)
    return Envelope(data=AgentResponse.model_validate(updated_agent))

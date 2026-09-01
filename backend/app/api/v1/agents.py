from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas.agent import AgentResponse, AgentCreate, AgentUpdate, PassportResponse
from app.api.schemas.common import Envelope, PaginatedResponse
from app.api.schemas.auth import CurrentUser
from app.domain.auth.middleware import get_current_user
from datetime import datetime, timezone

router = APIRouter()

# --- STUB DATA (In-memory mock for Sprint 1 frontend testing) ---
# When P3 finishes the real PostgreSQL AgentService injection, we swap this out.
MOCK_AGENTS = {}

def get_mock_passport(agent_id: UUID) -> PassportResponse:
    return PassportResponse(
        id=uuid4(),
        agent_id=agent_id,
        compliance_status="PENDING",
        lifecycle_state="DRAFT",
        compliance_checked_at=None,
        permissions=[],
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

def create_mock_agent(data: AgentCreate, user: CurrentUser) -> AgentResponse:
    agent_id = uuid4()
    agent = AgentResponse(
        id=agent_id,
        org_id=user.org_id,
        owner_id=user.id,
        name=data.name,
        description=data.description,
        status="DRAFT",
        skills=data.skills,
        passport=get_mock_passport(agent_id),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    MOCK_AGENTS[agent_id] = agent
    return agent

# Initialize with one mock agent so the dashboard has something to show
_mock_user = CurrentUser(id=uuid4(), org_id=uuid4(), role="admin")
create_mock_agent(AgentCreate(name="Support Bot", description="Handles L1 tickets", skills=[]), _mock_user)


@router.post("/", response_model=Envelope[AgentResponse])
async def create_agent(
    payload: AgentCreate, 
    user: CurrentUser = Depends(get_current_user)
):
    """Create a new agent draft."""
    agent = create_mock_agent(payload, user)
    return Envelope(data=agent)


@router.get("/", response_model=Envelope[PaginatedResponse[AgentResponse]])
async def list_agents(
    user: CurrentUser = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """List all agents for the current user's organization."""
    # Filter by user's org_id
    org_agents = [a for a in MOCK_AGENTS.values() if a.org_id == user.org_id]
    
    paginated = PaginatedResponse(
        items=org_agents[offset:offset + limit],
        total=len(org_agents),
        limit=limit,
        offset=offset
    )
    return Envelope(data=paginated)


@router.get("/{agent_id}", response_model=Envelope[AgentResponse])
async def get_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get specific agent details."""
    agent = MOCK_AGENTS.get(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Envelope(data=agent)


@router.patch("/{agent_id}/submit", response_model=Envelope[AgentResponse])
async def submit_agent_for_review(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Submit a draft agent for governance review."""
    agent = MOCK_AGENTS.get(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.passport.lifecycle_state != "DRAFT":
        raise HTTPException(status_code=400, detail="Only DRAFT agents can be submitted")
        
    # Simulate compliance review passing automatically for MVP
    agent.passport.lifecycle_state = "APPROVED"
    agent.passport.compliance_status = "PASSED"
    agent.passport.compliance_checked_at = datetime.now(timezone.utc)
    agent.updated_at = datetime.now(timezone.utc)
    
    return Envelope(data=agent)


@router.patch("/{agent_id}/activate", response_model=Envelope[AgentResponse])
async def activate_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Activate an approved agent."""
    agent = MOCK_AGENTS.get(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.passport.lifecycle_state != "APPROVED":
        raise HTTPException(status_code=400, detail="Only APPROVED agents can be activated")
        
    agent.status = "ACTIVE"
    agent.passport.lifecycle_state = "ACTIVE"
    agent.updated_at = datetime.now(timezone.utc)
    
    return Envelope(data=agent)

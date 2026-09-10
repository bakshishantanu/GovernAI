from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_agent_request_service
from app.api.schemas.agent_requests import AgentRequestCreate, AgentRequestResponse
from app.api.schemas.auth import CurrentUser
from app.domain.agent_requests.service import (
    AgentRequestService,
    InvalidStateTransitionError,
    RequestAlreadyClaimedError,
    RequestNotFoundError,
)
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_builder_or_admin, require_role

router = APIRouter()


@router.post("/", response_model=AgentRequestResponse)
async def create_request(
    request: AgentRequestCreate,
    service: AgentRequestService = Depends(get_agent_request_service),
    user: CurrentUser = Depends(require_role("agent_builder", "admin")),
):
    """Create a new agent request."""
    return await service.create_request(
        org_id=user.org_id,
        requester_id=user.id,
        title=request.title,
        description=request.description,
        requested_skills=request.requested_skills,
    )


@router.get("/", response_model=list[AgentRequestResponse])
async def list_requests(
    status: str | None = None,
    requester_id: UUID | None = None,
    builder_id: UUID | None = None,
    service: AgentRequestService = Depends(get_agent_request_service),
    user: CurrentUser = Depends(get_current_user),
):
    """List agent requests with optional filters."""
    # simple listing with filters
    # User can only see their own requests (enforced if user role)
    if user.role == "agent_builder":
        requester_id = user.id

    # Builder can see all PENDING, or their own CLAIMED/FULFILLED
    # This could be more complex but we stick to basic query params for now

    return await service.request_repo.list_requests(
        org_id=user.org_id,
        requester_id=requester_id,
        builder_id=builder_id,
        status=status,
    )


@router.get("/{request_id}", response_model=AgentRequestResponse)
async def get_request(
    request_id: UUID,
    service: AgentRequestService = Depends(get_agent_request_service),
    user: CurrentUser = Depends(get_current_user),
):
    """Get a specific request."""
    req = await service.request_repo.get_request(request_id)
    if not req or req.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Request not found")

    if user.role == "agent_builder" and req.requester_id != user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    return req


@router.post("/{request_id}/claim", response_model=AgentRequestResponse)
@router.patch("/{request_id}/claim", response_model=AgentRequestResponse)
async def claim_request(
    request_id: UUID,
    service: AgentRequestService = Depends(get_agent_request_service),
    user: CurrentUser = Depends(require_builder_or_admin),
):
    """Claim a pending request.

    Post role-merge: a non-admin user may only claim and build **their own**
    request, not any request in the queue — confirmed directly as the
    intended behavior (narrower than a general "self-claim allowed", and a
    genuinely new rule neither the old `user` nor `agent_builder` role
    enforced on its own). Admin is unrestricted, as before.
    """
    req = await service.request_repo.get_request(request_id)
    if not req or req.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Request not found")

    if user.role != "admin" and req.requester_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only build agents from your own requests.",
        )

    try:
        return await service.claim_request(request_id, user.id)
    except RequestNotFoundError:
        raise HTTPException(status_code=404, detail="Request not found")
    except RequestAlreadyClaimedError:
        raise HTTPException(status_code=409, detail="Request already claimed")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/cancel", response_model=AgentRequestResponse)
@router.patch("/{request_id}/cancel", response_model=AgentRequestResponse)
async def cancel_request(
    request_id: UUID,
    service: AgentRequestService = Depends(get_agent_request_service),
    user: CurrentUser = Depends(require_role("agent_builder", "admin")),
):
    """Cancel a request."""
    req = await service.request_repo.get_request(request_id)
    if not req or req.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Request not found")

    if user.role == "agent_builder" and req.requester_id != user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    try:
        return await service.cancel_request(request_id)
    except RequestNotFoundError:
        raise HTTPException(status_code=404, detail="Request not found")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

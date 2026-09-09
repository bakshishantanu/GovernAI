from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.audit import AuditEventResponse
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.domain.audit.repository import AuditRepository
from app.domain.auth.middleware import get_current_user

router = APIRouter(prefix="/audits", tags=["audits"])


def get_audit_repo(db: AsyncSession = Depends(get_db)) -> AuditRepository:
    return AuditRepository(db)


@router.get("/", response_model=Envelope[list[AuditEventResponse]])
async def list_audit_events(
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    repo: AuditRepository = Depends(get_audit_repo),
):
    """
    List audit events (security logs) for the current user's organization.
    Ordered by most recent first.
    """
    # Fetch all events (repository already orders by timestamp desc)
    # If the database gets large, we should pass 'limit' down to the repository.
    builder_id = current_user.id if current_user.role == "agent_builder" else None
    assigned_user_id = current_user.id if current_user.role == "user" else None
    
    events = await repo.get_events_for_org(
        current_user.org_id, 
        builder_id=builder_id, 
        assigned_user_id=assigned_user_id
    )
    return Envelope(data=events[:limit])

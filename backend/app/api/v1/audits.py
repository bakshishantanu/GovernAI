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
    # Same id passed to both: get_events_for_org already ORs owner_id,
    # assigned_user_id and actor_id together (see its docstring), so a
    # merged user who is both an owner and an assignee sees the union
    # correctly without any change needed there.
    non_admin_id = None if current_user.role == "admin" else current_user.id

    events = await repo.get_events_for_org(
        current_user.org_id, builder_id=non_admin_id, assigned_user_id=non_admin_id
    )
    return Envelope(data=events[:limit])

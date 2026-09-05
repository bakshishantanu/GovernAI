from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.domain.auth.middleware import get_current_user
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.audit import AuditEventResponse
from app.domain.audit.repository import AuditRepository

router = APIRouter(prefix="/audits", tags=["audits"])

def get_audit_repo(db: AsyncSession = Depends(get_db)) -> AuditRepository:
    return AuditRepository(db)


def _to_response(event) -> AuditEventResponse:
    """Map a stored audit row onto the API shape.

    The JSONB column is called `metadata` in the database but is mapped as
    `metadata_json` on the model, because `metadata` is reserved on a
    SQLAlchemy declarative class. Validating the ORM object directly therefore
    read SQLAlchemy's own `MetaData()` object into the response field and
    failed with `dict_type`, so this endpoint returned 500 for every real row.
    `costs.py` maps explicitly for exactly the same reason.
    """
    return AuditEventResponse(
        id=event.id,
        timestamp=event.timestamp,
        actor_type=event.actor_type,
        actor_id=event.actor_id,
        agent_id=event.agent_id,
        execution_id=event.execution_id,
        action=event.action,
        resource=event.resource,
        tool=event.tool,
        policy_decision=event.policy_decision,
        result=event.result,
        reason=event.reason,
        cost_usd=event.cost_usd,
        metadata=event.metadata_json,
    )


@router.get("/", response_model=Envelope[list[AuditEventResponse]])
async def list_audit_events(
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    repo: AuditRepository = Depends(get_audit_repo)
):
    """
    List audit events (security logs) for the current user's organization.
    Ordered by most recent first.
    """
    # Fetch all events (repository already orders by timestamp desc)
    # If the database gets large, we should pass 'limit' down to the repository.
    events = await repo.get_events_for_org(current_user.org_id)
    return Envelope(data=[_to_response(e) for e in events[:limit]])

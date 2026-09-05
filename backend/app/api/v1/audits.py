from __future__ import annotations
import uuid
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
    agent_id: uuid.UUID | None = Query(None, description="Narrow to one agent"),
    execution_id: uuid.UUID | None = Query(None, description="Narrow to one run"),
    current_user: CurrentUser = Depends(get_current_user),
    repo: AuditRepository = Depends(get_audit_repo)
):
    """Audit events for the caller's organisation, most recent first.

    `execution_id` is what lets the run viewer show a run that finished before
    anyone opened it: the SSE stream only carries events that happen while it
    is connected, so without a way to read a run's history the viewer showed
    "no governance events" for a run that had plenty.

    The filters are applied after the org fetch because the repository has no
    filtered query. That is fine at this size and wrong at scale — worth
    pushing down into `AuditRepository` when the table grows.
    """
    events = await repo.get_events_for_org(current_user.org_id)

    if agent_id is not None:
        events = [e for e in events if e.agent_id == agent_id]
    if execution_id is not None:
        events = [e for e in events if e.execution_id == execution_id]

    return Envelope(data=[_to_response(e) for e in events[:limit]])

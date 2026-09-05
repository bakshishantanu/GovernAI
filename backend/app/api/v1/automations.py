from __future__ import annotations

"""Automations — recipe-style rules, and the record of every time they fired.

Creating, changing and deleting a rule is an admin action: an automation can
suspend an agent, so it carries the same authority as the kill switch and is
gated the same way. Reading is open to any member of the org, because the run
history is evidence and evidence that only admins can see is not much use.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.auth import CurrentUser
from app.api.schemas.automation import (
    AutomationCreate,
    AutomationResponse,
    AutomationRunResponse,
    AutomationUpdate,
)
from app.api.schemas.common import Envelope
from app.domain.agents.repository import AgentRepository
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_admin
from app.domain.automations.models import Automation
from app.domain.automations.repository import AutomationRepository

router = APIRouter(prefix="/automations", tags=["automations"])

#: Run history gets its own prefix rather than sitting at `/automations/runs`.
#: A static segment beside `/automations/{automation_id}` is the exact shape
#: that broke `PATCH /policies/rules/{id}` — it resolves only by declaration
#: order, and `tests/unit/test_route_paths.py` rejects it structurally. One
#: endpoint with an optional filter covers both "all runs" and "one rule's
#: runs", so nesting a second copy is unnecessary.
runs_router = APIRouter(prefix="/automation-runs", tags=["automations"])


def get_automation_repo(db: AsyncSession = Depends(get_db)) -> AutomationRepository:
    return AutomationRepository(db)


@router.get("/", response_model=Envelope[list[AutomationResponse]])
async def list_automations(
    user: CurrentUser = Depends(get_current_user),
    repo: AutomationRepository = Depends(get_automation_repo),
):
    """Every automation in the caller's organisation, newest first."""
    return Envelope(data=await repo.list_automations(user.org_id))


@router.post(
    "/", response_model=Envelope[AutomationResponse], status_code=status.HTTP_201_CREATED
)
async def create_automation(
    payload: AutomationCreate,
    user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: AutomationRepository = Depends(get_automation_repo),
):
    """Create a rule. Admin only — a rule can suspend an agent."""
    if payload.agent_id is not None:
        agent = await AgentRepository(db).get_agent(payload.agent_id)
        if not agent or agent.org_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found in your organization",
            )

    automation = Automation(
        id=uuid.uuid4(),
        org_id=user.org_id,
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
        agent_id=payload.agent_id,
        trigger_type=payload.trigger_type,
        trigger_config=payload.trigger_config,
        action_type=payload.action_type,
        action_config=payload.action_config,
    )
    repo.add(automation)
    await db.commit()
    await db.refresh(automation)
    return Envelope(data=automation)


@runs_router.get("/", response_model=Envelope[list[AutomationRunResponse]])
async def list_runs(
    user: CurrentUser = Depends(get_current_user),
    automation_id: uuid.UUID | None = Query(None, description="Narrow to one rule"),
    limit: int = Query(50, ge=1, le=200),
    repo: AutomationRepository = Depends(get_automation_repo),
):
    """The evidence trail: every evaluation, including the ones that did nothing.

    A SKIPPED run is recorded as deliberately as a FIRED one. Knowing that a
    rule looked at an agent and decided not to act is evidence; only logging
    the firings would leave the platform unable to show that a rule was
    working but quiet.
    """
    return Envelope(
        data=await repo.list_runs(user.org_id, automation_id=automation_id, limit=limit)
    )


@router.get("/{automation_id}", response_model=Envelope[AutomationResponse])
async def get_automation(
    automation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    repo: AutomationRepository = Depends(get_automation_repo),
):
    automation = await repo.get_automation(automation_id)
    if not automation or automation.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    return Envelope(data=automation)


@router.patch("/{automation_id}", response_model=Envelope[AutomationResponse])
async def update_automation(
    automation_id: uuid.UUID,
    payload: AutomationUpdate,
    user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: AutomationRepository = Depends(get_automation_repo),
):
    """Rename, re-describe, or switch a rule on and off.

    Switching off is the important one: it is how a rule that is firing wrongly
    gets stopped, so it must not require deleting the rule and losing its
    history.
    """
    automation = await repo.get_automation(automation_id)
    if not automation or automation.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Automation not found")

    if payload.name is not None:
        automation.name = payload.name
    if payload.description is not None:
        automation.description = payload.description
    if payload.enabled is not None:
        automation.enabled = payload.enabled
    automation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(automation)
    return Envelope(data=automation)


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    automation_id: uuid.UUID,
    user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    repo: AutomationRepository = Depends(get_automation_repo),
):
    """Delete a rule that never fired.

    A rule with run history is **refused**, not cascaded. Those runs are the
    record of why an agent was suspended, and letting someone erase the rule
    would erase the explanation with it. Disabling is the supported way to
    stop a rule; it keeps the history intact.
    """
    automation = await repo.get_automation(automation_id)
    if not automation or automation.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Automation not found")

    if automation.runs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This automation has {len(automation.runs)} recorded run(s), which are "
                "the audit trail for what it did. Disable it instead of deleting it."
            ),
        )

    await repo.delete(automation)
    await db.commit()

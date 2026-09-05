from __future__ import annotations

"""Who am I.

The console had no way to ask this. It rendered a hardcoded name and role in
the sidebar, which is a poor look anywhere and actively misleading in a
product whose whole subject is who is allowed to do what — a member would have
seen "Admin" beside their own face.

This route reports exactly what the token proves and nothing more. It does not
reach for a display name or an email: those live in Supabase, not in this
database, and inventing one here would be the same mistake in a new place.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.settings import OrganizationSummary, SettingsResponse
from app.domain.agents.models import Agent
from app.domain.auth.middleware import dev_token_allowed, get_current_user
from app.domain.auth.models import Organization
from app.domain.automations.models import Automation
from app.domain.governance.budget import BUDGET_WINDOW, resolve_cap
from app.domain.policies.models import Policy

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=Envelope[CurrentUser])
async def me(user: CurrentUser = Depends(get_current_user)):
    """The identity the caller's token establishes: user, org and role."""
    return Envelope(data=user)


@router.get("/settings", response_model=Envelope[SettingsResponse])
async def settings_overview(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """What is configured and enforced for this organisation.

    Everything here is read-only, and the response says so per field. The
    budget cap and the dev-token bypass are environment values read at
    startup; a console control that appeared to change them would do nothing,
    and a dead switch on a settings page is worse than no switch at all.
    """
    org = await db.get(Organization, user.org_id)

    agent_count = await db.scalar(
        select(func.count(Agent.id)).where(Agent.org_id == user.org_id)
    )
    policy_count = await db.scalar(
        select(func.count(Policy.id)).where(Policy.org_id == user.org_id)
    )
    automation_count = await db.scalar(
        select(func.count(Automation.id)).where(Automation.org_id == user.org_id)
    )

    return Envelope(
        data=SettingsResponse(
            user=user,
            organization=OrganizationSummary(
                id=user.org_id,
                name=org.name if org else "Unknown organisation",
                agent_count=int(agent_count or 0),
                policy_count=int(policy_count or 0),
                automation_count=int(automation_count or 0),
            ),
            budget_cap_usd=resolve_cap(user.id),
            budget_window_hours=int(BUDGET_WINDOW.total_seconds() // 3600),
            dev_token_enabled=dev_token_allowed(),
        )
    )

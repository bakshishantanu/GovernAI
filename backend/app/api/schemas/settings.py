from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.api.schemas.auth import CurrentUser


class OrganizationSummary(BaseModel):
    id: UUID
    name: str
    agent_count: int
    policy_count: int
    automation_count: int


class SettingsResponse(BaseModel):
    """What is configured for this organisation, and what is enforcing it.

    Read-only by design. The budget cap and the dev-token bypass come from
    environment values read at startup, so there is nothing here the console
    could write back; the page says as much rather than offering a control
    that would silently do nothing.
    """

    user: CurrentUser
    organization: OrganizationSummary
    #: The cap the budget guard applies, per agent, over the window below.
    budget_cap_usd: float
    budget_window_hours: int
    #: True when "dummy-token" is accepted as an admin — local development
    #: only, and worth showing because it is a live authentication bypass.
    dev_token_enabled: bool

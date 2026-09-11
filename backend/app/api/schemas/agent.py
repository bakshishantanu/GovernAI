from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

AgentStatus = Literal["DRAFT", "ACTIVE", "SUSPENDED", "REVOKED"]
LifecycleState = Literal["DRAFT", "APPROVED", "ACTIVE", "SUSPENDED", "REVOKED"]
ComplianceStatus = Literal["PENDING", "PASSED", "FAILED"]


class PassportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_id: UUID
    compliance_status: ComplianceStatus
    compliance_checked_at: datetime | None = None
    lifecycle_state: LifecycleState
    permissions: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("compliance_status", "lifecycle_state", mode="before")
    @classmethod
    def _normalise_legacy_status(cls, value):
        """Accept the vocabulary older rows were written with.

        These are free-text columns, not database enums, so whatever wrote a
        row is what comes back. Seeded databases still hold
        `compliance_status="COMPLIANT"` from an earlier seed script, and one
        such row used to fail validation for the *whole* response — a single
        legacy agent 500'd the entire agents list rather than rendering. The
        writers now agree on this vocabulary; this keeps a database that
        predates that from taking the page down.
        """
        if not isinstance(value, str):
            return value
        normalised = value.strip().upper()
        # "COMPLIANT" was the old name for a passport that passed its check.
        return "PASSED" if normalised == "COMPLIANT" else normalised

    @field_validator("permissions", mode="before")
    @classmethod
    def _extract_permission_strings(cls, value):
        """`passport.permissions` is the ORM relationship — a list of
        `Permission` rows, not strings. Each row's real value is its
        `.permission` column; extract it here rather than on the model, so
        the ORM stays a plain mapping and every response boundary that reads
        it goes through the same rule."""
        return [item.permission if hasattr(item, "permission") else item for item in value]


class AgentSkillRef(BaseModel):
    """A skill attached to an agent, as the console needs to show it.

    Carries the display name as well as the id: `agent_skills` stores only
    `skill_id`, and showing a raw slug where a human expects a skill name is
    the sort of thing that makes a governance console look unfinished.
    """

    id: str
    name: str


class AgentCreate(BaseModel):
    name: str
    description: str
    skills: list[str]  # skill IDs
    request_id: UUID | None = None
    assigned_user_id: UUID | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    skills: list[str] | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    org_id: UUID
    owner_id: UUID
    assigned_user_id: UUID | None = None
    request_id: UUID | None = None
    name: str
    description: str
    status: AgentStatus
    passport: PassportResponse | None = None
    #: The agent's skills. `Agent` has no `skills` relationship, so this is
    #: filled by the route from `agent_skills`; it was absent entirely, and
    #: the console consequently told the user that an agent with two skills
    #: had none and "cannot call any tool".
    skills: list[AgentSkillRef] = []
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentResponse]

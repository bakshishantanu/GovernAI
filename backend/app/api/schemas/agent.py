from __future__ import annotations
from typing import Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

AgentStatus = Literal["DRAFT", "ACTIVE", "SUSPENDED", "REVOKED"]
LifecycleState = Literal["DRAFT", "APPROVED", "ACTIVE", "SUSPENDED", "REVOKED"]
ComplianceStatus = Literal["PENDING", "PASSED", "FAILED"]

class PassportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_id: UUID
    compliance_status: ComplianceStatus
    compliance_checked_at: Optional[datetime] = None
    lifecycle_state: LifecycleState
    permissions: list[str]
    created_at: datetime
    updated_at: datetime

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

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[list[str]] = None

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    org_id: UUID
    owner_id: UUID
    name: str
    description: str
    status: AgentStatus
    passport: Optional[PassportResponse] = None
    #: The agent's skills. `Agent` has no `skills` relationship, so this is
    #: filled by the route from `agent_skills`; it was absent entirely, and the
    #: console consequently told the user that an agent with two skills had
    #: none and "cannot call any tool".
    skills: list[AgentSkillRef] = []
    created_at: datetime
    updated_at: datetime

class AgentListResponse(BaseModel):
    items: list[AgentResponse]

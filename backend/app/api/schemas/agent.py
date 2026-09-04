from __future__ import annotations
from typing import Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

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

class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(max_length=2000)
    skills: list[str] = Field(max_length=20)  # skill IDs

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    skills: Optional[list[str]] = Field(default=None, max_length=20)

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    org_id: UUID
    owner_id: UUID
    name: str
    description: str
    status: AgentStatus
    passport: Optional[PassportResponse] = None
    created_at: datetime
    updated_at: datetime

class AgentListResponse(BaseModel):
    items: list[AgentResponse]

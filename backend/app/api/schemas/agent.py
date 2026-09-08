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

class AgentCreate(BaseModel):
    name: str
    description: str
    skills: list[str]  # skill IDs
    request_id: Optional[UUID] = None
    assigned_user_id: Optional[UUID] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[list[str]] = None

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    org_id: UUID
    owner_id: UUID
    assigned_user_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    name: str
    description: str
    status: AgentStatus
    passport: Optional[PassportResponse] = None
    created_at: datetime
    updated_at: datetime

class AgentListResponse(BaseModel):
    items: list[AgentResponse]

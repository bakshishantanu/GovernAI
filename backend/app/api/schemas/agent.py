from typing import Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

AgentStatus = Literal["DRAFT", "ACTIVE", "SUSPENDED", "REVOKED"]
LifecycleState = Literal["DRAFT", "APPROVED", "ACTIVE", "SUSPENDED", "REVOKED"]
ComplianceStatus = Literal["PENDING", "PASSED", "FAILED"]

class PassportResponse(BaseModel):
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

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[list[str]] = None

class AgentResponse(BaseModel):
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

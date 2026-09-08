from __future__ import annotations
from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

ActorType = Literal["USER", "AGENT", "SYSTEM", "user", "agent", "system"]
PolicyDecision = Literal["ALLOWED", "DENIED", "N/A", "ALLOW", "DENY"]

class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    actor_type: ActorType
    actor_id: UUID
    agent_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    action: str
    resource: Optional[str] = None
    tool: Optional[str] = None
    policy_decision: PolicyDecision
    result: Optional[str] = None
    reason: Optional[str] = None
    cost_usd: Optional[float] = None
    #: The DB column is named `metadata`, which collides with SQLAlchemy's
    #: own reserved `Base.metadata` attribute, so the ORM model maps it to
    #: `metadata_json` instead. `validation_alias` reads that attribute name
    #: under `from_attributes=True` while the API still calls the field
    #: `metadata` — without this, every row read `AuditEvent.metadata`
    #: (SQLAlchemy's internal `MetaData()` registry) instead of the real
    #: value, and the whole list failed pydantic validation.
    metadata: Optional[dict[str, Any]] = Field(default=None, validation_alias="metadata_json")

class AuditQueryParams(BaseModel):
    agent_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    action: Optional[str] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    limit: int = 50
    cursor: Optional[UUID] = None

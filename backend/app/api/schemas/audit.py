from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ActorType = Literal["USER", "AGENT", "SYSTEM", "user", "agent", "system"]
PolicyDecision = Literal["ALLOWED", "DENIED", "N/A", "ALLOW", "DENY"]


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    actor_type: ActorType
    actor_id: UUID
    agent_id: UUID | None = None
    execution_id: UUID | None = None
    action: str
    resource: str | None = None
    tool: str | None = None
    policy_decision: PolicyDecision
    result: str | None = None
    reason: str | None = None
    cost_usd: float | None = None
    #: The DB column is named `metadata`, which collides with SQLAlchemy's
    #: own reserved `Base.metadata` attribute, so the ORM model maps it to
    #: `metadata_json` instead. `validation_alias` reads that attribute name
    #: under `from_attributes=True` while the API still calls the field
    #: `metadata` — without this, every row read `AuditEvent.metadata`
    #: (SQLAlchemy's internal `MetaData()` registry) instead of the real
    #: value, and the whole list failed pydantic validation.
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_json")


class AuditQueryParams(BaseModel):
    agent_id: UUID | None = None
    execution_id: UUID | None = None
    actor_id: UUID | None = None
    action: str | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None
    limit: int = 50
    cursor: UUID | None = None

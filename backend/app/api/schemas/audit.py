from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

ActorType = Literal["USER", "AGENT", "SYSTEM"]
PolicyDecision = Literal["ALLOWED", "DENIED", "N/A"]

class AuditEventResponse(BaseModel):
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
    metadata: Optional[dict[str, Any]] = None

class AuditQueryParams(BaseModel):
    agent_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    action: Optional[str] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    limit: int = 50
    cursor: Optional[UUID] = None

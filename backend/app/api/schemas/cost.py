from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

EventType = Literal["LLM_CALL", "TOOL_CALL"]

class CostEventResponse(BaseModel):
    id: UUID
    agent_id: UUID
    execution_id: UUID
    execution_step_id: Optional[UUID] = None
    event_type: EventType
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: float
    timestamp: datetime
    metadata: Optional[dict[str, Any]] = None

class CostSummaryResponse(BaseModel):
    total_cost_usd: float
    by_agent: dict[str, float]
    by_model: dict[str, float]

from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

ExecutionStatus = Literal["RUNNING", "COMPLETED", "FAILED", "TERMINATED"]

class ExecutionCreate(BaseModel):
    goal: str

class ExecutionStepResponse(BaseModel):
    id: UUID
    execution_id: UUID
    step_number: int
    tool: Optional[str] = None
    tool_args: Optional[dict[str, Any]] = None
    tool_result: Optional[dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime

class ExecutionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    goal: str
    status: ExecutionStatus
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: Optional[list[ExecutionStepResponse]] = None

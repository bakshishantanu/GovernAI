from __future__ import annotations
from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

ExecutionStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "TERMINATED", "CANCELLED"]

class ExecutionCreate(BaseModel):
    agent_id: UUID
    goal: str
    system_prompt: Optional[str] = None
    max_steps: int = 10

class ExecutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    org_id: UUID
    goal: str
    status: ExecutionStatus
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: list[ExecutionStepResponse] = []

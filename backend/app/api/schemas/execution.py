from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ExecutionStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "TERMINATED", "CANCELLED"]


class ExecutionCreate(BaseModel):
    agent_id: UUID
    goal: str
    system_prompt: str | None = None
    max_steps: int = 10


class ExecutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID
    step_number: int
    tool: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
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
    result: str | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[ExecutionStepResponse] = []

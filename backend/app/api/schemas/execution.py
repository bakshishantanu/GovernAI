from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.schemas.audit import AuditEventResponse
from app.api.schemas.cost import CostEventResponse

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
    # The column has existed since the execution_triggered_by migration but was
    # never surfaced, so the console had no way to say who started a run. Null
    # for runs with no human actor (e.g. the Jira webhook).
    triggered_by_id: UUID | None = None
    steps: list[ExecutionStepResponse] = []
    # Populated only by get_execution_detail, which loads them from
    # CostRepository -- absent (None) on list/create responses rather than
    # silently 0, so the frontend can tell "not computed" from "genuinely
    # free".
    total_cost_usd: float | None = None
    total_tokens: int | None = None


class ExecutionTimelineResponse(BaseModel):
    """The full recorded history of one run: every governed tool call and every
    LLM call, each in its own real shape rather than flattened into a generic
    "event" that would lose fields.

    Exists because `/stream` only ever shows events from the moment a client
    connects — nothing before that, and nothing at all for a run that had
    already finished by the time someone opened its page.

    The console interleaves the two lists by timestamp into one chronological
    feed. They are kept separate here because they answer different questions
    (governance decisions vs. spend), and a caller that wants only one should
    not have to parse the other back out of a merge.
    """

    execution_id: UUID
    governance_events: list[AuditEventResponse]
    cost_events: list[CostEventResponse]

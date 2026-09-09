from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

EventType = Literal["LLM_CALL", "TOOL_CALL"]


class CostEventResponse(BaseModel):
    id: UUID
    agent_id: UUID
    execution_id: UUID
    execution_step_id: UUID | None = None
    event_type: EventType
    model: str | None = None
    provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float
    timestamp: datetime
    metadata: dict[str, Any] | None = None


class CostSummaryResponse(BaseModel):
    total_cost_usd: float
    by_agent: dict[str, float]
    by_model: dict[str, float]


class AgentBudgetStatus(BaseModel):
    """One agent's spend inside the enforced window, against its own cap."""

    agent_id: UUID
    name: str
    spend_usd: float
    cap_usd: float
    #: 0-100+, and deliberately allowed past 100: an agent can finish the tool
    #: call that crosses the cap before the guard suspends it.
    percent_of_cap: float
    suspended: bool


class BudgetStatusResponse(BaseModel):
    """What the live budget guard would see right now.

    The cap is the same org-wide value the guard enforces
    (`domain/governance/budget.resolve_cap`) over the same rolling window, so
    this reports the real control rather than a second, cosmetic one.
    """

    cap_usd: float
    window_hours: int
    total_spend_usd: float
    agents: list[AgentBudgetStatus]
    #: The agent closest to its cap, or null when nothing has been spent.
    closest: AgentBudgetStatus | None = None

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TriggerType = Literal["TOOL_DENIED", "SPEND_THRESHOLD", "AGENT_SUSPENDED"]
ActionType = Literal["SUSPEND_AGENT", "RAISE_ALERT"]
RunOutcome = Literal["FIRED", "SKIPPED", "FAILED"]


class AutomationCreate(BaseModel):
    """A rule: when this happens, do that.

    `trigger_config` is validated per trigger type rather than left as a free
    dict. An automation can suspend an agent, so a typo'd key must be rejected
    at the door instead of silently making the rule never fire — a governance
    rule that quietly does nothing is the worst failure mode available.
    """

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    enabled: bool = True
    #: Null scopes the rule to every agent in the organisation.
    agent_id: Optional[UUID] = None

    trigger_type: TriggerType
    trigger_config: dict[str, Any] = Field(default_factory=dict)

    action_type: ActionType
    action_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("trigger_config")
    @classmethod
    def check_trigger_config(cls, value: dict, info) -> dict:
        trigger = (info.data or {}).get("trigger_type")

        if trigger == "TOOL_DENIED":
            count = value.get("count", 1)
            window = value.get("window_minutes", 60)
            if not isinstance(count, int) or count < 1:
                raise ValueError("count must be an integer of at least 1")
            if not isinstance(window, int) or not (1 <= window <= 1440):
                raise ValueError("window_minutes must be an integer between 1 and 1440")

        elif trigger == "SPEND_THRESHOLD":
            percent = value.get("percent_of_cap", 80)
            if not isinstance(percent, (int, float)) or not (1 <= percent <= 1000):
                raise ValueError("percent_of_cap must be a number between 1 and 1000")

        cooldown = value.get("cooldown_minutes", 10)
        if not isinstance(cooldown, int) or not (0 <= cooldown <= 1440):
            raise ValueError("cooldown_minutes must be an integer between 0 and 1440")

        return value


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    enabled: Optional[bool] = None


class AutomationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    automation_id: UUID
    agent_id: Optional[UUID] = None
    triggered_at: datetime
    outcome: RunOutcome
    detail: str
    context: dict[str, Any] = {}


class AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    description: str
    enabled: bool
    agent_id: Optional[UUID] = None
    trigger_type: TriggerType
    trigger_config: dict[str, Any]
    action_type: ActionType
    action_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RuleType = Literal[
    "PERMISSION_CHECK",
    "DENY_LIST",
    "RATE_LIMIT",
    "CUSTOM",
    "sql_blocklist",
    # These two are enforced by PolicyEngine.evaluate (domain/policies/engine.py,
    # matched case-insensitively) but were missing here, so the API refused to
    # create the two rule types that actually govern Enterprise Search queries
    # and Figma brand-color compliance. Drift recorded in DECISIONS/STATE;
    # this closes the API half of it.
    "solr_query_blocklist",
    "brand_color_check",
]


class PolicyRuleCreate(BaseModel):
    name: str
    rule_type: RuleType
    config: dict[str, Any]
    priority: int
    enabled: bool = True


class PolicyRuleResponse(PolicyRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    policy_id: UUID
    created_at: datetime
    updated_at: datetime


class PolicyCreate(BaseModel):
    name: str
    description: str
    enabled: bool = True
    rules: list[PolicyRuleCreate] = []


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    enabled: bool
    rules: list[PolicyRuleResponse] | None = None
    created_at: datetime
    updated_at: datetime

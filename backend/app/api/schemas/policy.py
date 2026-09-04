from __future__ import annotations
from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

RuleType = Literal["PERMISSION_CHECK", "DENY_LIST", "RATE_LIMIT", "CUSTOM", "sql_blocklist"]

class PolicyRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
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
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(max_length=1000)
    enabled: bool = True
    rules: list[PolicyRuleCreate] = Field(default=[], max_length=50)

class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    enabled: bool
    rules: Optional[list[PolicyRuleResponse]] = None
    created_at: datetime
    updated_at: datetime

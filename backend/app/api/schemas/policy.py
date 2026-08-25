from typing import Literal, Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

RuleType = Literal["PERMISSION_CHECK", "DENY_LIST", "RATE_LIMIT", "CUSTOM"]

class PolicyRuleCreate(BaseModel):
    name: str
    rule_type: RuleType
    config: dict[str, Any]
    priority: int
    enabled: bool = True

class PolicyRuleResponse(PolicyRuleCreate):
    id: UUID
    policy_id: UUID
    created_at: datetime
    updated_at: datetime

class PolicyCreate(BaseModel):
    name: str
    description: str
    enabled: bool = True

class PolicyResponse(BaseModel):
    id: UUID
    name: str
    description: str
    enabled: bool
    rules: Optional[list[PolicyRuleResponse]] = None
    created_at: datetime
    updated_at: datetime

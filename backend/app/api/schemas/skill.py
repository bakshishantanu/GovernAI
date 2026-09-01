from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

TrustLevel = Literal["VERIFIED", "COMMUNITY", "EXPERIMENTAL"]

class ToolResponse(BaseModel):
    name: str
    description: str
    required_permission: str

class SkillResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    version: str
    required_permissions: list[str]
    trust_level: TrustLevel
    tools: list[ToolResponse]

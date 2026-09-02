from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, field_validator

TrustLevel = Literal["VERIFIED", "COMMUNITY", "EXPERIMENTAL"]

class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    description: str
    required_permission: str

class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    display_name: str
    description: str
    version: str
    trust_level: TrustLevel
    tools: list[ToolResponse]
    required_permissions: list[str] = []

    @field_validator('required_permissions', mode='before')
    @classmethod
    def extract_permissions(cls, v: Any) -> list[str]:
        # Handle SQLAlchemy relationship list of SkillPermission objects
        if isinstance(v, list):
            return [p.permission if hasattr(p, 'permission') else p for p in v]
        return v

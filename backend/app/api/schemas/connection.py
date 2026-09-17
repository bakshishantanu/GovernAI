from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requirement_key: str
    type: str
    label: str
    status: str
    preview: dict[str, str] | None = None


class SaveConnectionRequest(BaseModel):
    type: str
    label: str
    fields: dict[str, str]


class RequirementFieldResponse(BaseModel):
    key: str
    label: str
    secret: bool = False
    placeholder: str = ""


class RequirementStatusResponse(BaseModel):
    key: str
    type: str
    label: str
    description: str = ""
    fields: list[RequirementFieldResponse] = []
    satisfied: bool

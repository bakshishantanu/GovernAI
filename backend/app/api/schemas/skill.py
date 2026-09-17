from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TrustLevel = Literal["VERIFIED", "COMMUNITY", "EXPERIMENTAL"]


class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str
    required_permission: str


class SkillRequirementFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    secret: bool = False
    placeholder: str = ""


class SkillRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    type: str
    label: str
    description: str = ""
    fields: list[SkillRequirementFieldResponse] = []

    @field_validator("fields", mode="before")
    @classmethod
    def _normalise_fields(cls, v: Any) -> Any:
        # `fields` is a nullable JSONB column; a requirement with no
        # per-field form (e.g. file_upload) stores an empty list there, but
        # nothing stops a stale or manually-inserted row from having NULL.
        return [] if v is None else v


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    description: str
    version: str
    trust_level: TrustLevel
    tools: list[ToolResponse]
    # validation_alias is load-bearing: SkillModel's ORM attribute is named
    # `permissions` (see domain/skills/models.py), not `required_permissions`.
    # Without this, from_attributes=True never finds a `required_permissions`
    # attribute on a real SkillModel and silently falls back to the `[]`
    # default below -- the extract_permissions validator never even runs on
    # real data. Confirmed live: GET /skills/ returned required_permissions:
    # [] for every skill despite each one having real SkillPermission rows
    # (agent creation itself was unaffected, since it reads `skill.permissions`
    # directly rather than through this schema).
    required_permissions: list[str] = Field(default=[], validation_alias="permissions")
    requirements: list[SkillRequirementResponse] = []

    @field_validator("trust_level", mode="before")
    @classmethod
    def _normalise_trust_level(cls, value):
        """Case-insensitive: `trust_level` is a free-text column, and an
        earlier hand-written seed wrote it lower-case ("verified") while the
        skill classes write it upper-case. A lower-case row used to 500 the
        entire skills list."""
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("required_permissions", mode="before")
    @classmethod
    def extract_permissions(cls, v: Any) -> list[str]:
        # Handle SQLAlchemy relationship list of SkillPermission objects
        if isinstance(v, list):
            return [p.permission if hasattr(p, "permission") else p for p in v]
        return v

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Role = Literal["admin", "agent_builder", "user"]


class CurrentUser(BaseModel):
    id: UUID
    org_id: UUID
    role: Role
    email: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_builder(self) -> bool:
        return self.role in ("agent_builder", "user")

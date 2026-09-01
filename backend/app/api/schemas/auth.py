from __future__ import annotations
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

Role = Literal["admin", "member"]

class CurrentUser(BaseModel):
    id: UUID
    org_id: UUID
    role: Role

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Role = Literal["admin", "agent_builder"]


class CurrentUser(BaseModel):
    id: UUID
    org_id: UUID
    role: Role
    #: From the real Supabase session's own `email`/`user_metadata.full_name`
    #: claims — never invented here. Both are null for the local dev-token
    #: bypass, which has no real identity behind it to report; the frontend
    #: falls back to the role name in that case rather than showing "None".
    email: str | None = None
    full_name: str | None = None

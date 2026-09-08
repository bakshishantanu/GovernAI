from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentUpload(BaseModel):
    title: str
    content: str
    source: str
    access_scope: list[str]

class DocumentResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    source: str
    access_scope: list[str]
    created_at: datetime

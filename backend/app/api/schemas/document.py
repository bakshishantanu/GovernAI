from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.documents.models import Document


class DocumentResponse(BaseModel):
    """One document as the console lists it.

    Carries `status` and `error` because ingestion is asynchronous: the
    console shows an uploaded file immediately and polls this until it
    reaches READY or FAILED. Without `error` on the response, a failed
    upload is indistinguishable from one that is still working.
    """

    id: UUID
    title: str
    filename: str | None
    mime_type: str | None
    status: str
    error: str | None
    page_count: int | None
    chunk_count: int | None
    access_scope: list[str]
    source: str
    created_at: datetime | None

    @classmethod
    def from_document(cls, document: Document) -> DocumentResponse:
        return cls(
            id=document.id,
            title=document.title,
            filename=document.filename,
            mime_type=document.mime_type,
            status=document.status,
            error=document.error,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            access_scope=list(document.access_scope or []),
            source=document.source,
            created_at=document.created_at,
        )

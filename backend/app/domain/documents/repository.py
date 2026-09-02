from __future__ import annotations
from uuid import UUID
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.domain.documents.models import Document, DocumentChunk

class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(self, document: Document) -> Document:
        self.session.add(document)
        return document

    async def get_document(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id).options(selectinload(Document.chunks))
        )
        return result.scalar_one_or_none()

    async def search_chunks(self, embedding: list[float], limit: int = 5) -> list[DocumentChunk]:
        # Using pgvector cosine distance
        result = await self.session.execute(
            select(DocumentChunk)
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_chunks_by_scope(
        self, embedding: list[float], permitted_scopes: list[str], limit: int = 5
    ) -> list[DocumentChunk]:
        """Same as search_chunks, but scope-filtered in the WHERE clause -
        applied before the ORDER BY/LIMIT, so an out-of-scope chunk is never
        even ranked, let alone returned (FRD-08 hard requirement)."""
        if not permitted_scopes:
            return []
        result = await self.session.execute(
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            # access_scope is declared JSONB on the model, but the migration
            # actually created it as plain json (a pre-existing model/schema
            # mismatch) - the ?| operator only exists for jsonb, hence the cast.
            .where(cast(Document.access_scope, JSONB).op("?|")(array(permitted_scopes)))
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(limit)
            .options(selectinload(DocumentChunk.document))
        )
        return list(result.scalars().all())

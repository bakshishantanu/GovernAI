from __future__ import annotations

from uuid import UUID

from sqlalchemy import cast, delete, select
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
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.chunks))
        )
        return result.scalar_one_or_none()

    async def get_document_meta(self, document_id: UUID) -> Document | None:
        """The row without its chunks.

        Deliberately separate from get_document: a 120-page upload has a few
        hundred chunks, each carrying a 768-float vector, and loading all of
        them only to read a status field is wasteful enough to notice.
        """
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def list_documents(self, org_id: UUID) -> list[Document]:
        """Newest first, without chunks (see get_document_meta)."""
        result = await self.session.execute(
            select(Document).where(Document.org_id == org_id).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self.session.add_all(chunks)

    async def delete_document(self, document_id: UUID) -> bool:
        """Remove a document and its chunks. Returns whether it existed.

        Chunks go first: there is a foreign key from document_chunks to
        documents and no ON DELETE CASCADE on it, so deleting the parent first
        fails.
        """
        document = await self.get_document_meta(document_id)
        if document is None:
            return False
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await self.session.delete(document)
        return True

    async def flush(self) -> None:
        await self.session.flush()

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

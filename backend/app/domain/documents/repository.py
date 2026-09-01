from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.documents.models import Document, DocumentChunk

class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(self, document: Document) -> Document:
        self.session.add(document)
        return document

    async def search_chunks(self, embedding: list[float], limit: int = 5) -> list[DocumentChunk]:
        # Using pgvector cosine distance
        result = await self.session.execute(
            select(DocumentChunk)
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        return list(result.scalars().all())

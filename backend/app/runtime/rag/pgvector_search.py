from __future__ import annotations
from uuid import UUID

from app.domain.documents.repository import DocumentRepository
from app.runtime.rag.embeddings import EmbeddingProvider
from app.runtime.rag.retrieval import Document, SearchResult


class PgVectorDocumentSearchAdapter:
    """Real retrieval: embeds the query with EmbeddingProvider, then finds the
    nearest chunks via pgvector cosine distance (DocumentRepository).
    Same public interface as DocumentSearchAdapter (retrieval.py) so
    DocumentSearchSkill can use either one interchangeably - this is the
    swap-in upgrade from TF-IDF, not a new skill (FRD-08)."""

    def __init__(
        self,
        repo: DocumentRepository,
        embedding_provider: EmbeddingProvider,
        min_relevance_score: float = 0.3,
    ) -> None:
        self._repo = repo
        self._embeddings = embedding_provider
        self._min_relevance_score = min_relevance_score

    async def search(self, query: str, permitted_scopes: frozenset[str], top_n: int = 3) -> list[SearchResult]:
        query_embedding = await self._embeddings.embed(query)
        chunks = await self._repo.search_chunks_by_scope(
            embedding=query_embedding, permitted_scopes=sorted(permitted_scopes), limit=top_n
        )

        results = []
        for chunk in chunks:
            distance = _cosine_distance(query_embedding, chunk.embedding)
            relevance_score = round(1.0 - distance, 4)
            if relevance_score < self._min_relevance_score:
                continue
            results.append(
                SearchResult(
                    chunk_id=f"{chunk.document_id}#{chunk.chunk_index}",
                    document_id=str(chunk.document_id),
                    document_title=chunk.document.title,
                    chunk_index=chunk.chunk_index,
                    text=chunk.content,
                    relevance_score=relevance_score,
                )
            )
        return results

    async def get_document(self, document_id: str) -> Document | None:
        db_document = await self._repo.get_document(UUID(document_id))
        if db_document is None:
            return None
        return Document(
            id=str(db_document.id),
            title=db_document.title,
            access_scope=frozenset(db_document.access_scope),
        )

    async def get_document_text(self, document_id: str) -> str | None:
        db_document = await self._repo.get_document(UUID(document_id))
        if db_document is None:
            return None
        chunks = sorted(db_document.chunks, key=lambda c: c.chunk_index)
        return " ".join(c.content for c in chunks)


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Recomputed in Python for the relevance_score/min_relevance_score
    threshold - the DB already did the real ranking via pgvector; this just
    turns the same distance into a score without a second DB round-trip."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))

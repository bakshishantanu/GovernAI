from __future__ import annotations
from abc import ABC, abstractmethod

import httpx


class EmbeddingProvider(ABC):
    """Turns text into a fixed-size vector for similarity search. `dimensions`
    must match the pgvector column's declared size (document_chunks.embedding
    is vector(768) - see alembic/versions/1321726bf4c7_documents.py)."""

    dimensions: int

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google's gemini-embedding-001. Its native output is 3072-dimensional,
    but it supports Matryoshka truncation via outputDimensionality - truncated
    to 768 here to match the pgvector column's fixed dimension (older,
    natively-768 models like text-embedding-004 aren't available on every
    account/region, so this is the portable choice)."""

    dimensions = 768
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def embed(self, text: str) -> list[float]:
        url = f"{self.BASE_URL}/{self._model}:embedContent"
        response = await self._client.post(
            url,
            headers={"x-goog-api-key": self._api_key},
            json={
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": self.dimensions,
            },
        )
        response.raise_for_status()
        return response.json()["embedding"]["values"]

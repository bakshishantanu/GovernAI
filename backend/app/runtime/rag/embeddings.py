from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import httpx


def retry_delay_seconds(response: httpx.Response, attempt: int, base: float) -> float:
    """How long to wait before retrying a rate-limited embedding call.

    Prefers the server's own answer. Gemini returns it two ways: a standard
    `Retry-After` header, and a RetryInfo entry inside the error body with a
    duration like "17s". Guessing when the server has already said is how you
    end up either hammering it or sleeping far longer than needed.

    Shared with the OCR client (see rag/ocr.py), which talks to the same API
    under the same quota and needs to back off identically.
    """
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(float(header), 1.0)
        except ValueError:
            pass

    try:
        details = response.json().get("error", {}).get("details", [])
        for detail in details:
            delay = detail.get("retryDelay")
            if isinstance(delay, str) and delay.endswith("s"):
                return max(float(delay[:-1]), 1.0)
    except Exception:
        pass

    # Exponential, so a quota that needs a full minute is not retried six
    # times in twenty seconds.
    return base * (2 ** (attempt - 1))


class EmbeddingProvider(ABC):
    """Turns text into a fixed-size vector for similarity search. `dimensions`
    must match the pgvector column's declared size (document_chunks.embedding
    is vector(768) - see alembic/versions/1321726bf4c7_documents.py)."""

    dimensions: int

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts, in order. Defaults to one call each; providers
        that support real batching should override (see GeminiEmbeddingProvider).
        """
        return [await self.embed(text) for text in texts]


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

    #: Texts per batchEmbedContents call.
    #:
    #: Not a size ceiling: measured against the live free tier, batches of 40
    #: and 50 were refused with 429 while a batch of 60 immediately afterwards
    #: succeeded. The constraint is a per-minute quota that refills, not the
    #: request size, so the thing that makes ingestion reliable is the backoff
    #: below, not a smaller batch. 50 is simply a reasonable payload size.
    BATCH_SIZE = 50

    #: A 429 here is transient: the embeddings quota is shared with every
    #: other Gemini call this project makes, chat included. Giving up on the
    #: first one would fail a whole document for a condition that clears by
    #: itself within a minute.
    MAX_RETRIES = 5
    BASE_BACKOFF_SECONDS = 15

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

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """One HTTP call per BATCH_SIZE texts instead of one per text.

        This is the difference between a real document being ingestable and
        not: a 120-page filing is ~150 chunks, which is 150 sequential calls
        against a shared per-minute quota, versus 3 batched ones.
        """
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[start : start + self.BATCH_SIZE]
            embeddings = await self._post_batch_with_retry(batch)
            if len(embeddings) != len(batch):
                # Silently short results would misalign every vector after
                # this point with the wrong chunk text, which is worse than
                # failing: retrieval would quietly return the wrong page.
                raise RuntimeError(
                    f"Embedding batch returned {len(embeddings)} vectors for {len(batch)} inputs"
                )
            vectors.extend(item["values"] for item in embeddings)
        return vectors

    async def _post_batch_with_retry(self, batch: list[str]) -> list[dict]:
        """One batch, retrying while the API says it is rate limited."""
        url = f"{self.BASE_URL}/{self._model}:batchEmbedContents"
        payload = {
            "requests": [
                {
                    # Required per-request, even though the model is already
                    # in the URL.
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.dimensions,
                }
                for text in batch
            ]
        }

        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            response = await self._client.post(
                url, headers={"x-goog-api-key": self._api_key}, json=payload
            )
            # 503 means the model is temporarily overloaded, which clears the
            # same way a 429 does.
            if response.status_code not in (429, 503):
                response.raise_for_status()
                return response.json().get("embeddings", [])

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc

            if attempt == self.MAX_RETRIES:
                break
            await asyncio.sleep(retry_delay_seconds(response, attempt, self.BASE_BACKOFF_SECONDS))

        assert last_error is not None
        raise last_error

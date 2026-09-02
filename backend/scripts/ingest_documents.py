"""One-time seed: embeds the same 5 mock documents retrieval.py used for
TF-IDF and writes them into Postgres (documents/document_chunks) with real
Gemini embeddings, so PgVectorDocumentSearchAdapter has something to find.

Idempotent by title - safe to re-run; makes real network calls (needs
GEMINI_API_KEY), so it's a script, not a pytest test, same as
manual_llm_smoke_test.py.

    .venv/Scripts/python.exe scripts/ingest_documents.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.domain.documents.models import Document, DocumentChunk
from app.infrastructure.database import async_session_factory
from app.runtime.rag.embeddings import GeminiEmbeddingProvider
from app.runtime.rag.retrieval import _chunk_text, _seed_documents

# Every domain's models must be imported so SQLAlchemy's mapper registry
# knows about cross-domain foreign keys (e.g. documents.org_id ->
# organizations.id) before the first flush - see app/main.py's own note.
import app.domain.agents.models  # noqa: F401
import app.domain.audit.models  # noqa: F401
import app.domain.auth.models  # noqa: F401
import app.domain.costs.models  # noqa: F401
import app.domain.executions.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
import app.domain.policies.models  # noqa: F401
import app.domain.skills.models  # noqa: F401

_DUMMY_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def _embed_with_retry(embeddings: GeminiEmbeddingProvider, text: str, attempts: int = 4) -> list[float]:
    """The free-tier embeddings endpoint shares a per-minute request quota
    with every other Gemini call this project makes (chat included) - a 429
    here is transient, not a real failure, so back off and retry rather than
    aborting the whole ingestion run."""
    for attempt in range(1, attempts + 1):
        try:
            return await embeddings.embed(text)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429 or attempt == attempts:
                raise
            wait_seconds = 20 * attempt
            print(f"  [rate limited] retrying in {wait_seconds}s (attempt {attempt}/{attempts})")
            await asyncio.sleep(wait_seconds)
    raise RuntimeError("unreachable")


async def main() -> None:
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set - copy backend/.env.example to backend/.env and fill it in.")
        return

    embeddings = GeminiEmbeddingProvider(api_key=api_key)

    async with async_session_factory() as session:
        for doc, text in _seed_documents():
            existing = await session.execute(select(Document).where(Document.title == doc.title))
            if existing.scalar_one_or_none() is not None:
                print(f"[skip] '{doc.title}' already ingested")
                continue

            db_document = Document(
                id=uuid.uuid4(),
                org_id=_DUMMY_ORG_ID,
                title=doc.title,
                source="seed",
                access_scope=sorted(doc.access_scope),
            )
            session.add(db_document)

            chunks = _chunk_text(text, chunk_size_words=80, overlap_words=15)
            for index, chunk_text in enumerate(chunks):
                vector = await _embed_with_retry(embeddings, chunk_text)
                session.add(
                    DocumentChunk(
                        id=uuid.uuid4(),
                        document=db_document,
                        content=chunk_text,
                        embedding=vector,
                        chunk_index=index,
                    )
                )
            print(f"[ingested] '{doc.title}' - {len(chunks)} chunk(s)")

        await session.commit()

    print("done")


if __name__ == "__main__":
    asyncio.run(main())

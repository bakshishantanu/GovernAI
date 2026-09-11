from __future__ import annotations

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_document_service, get_embedding_provider
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.document import DocumentResponse
from app.domain.auth.middleware import get_current_user
from app.domain.documents.repository import DocumentRepository
from app.domain.documents.service import (
    DocumentIngestionService,
    DocumentNotFound,
    UploadRejected,
)
from app.infrastructure.database import async_session_factory
from app.runtime.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

#: What an uploaded document is visible as. Hardcoded for now to match the
#: single scope the Document Search skill is registered with
#: (`permitted_scopes={"public"}` in domain/skills/registry.py). Letting a
#: user pick a scope the skill cannot read would produce documents that are
#: silently unsearchable, which is worse than not offering the choice.
DEFAULT_ACCESS_SCOPE = ["public"]


async def _ingest_in_background(
    document_id: UUID, data: bytes, embedding_provider: EmbeddingProvider | None
) -> None:
    """Run ingestion on a session this task owns.

    The request's session is closed as soon as its response is sent, so the
    work that happens afterwards must open its own - the same reasoning as
    api/execution_runner.py. Commit is here rather than in the service so the
    service stays usable from a request that wants to manage its own
    transaction.
    """
    try:
        async with async_session_factory() as session:
            service = DocumentIngestionService(
                repo=DocumentRepository(session), embedding_provider=embedding_provider
            )
            await service.ingest(document_id, data)
            await session.commit()
    except Exception:
        # Nothing awaits this task, so an escaping exception would be
        # swallowed and the row would sit at PROCESSING forever while the
        # console polls it. Record the failure on a session of its own, since
        # the failure may have been the first session.
        logger.exception("Background ingestion crashed for document %s", document_id)
        await _mark_failed(document_id, "Ingestion crashed unexpectedly.")


async def _mark_failed(document_id: UUID, message: str) -> None:
    try:
        async with async_session_factory() as session:
            repo = DocumentRepository(session)
            document = await repo.get_document_meta(document_id)
            if document is not None:
                document.status = "FAILED"
                document.error = message
                await session.commit()
    except Exception:
        logger.exception("Could not record ingestion failure for %s", document_id)


@router.post("/", response_model=Envelope[DocumentResponse], status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    # Optional, because a filename is a poor title and this is the string
    # every citation displays: "_10-K-2025-As-Filed.pdf" becomes "10 K 2025 As
    # Filed", where "Apple FY2025 10-K" is what a reader wants to see.
    title: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: DocumentIngestionService = Depends(get_document_service),
    embedding_provider: EmbeddingProvider | None = Depends(get_embedding_provider),
):
    """Accept a document and start ingesting it.

    Returns 202 immediately with the row at PENDING. Extracting, chunking and
    embedding a long document takes minutes, far past any sensible request
    timeout, so the console polls `GET /documents/` until this reaches READY
    or FAILED.
    """
    data = await file.read()

    try:
        document = await service.create_upload(
            org_id=user.org_id,
            uploaded_by=user.id,
            filename=file.filename or "untitled",
            mime_type=file.content_type,
            size_bytes=len(data),
            access_scope=DEFAULT_ACCESS_SCOPE,
            title=(title or "").strip() or None,
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Committed before the background task starts: that task opens its own
    # session and would not find the row otherwise.
    await db.commit()
    await db.refresh(document)

    background_tasks.add_task(
        _ingest_in_background,
        document_id=document.id,
        data=data,
        embedding_provider=embedding_provider,
    )
    return Envelope(data=DocumentResponse.from_document(document))


@router.get("/", response_model=Envelope[list[DocumentResponse]])
async def list_documents(
    user: CurrentUser = Depends(get_current_user),
    service: DocumentIngestionService = Depends(get_document_service),
):
    """Every document in the caller's org, newest first.

    Not scoped per user: a document uploaded by anyone in the org is
    searchable by every agent in that org, so hiding it from the list while
    an agent can still quote it would be misleading.
    """
    documents = await service.list_documents(user.org_id)
    return Envelope(data=[DocumentResponse.from_document(d) for d in documents])


@router.get("/{document_id}", response_model=Envelope[DocumentResponse])
async def get_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: DocumentIngestionService = Depends(get_document_service),
):
    """One document's current state. This is the polling target after upload."""
    try:
        document = await service.get_document(document_id, user.org_id)
    except DocumentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return Envelope(data=DocumentResponse.from_document(document))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: DocumentIngestionService = Depends(get_document_service),
):
    """Delete a document and every chunk built from it."""
    try:
        await service.delete_document(document_id, user.org_id)
    except DocumentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.commit()

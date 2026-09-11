"""Turning an uploaded file into searchable, citable chunks.

Ingestion cannot happen inside the upload request. Extracting ~120 pages,
chunking them and embedding every chunk takes minutes, so `create_upload`
records the file and returns straight away, and `ingest` runs afterwards on a
session of its own, moving the row PENDING -> PROCESSING -> READY or FAILED.

That split is why `ingest` opens its own session rather than borrowing the
request's: the request's session is closed the moment its response is sent,
and using a closed session raises. This mirrors api/execution_runner.py, which
made the same move for the same reason.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from app.domain.documents.models import Document, DocumentChunk
from app.domain.documents.repository import DocumentRepository
from app.runtime.rag.chunking import chunk_pages
from app.runtime.rag.embeddings import EmbeddingProvider
from app.runtime.rag.extractors import (
    ExtractionFailed,
    UnsupportedFileType,
    detect_format,
    extract,
)

logger = logging.getLogger(__name__)

#: Refused before anything is read into memory. A cap here is the difference
#: between rejecting a file and the process being killed by the OS.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class UploadRejected(Exception):
    """The file cannot be accepted at all: wrong type, empty, or too large."""


class DocumentNotFound(Exception):
    """No such document in this org."""


class DocumentIngestionService:
    def __init__(self, repo: DocumentRepository, embedding_provider: EmbeddingProvider | None):
        self.repo = repo
        self._embeddings = embedding_provider

    async def create_upload(
        self,
        *,
        org_id: UUID,
        uploaded_by: UUID,
        filename: str,
        mime_type: str | None,
        size_bytes: int,
        access_scope: list[str],
        title: str | None = None,
    ) -> Document:
        """Record the file as PENDING. Raises UploadRejected if unusable.

        Validation happens here, before the row exists, so a user is told
        "that file type is not supported" in the response to their upload
        rather than finding a FAILED row some minutes later.
        """
        if size_bytes == 0:
            raise UploadRejected("The file is empty.")
        if size_bytes > MAX_UPLOAD_BYTES:
            raise UploadRejected(
                f"File is {size_bytes // (1024 * 1024)} MB; the limit is "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        try:
            detect_format(filename, mime_type)
        except UnsupportedFileType as exc:
            raise UploadRejected(str(exc)) from exc

        if self._embeddings is None:
            raise UploadRejected(
                "Document search is not configured on this server (no embedding provider), "
                "so an uploaded file could never be searched."
            )

        document = Document(
            id=uuid4(),
            org_id=org_id,
            title=title or _title_from_filename(filename),
            source="upload",
            access_scope=access_scope,
            filename=filename,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
            status="PENDING",
        )
        await self.repo.create_document(document)
        await self.repo.flush()
        return document

    async def ingest(self, document_id: UUID, data: bytes) -> None:
        """Extract, chunk, embed and store. Records FAILED rather than raising.

        Nothing awaits this, so an escaping exception would be swallowed by
        the event loop and leave the document stuck at PROCESSING forever,
        with the console polling a status that will never change.
        """
        document = await self.repo.get_document_meta(document_id)
        if document is None:
            logger.warning("Document %s vanished before ingestion", document_id)
            return

        try:
            document.status = "PROCESSING"
            await self.repo.flush()

            pages = extract(data, document.filename or "", document.mime_type)
            if not pages:
                raise ExtractionFailed(
                    "No text could be extracted. If this is a scanned document, "
                    "it needs OCR, which is not supported yet."
                )

            chunks = chunk_pages(pages)
            if not chunks:
                raise ExtractionFailed("The document contained no usable text.")

            assert self._embeddings is not None  # guaranteed by create_upload
            vectors = await self._embeddings.embed_batch([c.text for c in chunks])

            await self.repo.add_chunks(
                [
                    DocumentChunk(
                        id=uuid4(),
                        document_id=document.id,
                        content=chunk.text,
                        embedding=vector,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        locator=chunk.locator,
                    )
                    for chunk, vector in zip(chunks, vectors)
                ]
            )

            # Highest numbered page/slide seen, not len(pages): pages with no
            # extractable text are skipped, so counting entries would report a
            # 80-page PDF with 5 image-only pages as 75 pages. None for formats
            # with no page numbering at all (DOCX), where the console should
            # show section count instead of an invented page count.
            numbered = [p.page_number for p in pages if p.page_number is not None]
            document.page_count = max(numbered) if numbered else None
            document.chunk_count = len(chunks)
            document.status = "READY"
            document.error = None
            logger.info(
                "Ingested document %s: %d pages, %d chunks",
                document.id,
                len(pages),
                len(chunks),
            )
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            document.status = "FAILED"
            # Truncated: this is shown in the console, and a full provider
            # traceback in a UI panel helps nobody.
            document.error = str(exc)[:500]

    async def list_documents(self, org_id: UUID) -> list[Document]:
        return await self.repo.list_documents(org_id)

    async def get_document(self, document_id: UUID, org_id: UUID) -> Document:
        document = await self.repo.get_document_meta(document_id)
        # Another org's document reads as missing rather than forbidden;
        # "forbidden" would confirm the id exists.
        if document is None or document.org_id != org_id:
            raise DocumentNotFound(str(document_id))
        return document

    async def delete_document(self, document_id: UUID, org_id: UUID) -> None:
        await self.get_document(document_id, org_id)
        await self.repo.delete_document(document_id)


def _title_from_filename(filename: str) -> str:
    """A readable title, since this is what every citation will show."""
    stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    cleaned = stem.replace("_", " ").replace("-", " ").strip()
    return cleaned or filename

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[str] = mapped_column(Vector(), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    #: 1-based page (or slide) this chunk's text came from, so an answer can
    #: cite "p.32" instead of an opaque chunk number. Nullable because the
    #: seeded demo documents predate uploads and have no page of their own.
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")


#: Ingestion is slower than a request: extracting ~120 pages, chunking, and
#: embedding each chunk takes minutes, so upload returns immediately and the
#: row moves PENDING -> PROCESSING -> READY (or FAILED, with `error` set).
#: The console polls on this rather than holding a connection open.
DOCUMENT_STATUSES = ("PENDING", "PROCESSING", "READY", "FAILED")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    access_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    #: Upload metadata. All nullable so the pre-existing seeded rows, which
    #: were never uploaded by anyone, stay valid without a backfill.
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    uploaded_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'READY'"))
    #: Why ingestion failed, shown to whoever uploaded it. A failed upload that
    #: says nothing is indistinguishable from one still processing.
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    chunks: Mapped[list[DocumentChunk]] = relationship("DocumentChunk", back_populates="document")

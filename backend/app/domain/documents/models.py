from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.infrastructure.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id"))
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[str] = mapped_column(Vector(), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    access_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    
    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document")

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    execution_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource: Mapped[str | None] = mapped_column(String, nullable=True)
    tool: Mapped[str | None] = mapped_column(String, nullable=True)
    policy_decision: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

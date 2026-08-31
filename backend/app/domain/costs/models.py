from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base

class CostEvent(Base):
    __tablename__ = "cost_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"))
    execution_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("executions.id"))
    execution_step_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

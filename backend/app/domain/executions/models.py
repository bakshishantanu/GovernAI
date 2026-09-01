from __future__ import annotations
from typing import Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

class ExecutionStep(Base):
    __tablename__ = "execution_steps"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("executions.id"))
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tool: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tool_args: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    tool_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    
    execution: Mapped["Execution"] = relationship("Execution", back_populates="steps")

class Execution(Base):
    __tablename__ = "executions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"))
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    goal: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    steps: Mapped[list["ExecutionStep"]] = relationship("ExecutionStep", back_populates="execution")

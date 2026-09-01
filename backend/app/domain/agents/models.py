from __future__ import annotations
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

class AgentSkill(Base):
    __tablename__ = "agent_skills"
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"), primary_key=True)

class AgentPassport(Base):
    __tablename__ = "agent_passports"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"))
    compliance_status: Mapped[str] = mapped_column(String, nullable=False)
    compliance_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    agent: Mapped["Agent"] = relationship("Agent", back_populates="passport")
    permissions: Mapped[list["Permission"]] = relationship("Permission", back_populates="passport")

class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"))
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("profiles.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    
    passport: Mapped["AgentPassport"] = relationship("AgentPassport", back_populates="agent", uselist=False)

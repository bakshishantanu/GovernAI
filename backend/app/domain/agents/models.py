from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:  # imported for the string annotations below only.
    # These two modules reference each other's mapped classes. SQLAlchemy
    # resolves the quoted names through its own declarative registry at
    # mapper-configuration time, so a real import would be both unnecessary
    # and circular - but without this, the names are undefined to every
    # linter and type checker reading the file.
    from app.domain.permissions.models import Permission


class AgentSkill(Base):
    __tablename__ = "agent_skills"
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.id"), primary_key=True)

class AgentPassport(Base):
    __tablename__ = "agent_passports"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id"))
    compliance_status: Mapped[str] = mapped_column(String, nullable=False)
    compliance_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    budget_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    agent: Mapped[Agent] = relationship("Agent", back_populates="passport")
    permissions: Mapped[list[Permission]] = relationship("Permission", back_populates="passport")

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

    passport: Mapped[AgentPassport] = relationship("AgentPassport", back_populates="agent", uselist=False)

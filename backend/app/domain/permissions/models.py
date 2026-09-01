from __future__ import annotations
from uuid import UUID, uuid4
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    passport_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agent_passports.id"), index=True)
    permission: Mapped[str] = mapped_column(String, nullable=False)

    passport: Mapped["AgentPassport"] = relationship("AgentPassport", back_populates="permissions")

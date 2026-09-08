from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:  # imported for the string annotations below only.
    # These two modules reference each other's mapped classes. SQLAlchemy
    # resolves the quoted names through its own declarative registry at
    # mapper-configuration time, so a real import would be both unnecessary
    # and circular - but without this, the names are undefined to every
    # linter and type checker reading the file.
    from app.domain.agents.models import AgentPassport


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    passport_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agent_passports.id"), index=True
    )
    permission: Mapped[str] = mapped_column(String, nullable=False)

    passport: Mapped[AgentPassport] = relationship("AgentPassport", back_populates="permissions")

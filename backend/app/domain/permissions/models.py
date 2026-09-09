from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, text
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


class ForbiddenPermissionPair(Base):
    """Two permissions an agent may not hold at the same time — FRD-03 rule 4.

    A table rather than a constant in code, because no source document defines
    what a forbidden combination *is*: it is a project decision, and one that
    should be correctable without a redeploy. `reason` is shown verbatim in the
    violation, so it must read as an explanation rather than a code.

    Order within a pair is not significant — the check tests membership both
    ways — so a rule never needs writing twice.
    """

    __tablename__ = "forbidden_permission_pairs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    permission_a: Mapped[str] = mapped_column(String, nullable=False)
    permission_b: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

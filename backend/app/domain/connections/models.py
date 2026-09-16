from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class ConnectionModel(Base):
    """One org's saved answer to a skill's requirement (see
    app.skills.base.SkillRequirement). Keyed by (org_id, requirement_key)
    rather than by agent: a Jira connection is shared by every agent in the
    org whose skills need it, matching how Zapier/n8n scope integrations to
    the workspace rather than to one automation."""

    __tablename__ = "connections"
    __table_args__ = (
        UniqueConstraint("org_id", "requirement_key", name="uq_connection_org_key"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    requirement_key: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="CONNECTED")
    #: Fernet-encrypted JSON blob of the secret field values. Never sent to
    #: the frontend -- ConnectionResponse only ever carries `preview`.
    encrypted_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Non-secret values worth showing back to the user (e.g. base_url), plus
    #: a masked preview ("****3456") of secret ones. Safe to return as-is.
    preview: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )

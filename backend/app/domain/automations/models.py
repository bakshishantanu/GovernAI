from __future__ import annotations

"""Automations — recipe-style rules: when this happens, do that.

The design constraint that shaped these tables: **every trigger and every
action must be backed by something the platform genuinely does.** An
automation that claims to send an email when no mail infrastructure exists
would be a fiction sitting inside a governance product, which is worse than
not shipping the feature.

So the triggers are read from real rows (`audit_events`, `cost_events`) and
real bus events, and the actions call services that already enforce something
(`KillSwitchService`). "Raise an alert" writes a durable row that the console
reads — it is honestly an in-app record, not a notification.

`AutomationRun` is not optional bookkeeping. In a governance product, a rule
that can suspend an agent has to leave evidence of every time it considered
firing and what it decided, or the platform cannot answer "why was this agent
suspended?" — which is the whole point of the product.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class Automation(Base):
    __tablename__ = "automations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    #: Null means "every agent in the org". A value scopes the rule to one.
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )

    #: TOOL_DENIED | SPEND_THRESHOLD | AGENT_SUSPENDED
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    #: Shape depends on trigger_type; validated by the API schema, not here.
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    #: SUSPEND_AGENT | RAISE_ALERT
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    action_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    runs: Mapped[list["AutomationRun"]] = relationship(
        "AutomationRun", back_populates="automation"
    )


class AutomationRun(Base):
    """One evaluation of one automation, and what it did about it."""

    __tablename__ = "automation_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    automation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("automations.id"), nullable=False
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    #: FIRED | SKIPPED | FAILED. SKIPPED is recorded too — knowing a rule
    #: considered an agent and decided not to act is evidence, not noise.
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    #: Plain-English account of what was observed and decided.
    detail: Mapped[str] = mapped_column(String, nullable=False, default="")
    #: The measurements behind the decision, so a run can be audited later.
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    automation: Mapped["Automation"] = relationship("Automation", back_populates="runs")

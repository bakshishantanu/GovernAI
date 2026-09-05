from __future__ import annotations

"""Data access for automations and their run history."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.automations.models import Automation, AutomationRun


class AutomationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_automations(self, org_id: UUID) -> list[Automation]:
        result = await self.session.execute(
            select(Automation)
            .where(Automation.org_id == org_id)
            .order_by(Automation.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_enabled(self, org_id: UUID | None = None) -> list[Automation]:
        """Enabled automations, optionally narrowed to one org.

        The engine calls this for every event, so it selects only what it
        needs and never eager-loads the run history.
        """
        stmt = select(Automation).where(Automation.enabled.is_(True))
        if org_id is not None:
            stmt = stmt.where(Automation.org_id == org_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_automation(self, automation_id: UUID) -> Automation | None:
        result = await self.session.execute(
            select(Automation)
            .options(selectinload(Automation.runs))
            .where(Automation.id == automation_id)
        )
        return result.scalar_one_or_none()

    def add(self, automation: Automation) -> Automation:
        self.session.add(automation)
        return automation

    async def delete(self, automation: Automation) -> None:
        await self.session.delete(automation)

    def record_run(self, run: AutomationRun) -> AutomationRun:
        self.session.add(run)
        return run

    async def list_runs(
        self, org_id: UUID, automation_id: UUID | None = None, limit: int = 50
    ) -> list[AutomationRun]:
        stmt = (
            select(AutomationRun)
            .where(AutomationRun.org_id == org_id)
            .order_by(AutomationRun.triggered_at.desc())
            .limit(limit)
        )
        if automation_id is not None:
            stmt = stmt.where(AutomationRun.automation_id == automation_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_runs_since(self, automation_id: UUID, agent_id: UUID, since) -> int:
        """How many times this rule has already fired for this agent recently.

        Used to stop a rule firing again and again on the same condition — a
        denial storm should suspend an agent once, not write fifty rows.
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(AutomationRun.id))
            .where(AutomationRun.automation_id == automation_id)
            .where(AutomationRun.agent_id == agent_id)
            .where(AutomationRun.outcome == "FIRED")
            .where(AutomationRun.triggered_at >= since)
        )
        return int(result.scalar_one() or 0)

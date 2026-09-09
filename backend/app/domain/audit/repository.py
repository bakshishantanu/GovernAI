from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agents.models import Agent
from app.domain.audit.models import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_event(self, event: AuditEvent) -> AuditEvent:
        self.session.add(event)
        return event

    async def count_tool_calls_since(self, agent_id: UUID, since: datetime) -> int:
        """How many tool calls this agent has made since `since`.

        Counts attempts, not successes: a denied call is still a call, and a
        rate limit that only counted the allowed ones could be evaded by
        hammering a tool the agent has no permission for.
        """
        result = await self.session.execute(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.agent_id == agent_id,
                AuditEvent.action == "tool_call",
                AuditEvent.timestamp >= since,
            )
        )
        return result.scalar_one()

    async def get_events_for_org(
        self,
        org_id: UUID,
        limit: int = 50,
        cursor: UUID | None = None,
        builder_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).where(AuditEvent.org_id == org_id)

        # A builder sees events for agents they own; a user, events for agents
        # assigned to them. Either also sees events they themselves caused,
        # which is why actor_id is OR-ed in rather than replaced.
        if builder_id or assigned_user_id:
            query = query.outerjoin(Agent, AuditEvent.agent_id == Agent.id)
            user_id = builder_id or assigned_user_id
            conditions = [AuditEvent.actor_id == user_id]
            if builder_id:
                conditions.append(Agent.owner_id == builder_id)
            if assigned_user_id:
                conditions.append(Agent.assigned_user_id == assigned_user_id)
            query = query.where(or_(*conditions))

        query = query.order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())

        if cursor:
            # Composite cursor: (timestamp, id) so rows sharing a timestamp are never skipped
            cursor_result = await self.session.execute(
                select(AuditEvent.timestamp, AuditEvent.id).where(AuditEvent.id == cursor)
            )
            cursor_row = cursor_result.one_or_none()
            if cursor_row:
                cursor_ts, cursor_id = cursor_row
                from sqlalchemy import tuple_

                query = query.where(
                    tuple_(AuditEvent.timestamp, AuditEvent.id) < tuple_(cursor_ts, cursor_id)
                )

        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

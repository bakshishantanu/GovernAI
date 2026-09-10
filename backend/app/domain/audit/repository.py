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
        execution_id: UUID | None = None,
    ) -> list[AuditEvent]:

        query = select(AuditEvent).where(AuditEvent.org_id == org_id)

        # Narrowing to one run: the caller (the execution timeline endpoint)
        # has already authorized access to this specific execution, so this
        # deliberately does *not* also apply the ownership OR-filter below — a
        # user allowed to view their own run's timeline sees every governance
        # event on it, not only the ones they personally triggered.
        #
        # Because of that, this parameter must stay internal: it is reachable
        # only through a route that authorizes the execution first. Exposing it
        # as a query param on the public /audits route would let any org member
        # read another user's run by guessing an id.
        if execution_id is not None:
            query = query.where(AuditEvent.execution_id == execution_id)

        elif builder_id or assigned_user_id:
            query = query.outerjoin(Agent, AuditEvent.agent_id == Agent.id)
            conditions = []
            if builder_id:
                conditions.append(AuditEvent.actor_id == builder_id)
                conditions.append(Agent.owner_id == builder_id)
            if assigned_user_id:
                conditions.append(AuditEvent.actor_id == assigned_user_id)
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

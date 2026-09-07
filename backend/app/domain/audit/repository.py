from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.audit.models import AuditEvent

class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_event(self, event: AuditEvent) -> AuditEvent:
        self.session.add(event)
        return event
        
    async def get_events_for_org(self, org_id: UUID, limit: int = 50, cursor: UUID | None = None) -> list[AuditEvent]:
        query = (
            select(AuditEvent)
            .where(AuditEvent.org_id == org_id)
            .order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
        )
        
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

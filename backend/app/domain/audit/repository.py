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
        query = select(AuditEvent).where(AuditEvent.org_id == org_id).order_by(AuditEvent.timestamp.desc())
        
        if cursor:
            # For cursor pagination, we find the timestamp of the cursor event and fetch events older than it
            cursor_result = await self.session.execute(select(AuditEvent.timestamp).where(AuditEvent.id == cursor))
            cursor_ts = cursor_result.scalar_one_or_none()
            if cursor_ts:
                query = query.where(AuditEvent.timestamp < cursor_ts)
                
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

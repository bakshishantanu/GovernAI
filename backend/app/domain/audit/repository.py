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
        
    async def get_events_for_org(self, org_id: UUID) -> list[AuditEvent]:
        result = await self.session.execute(
            select(AuditEvent).where(AuditEvent.org_id == org_id).order_by(AuditEvent.timestamp.desc())
        )
        return list(result.scalars().all())

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.connections.models import ConnectionModel


class ConnectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_org(self, org_id: UUID) -> list[ConnectionModel]:
        stmt = select(ConnectionModel).where(ConnectionModel.org_id == org_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, org_id: UUID, requirement_key: str) -> ConnectionModel | None:
        stmt = select(ConnectionModel).where(
            ConnectionModel.org_id == org_id,
            ConnectionModel.requirement_key == requirement_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, connection: ConnectionModel) -> ConnectionModel:
        existing = await self.get(connection.org_id, connection.requirement_key)
        if existing:
            existing.type = connection.type
            existing.label = connection.label
            existing.status = connection.status
            existing.encrypted_secret = connection.encrypted_secret
            existing.preview = connection.preview
            return existing
        self.session.add(connection)
        return connection

    async def delete(self, org_id: UUID, requirement_key: str) -> bool:
        existing = await self.get(org_id, requirement_key)
        if not existing:
            return False
        await self.session.delete(existing)
        return True

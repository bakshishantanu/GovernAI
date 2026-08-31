from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.permissions.models import Permission

class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_permissions_for_passport(self, passport_id: UUID) -> list[Permission]:
        result = await self.session.execute(select(Permission).where(Permission.passport_id == passport_id))
        return list(result.scalars().all())

    async def create_permission(self, permission: Permission) -> Permission:
        self.session.add(permission)
        return permission

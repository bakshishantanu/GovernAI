from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.permissions.models import ForbiddenPermissionPair, Permission


class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_permissions_for_passport(self, passport_id: UUID) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.passport_id == passport_id)
        )
        return list(result.scalars().all())

    async def create_permission(self, permission: Permission) -> Permission:
        self.session.add(permission)
        return permission

    async def list_forbidden_pairs(self) -> list[tuple[str, str, str]]:
        """Enabled forbidden pairs, as (permission_a, permission_b, reason).

        Disabled rows are filtered here rather than inside the compliance
        check, so that check stays a pure function over the data it is handed.
        """
        result = await self.session.execute(
            select(ForbiddenPermissionPair).where(ForbiddenPermissionPair.enabled.is_(True))
        )
        return [(r.permission_a, r.permission_b, r.reason) for r in result.scalars().all()]

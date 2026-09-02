from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.skills.models import SkillModel, ToolModel

class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_skill(self, skill_id: str) -> SkillModel | None:
        stmt = (
            select(SkillModel)
            .options(selectinload(SkillModel.tools), selectinload(SkillModel.permissions))
            .where(SkillModel.id == skill_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_skills(self) -> list[SkillModel]:
        stmt = (
            select(SkillModel)
            .options(selectinload(SkillModel.tools), selectinload(SkillModel.permissions))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

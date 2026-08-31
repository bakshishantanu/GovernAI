from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.skills.models import SkillModel, ToolModel

class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_skill(self, skill_id: str) -> SkillModel | None:
        result = await self.session.execute(select(SkillModel).where(SkillModel.id == skill_id))
        return result.scalar_one_or_none()

    async def list_skills(self) -> list[SkillModel]:
        result = await self.session.execute(select(SkillModel))
        return list(result.scalars().all())

from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.skills.models import SkillModel, ToolModel
from app.domain.skills.repository import SkillRepository
from app.skills.ticketing import TicketingSkill
from app.skills.sql_query import SqlQuerySkill

class SkillRegistry:
    def __init__(self, skill_repo: SkillRepository, session: AsyncSession):
        self.skill_repo = skill_repo
        self.session = session

    async def bootstrap(self):
        # In a real app, this scans all classes inheriting from BaseSkill.
        # For now, we manually register TicketingSkill (FRD-05).
        skills_to_register = [
            TicketingSkill(),
            SqlQuerySkill(permitted_tables={"tickets", "internal_payroll"})
        ]
        
        for skill_class in skills_to_register:
            existing = await self.skill_repo.get_skill("ticketing")
            if not existing:
                db_skill = SkillModel(
                    id="ticketing",
                    name=skill_class.name,
                    display_name=skill_class.display_name,
                    description=skill_class.description,
                    version=skill_class.version,
                    trust_level=skill_class.trust_level
                )
                self.session.add(db_skill)
            
                for tool in skill_class.get_tools():
                    db_tool = ToolModel(
                        skill=db_skill,
                        name=tool.name,
                        description=tool.description,
                        required_permission=getattr(tool, 'required_permission', '')
                )
                    self.session.add(db_tool)

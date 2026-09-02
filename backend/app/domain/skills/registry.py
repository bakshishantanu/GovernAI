from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skills.models import SkillModel, SkillPermission, ToolModel
from app.domain.skills.repository import SkillRepository
from app.skills.base import BaseTool
from app.skills.document_search import DocumentSearchSkill
from app.skills.sql_query import SqlQuerySkill
from app.skills.ticketing import TicketingSkill


class SkillRegistry:
    def __init__(self, skill_repo: SkillRepository, session: AsyncSession):
        self.skill_repo = skill_repo
        self.session = session
        # In a real app, this scans all classes inheriting from BaseSkill.
        # For now, we manually register the MVP skills (FRD-05).
        self._instances = {
            skill.name: skill
            for skill in (
                TicketingSkill(),
                SqlQuerySkill(permitted_tables={"tickets", "internal_payroll"}),
                DocumentSearchSkill(permitted_scopes={"public"}),
            )
        }

    def get_tools(self, skill_ids: list[str]) -> list[BaseTool]:
        """Resolves an agent's bound skill ids into the tool list its LangGraph
        run should expose (FRD-06). A skill_id with no matching registered
        instance is skipped rather than raising -- binding already validates
        the id exists in the DB at agent-creation time (see AgentService),
        so this only happens if a skill was deregistered afterward."""
        tools: list[BaseTool] = []
        for skill_id in skill_ids:
            skill = self._instances.get(skill_id)
            if skill is not None:
                tools.extend(skill.get_tools())
        return tools

    async def bootstrap(self):
        for skill_class in self._instances.values():
            existing = await self.skill_repo.get_skill(skill_class.name)
            if existing:
                continue

            db_skill = SkillModel(
                id=skill_class.name,
                name=skill_class.name,
                display_name=skill_class.display_name,
                description=skill_class.description,
                version=skill_class.version,
                trust_level=skill_class.trust_level,
            )
            self.session.add(db_skill)

            for permission in skill_class.required_permissions:
                self.session.add(SkillPermission(skill=db_skill, permission=permission))

            for tool in skill_class.get_tools():
                db_tool = ToolModel(
                    skill=db_skill,
                    name=tool.name,
                    description=tool.description,
                    required_permission=tool.required_permission,
                )
                self.session.add(db_tool)

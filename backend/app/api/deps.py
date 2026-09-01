from __future__ import annotations
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.domain.agents.repository import AgentRepository
from app.domain.permissions.repository import PermissionRepository
from app.domain.skills.repository import SkillRepository
from app.domain.agents.service import AgentService

async def get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    agent_repo = AgentRepository(db)
    perm_repo = PermissionRepository(db)
    skill_repo = SkillRepository(db)
    return AgentService(agent_repo=agent_repo, perm_repo=perm_repo, skill_repo=skill_repo)

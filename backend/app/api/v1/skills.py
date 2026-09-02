from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_db
from app.domain.auth.middleware import get_current_user
from app.api.schemas.skill import SkillResponse
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.domain.skills.repository import SkillRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/skills", tags=["skills"])

def get_skill_repo(db: AsyncSession = Depends(get_db)) -> SkillRepository:
    return SkillRepository(db)


@router.get("/", response_model=Envelope[list[SkillResponse]])
async def list_skills(
    current_user: CurrentUser = Depends(get_current_user),
    repo: SkillRepository = Depends(get_skill_repo)
):
    """
    List all available skills that can be assigned to an agent.
    Skills represent sets of tools (e.g. Ticketing, SQL, Document Search).
    """
    skills = await repo.list_skills()
    return Envelope(data=skills)


@router.get("/{skill_id}", response_model=Envelope[SkillResponse])
async def get_skill(
    skill_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    repo: SkillRepository = Depends(get_skill_repo)
):
    """
    Get detailed information about a specific skill, including its tools 
    and required permissions.
    """
    skill = await repo.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
        
    return Envelope(data=skill)

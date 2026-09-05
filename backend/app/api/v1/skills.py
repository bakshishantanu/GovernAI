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


def _to_response(skill) -> SkillResponse:
    """Map a stored skill onto the API shape.

    `SkillResponse.required_permissions` carries a validator that turns
    `SkillPermission` rows into strings, but it never ran: with
    `from_attributes` pydantic looks for an attribute literally named
    `required_permissions`, and the ORM relationship is called `permissions`.
    The field silently fell back to its `[]` default, so every skill claimed to
    grant no permissions at all — which is the opposite of the point, since an
    agent's permissions are the union of its skills'.
    """
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        display_name=skill.display_name,
        description=skill.description,
        version=skill.version,
        trust_level=skill.trust_level,
        tools=skill.tools,
        required_permissions=[p.permission for p in (skill.permissions or [])],
    )


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
    return Envelope(data=[_to_response(s) for s in skills])


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
        
    return Envelope(data=_to_response(skill))

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_agent_service,
    get_audit_service,
    get_db,
    get_kill_switch_service,
)
from app.api.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentSkillRef,
    AgentUpdate,
)
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope, PaginatedResponse
from app.domain.agents.kill_switch import KillSwitchService
from app.domain.agents.models import AgentSkill
from app.domain.agents.service import (
    AgentService,
    ComplianceError,
    InvalidStateTransitionError,
    SkillNotFoundError,
)
from app.domain.audit.service import AuditService
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_admin, require_builder_or_admin
from app.domain.skills.models import SkillModel

router = APIRouter(prefix="/agents", tags=["agents"])


async def _skills_for(db: AsyncSession, agent_ids: list[UUID]) -> dict[UUID, list[AgentSkillRef]]:
    """Skill refs for several agents in one query, keyed by agent id.

    One statement for the whole page rather than one per agent — the agents
    board can list up to 200 rows at a time.
    """
    if not isinstance(db, AsyncSession) or not agent_ids:
        return {}

    rows = await db.execute(
        select(AgentSkill.agent_id, SkillModel.id, SkillModel.display_name)
        .join(SkillModel, SkillModel.id == AgentSkill.skill_id)
        .where(AgentSkill.agent_id.in_(agent_ids))
    )

    by_agent: dict[UUID, list[AgentSkillRef]] = {}
    for agent_id, skill_id, display_name in rows.all():
        by_agent.setdefault(agent_id, []).append(AgentSkillRef(id=skill_id, name=display_name))
    return by_agent


def _with_skills(agent, skills_by_agent: dict[UUID, list[AgentSkillRef]]) -> AgentResponse:
    response = AgentResponse.model_validate(agent)
    response.skills = skills_by_agent.get(agent.id, [])
    return response


@router.post("/", response_model=Envelope[AgentResponse])
async def create_agent(
    payload: AgentCreate,
    user: CurrentUser = Depends(require_builder_or_admin),
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent draft."""
    assigned_user_id = payload.assigned_user_id
    if payload.request_id and not assigned_user_id:
        from app.domain.agent_requests.repository import AgentRequestRepository

        req_repo = AgentRequestRepository(service.agent_repo.session)
        req = await req_repo.get_request(payload.request_id)
        if req:
            assigned_user_id = req.requester_id

    try:
        agent = await service.create_agent(
            org_id=user.org_id,
            owner_id=user.id,
            name=payload.name,
            description=payload.description,
            skill_ids=payload.skills,
            request_id=payload.request_id,
            assigned_user_id=assigned_user_id,
        )
        if isinstance(db, AsyncSession):
            await db.commit()
    except SkillNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    skills = await _skills_for(db, [agent.id]) if isinstance(db, AsyncSession) else {}
    return Envelope(data=_with_skills(agent, skills))


@router.get("/", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    user: CurrentUser = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db),
):
    """List agents. Admin sees every agent in the org. A user sees agents they
    built (owner) or that were handed to them (assigned) — the two are not
    mutually exclusive for the same person, so this is an OR, not a role
    branch."""
    owner_id = user.id if user.is_builder else None
    assigned_user_id = user.id if user.is_builder else None

    agents = await service.agent_repo.list_agents_by_org(
        user.org_id,
        limit=limit,
        offset=offset,
        owner_id=owner_id,
        assigned_user_id=assigned_user_id,
    )
    count = await service.agent_repo.count_agents_by_org(
        user.org_id, owner_id=owner_id, assigned_user_id=assigned_user_id
    )

    # Built explicitly so the passport and the skills are both included; one
    # skills query covers the whole page rather than one per row.
    skills = await _skills_for(db, [a.id for a in agents])
    return PaginatedResponse(
        data=[_with_skills(a, skills) for a in agents],
        meta={"has_more": offset + limit < count, "total": count},
    )


@router.get("/{agent_id}", response_model=Envelope[AgentResponse])
async def get_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db),
):
    """Get specific agent details."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 404 rather than 403 outside the caller's scope: a 403 would confirm the
    # agent exists. Owner or assignee (not a role branch — the same person
    # can be either, or both, for different agents).
    if user.role != "admin" and user.id not in (agent.owner_id, agent.assigned_user_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    skills = await _skills_for(db, [agent.id])
    return Envelope(data=_with_skills(agent, skills))


@router.patch("/{agent_id}/submit", response_model=Envelope[AgentResponse])
async def submit_agent_for_review(
    agent_id: UUID,
    user: CurrentUser = Depends(require_builder_or_admin),
    service: AgentService = Depends(get_agent_service),
    audit: AuditService = Depends(get_audit_service),
    db: AsyncSession = Depends(get_db),
):
    """Submit a draft agent for governance review."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Build actions (submit/activate/edit) are an owner-only privilege, not
    # widened to "or assigned" — being handed an agent to *use* is not the
    # same as being allowed to edit its definition.
    if user.role != "admin" and agent.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this agent")

    try:
        await service.submit_for_review(agent_id)
        # FRD-02: an audit event after every compliance attempt, not only the
        # refusals. A log that records what was stopped and not what was let
        # through cannot answer "who approved this agent, and when".
        await audit.log_compliance_passed(user.org_id, user.id, agent_id)
        if isinstance(db, AsyncSession):
            await db.commit()
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ComplianceError as e:
        await audit.log_compliance_failed(user.org_id, user.id, agent_id, e.violations)

        # Commit the FAILED verdict and the audit row before reporting them. The
        # service writes compliance_status and compliance_checked_at on the way
        # out; without a commit here the session is discarded with the exception
        # and the passport would still read PENDING, so the console could never
        # show that a check had been run and refused - and an audit trail that
        # records only successes is worse than none.
        if isinstance(db, AsyncSession):
            await db.commit()

        # Every violation, not just the first: FRD-02 requires the builder be
        # shown what is wrong, and an agent told only "no" cannot be fixed by
        # whoever built it. `message` keeps the response readable to any client
        # that only reads `detail.message`.
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This agent does not pass the compliance check.",
                "violations": [{"rule": v.rule, "message": v.message} for v in e.violations],
            },
        )

    # Reload agent to get the updated status
    updated_agent = await service.agent_repo.get_agent(agent_id)
    skills = await _skills_for(db, [updated_agent.id]) if isinstance(db, AsyncSession) else {}
    return Envelope(data=_with_skills(updated_agent, skills))


@router.patch("/{agent_id}/activate", response_model=Envelope[AgentResponse])
async def activate_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(require_builder_or_admin),
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_db),
):
    """Activate an approved agent."""
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    if user.role != "admin" and agent.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to activate this agent")

    try:
        await service.activate_agent(agent_id)
        if isinstance(db, AsyncSession):
            await db.commit()
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reload agent to get the updated status
    updated_agent = await service.agent_repo.get_agent(agent_id)
    skills = await _skills_for(db, [updated_agent.id]) if isinstance(db, AsyncSession) else {}
    return Envelope(data=_with_skills(updated_agent, skills))


@router.patch("/{agent_id}", response_model=Envelope[AgentResponse])
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    user: CurrentUser = Depends(require_builder_or_admin),
    db: AsyncSession = Depends(get_db),
    service: AgentService = Depends(get_agent_service),
):
    """Edit an agent's name and description.

    Skills are deliberately **not** editable here. An agent's permissions are
    the union of its skills (FRD-02), so changing them after activation would
    silently widen what it may do without re-running the compliance check.
    There is no re-review flow yet, so the request is refused rather than
    quietly letting permissions drift.
    """
    agent = await service.agent_repo.get_agent(agent_id)
    if not agent or agent.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    if user.role != "admin" and agent.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this agent")

    if payload.skills is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Skills cannot be changed after creation: an agent's permissions "
                "are derived from its skills and would bypass the compliance check. "
                "Create a new agent with the skills you need."
            ),
        )

    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description

    await db.commit()
    refreshed = await service.agent_repo.get_agent(agent_id)
    skills = await _skills_for(db, [refreshed.id])
    return Envelope(data=_with_skills(refreshed, skills))


@router.post("/{agent_id}/kill", response_model=Envelope[AgentResponse])
async def kill_agent(
    agent_id: UUID,
    reason: str = Body("Kill switch activated by an administrator", embed=True),
    user: CurrentUser = Depends(require_admin),
    service: AgentService = Depends(get_agent_service),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    db: AsyncSession = Depends(get_db),
):
    """Stop an agent immediately (FRD-12).

    Suspends the agent and its passport together, and writes the audit entry.
    Any run in flight stops at its next tool call, because the governance gate
    reads the passport before every call and will now find it suspended.
    """
    try:
        await kill_switch.suspend_agent(
            agent_id=agent_id, actor_id=user.id, org_id=user.org_id, reason=reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    agent = await service.agent_repo.get_agent(agent_id)
    skills = await _skills_for(db, [agent.id])
    return Envelope(data=_with_skills(agent, skills))


@router.post("/{agent_id}/reactivate", response_model=Envelope[AgentResponse])
async def reactivate_agent(
    agent_id: UUID,
    reason: str = Body("Reactivated by an administrator", embed=True),
    user: CurrentUser = Depends(require_admin),
    service: AgentService = Depends(get_agent_service),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    db: AsyncSession = Depends(get_db),
):
    """Bring a suspended agent back. Never automatic — FRD-12 requires a person."""
    try:
        await kill_switch.reactivate_agent(
            agent_id=agent_id, actor_id=user.id, org_id=user.org_id, reason=reason
        )
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=detail)

    agent = await service.agent_repo.get_agent(agent_id)
    skills = await _skills_for(db, [agent.id])
    return Envelope(data=_with_skills(agent, skills))

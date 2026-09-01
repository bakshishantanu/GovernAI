from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.repository import AgentRepository
from app.domain.permissions.repository import PermissionRepository
from app.domain.skills.repository import SkillRepository

class ComplianceError(Exception):
    pass

class InvalidStateTransitionError(Exception):
    pass

class SkillNotFoundError(Exception):
    pass

class AgentService:
    def __init__(self, agent_repo: AgentRepository, perm_repo: PermissionRepository, skill_repo: SkillRepository):
        self.agent_repo = agent_repo
        self.perm_repo = perm_repo
        self.skill_repo = skill_repo

    async def create_agent(self, org_id: UUID, owner_id: UUID, name: str, description: str, skill_ids: list[str] | None = None) -> Agent:
        skill_ids = skill_ids or []
        for skill_id in skill_ids:
            if not await self.skill_repo.get_skill(skill_id):
                raise SkillNotFoundError(f"Skill '{skill_id}' does not exist")

        agent = Agent(
            id=uuid4(),
            org_id=org_id,
            owner_id=owner_id,
            name=name,
            description=description,
            status="DRAFT"
        )
        await self.agent_repo.create_agent(agent)

        for skill_id in skill_ids:
            await self.agent_repo.add_skill(agent.id, skill_id)

        passport = AgentPassport(
            id=uuid4(),
            agent_id=agent.id,
            agent=agent,
            compliance_status="PENDING",
            lifecycle_state="DRAFT"
        )
        await self.agent_repo.create_passport(passport)
        await self.agent_repo.flush()

        # Re-fetch rather than return the in-memory objects: created_at/
        # updated_at are DB server_defaults, and flushing a fresh object
        # doesn't reliably leave its relationship collections (e.g.
        # passport.permissions) in a loaded state under async SQLAlchemy --
        # accessing them later can trigger a lazy-load outside of a
        # greenlet context (MissingGreenlet). A clean reload via the same
        # eager-loaded query every other read path uses avoids all of that.
        return await self.agent_repo.get_agent(agent.id)

    async def submit_for_review(self, agent_id: UUID) -> AgentPassport:
        agent = await self.agent_repo.get_agent(agent_id)
        if not agent or not agent.passport:
            raise ValueError("Agent or passport not found")

        if agent.passport.lifecycle_state != "DRAFT":
            raise InvalidStateTransitionError("Only DRAFT agents can be submitted for review")

        # Basic compliance check (FRD-03)
        if not agent.owner_id:
            agent.passport.compliance_status = "FAILED"
            raise ComplianceError("Agent must have an owner")

        # In a full implementation, we'd check if requested permissions are a subset of bound skills here.

        agent.passport.compliance_status = "PASSED"
        agent.passport.compliance_checked_at = datetime.now(timezone.utc)
        agent.passport.lifecycle_state = "APPROVED"
        return agent.passport

    async def activate_agent(self, agent_id: UUID) -> Agent:
        agent = await self.agent_repo.get_agent(agent_id)
        if not agent or not agent.passport:
            raise ValueError("Agent or passport not found")
        if agent.passport.lifecycle_state != "APPROVED":
            raise InvalidStateTransitionError("Only APPROVED agents can be activated")
        agent.status = "ACTIVE"
        agent.passport.lifecycle_state = "ACTIVE"
        return agent

    async def suspend_agent(self, agent_id: UUID) -> Agent:
        agent = await self.agent_repo.get_agent(agent_id)
        agent.status = "SUSPENDED"
        agent.passport.lifecycle_state = "SUSPENDED"
        return agent

    async def revoke_agent(self, agent_id: UUID) -> Agent:
        agent = await self.agent_repo.get_agent(agent_id)
        agent.status = "REVOKED"
        agent.passport.lifecycle_state = "REVOKED"
        return agent

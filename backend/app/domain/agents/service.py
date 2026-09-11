from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.agents.compliance import Violation, check_compliance
from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.repository import AgentRepository
from app.domain.permissions.models import Permission
from app.domain.permissions.repository import PermissionRepository
from app.domain.skills.repository import SkillRepository


class ComplianceError(Exception):
    """One or more of FRD-03's four rules were broken.

    Carries the violations rather than only a sentence, because FRD-02 requires
    the builder be told everything that is wrong — the API turns them into a
    structured response, and `str()` stays readable for logs and for any caller
    that only wants a message.
    """

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        super().__init__(" ".join(v.message for v in violations))


class InvalidStateTransitionError(Exception):
    pass


class SkillNotFoundError(Exception):
    pass


class AgentService:
    def __init__(
        self,
        agent_repo: AgentRepository,
        perm_repo: PermissionRepository,
        skill_repo: SkillRepository,
    ):
        self.agent_repo = agent_repo
        self.perm_repo = perm_repo
        self.skill_repo = skill_repo

    async def _permissions_for_skills(self, skill_ids: list[str]) -> list[str]:
        """The union of the permissions declared by these skills.

        This is the ceiling an agent's passport may not exceed (FRD-02), and —
        because the console offers no way to ask for less — it is also exactly
        what a new agent is granted.
        """
        permissions: set[str] = set()
        for skill_id in skill_ids:
            skill = await self.skill_repo.get_skill(skill_id)
            if skill is None:
                continue
            permissions.update(p.permission for p in skill.permissions)
        return sorted(permissions)

    async def create_agent(
        self,
        org_id: UUID,
        owner_id: UUID,
        name: str,
        description: str,
        skill_ids: list[str] | None = None,
        request_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> Agent:
        skill_ids = skill_ids or []
        # Validating a skill and reading its permissions are the same lookup,
        # so do it once per skill rather than twice.
        granted: set[str] = set()
        for skill_id in skill_ids:
            skill = await self.skill_repo.get_skill(skill_id)
            if not skill:
                raise SkillNotFoundError(f"Skill '{skill_id}' does not exist")
            granted.update(p.permission for p in skill.permissions)

        agent = Agent(
            id=uuid4(),
            org_id=org_id,
            owner_id=owner_id,
            assigned_user_id=assigned_user_id,
            request_id=request_id,
            name=name,
            description=description,
            status="DRAFT",
        )
        await self.agent_repo.create_agent(agent)

        for skill_id in skill_ids:
            await self.agent_repo.add_skill(agent.id, skill_id)

        passport = AgentPassport(
            id=uuid4(),
            agent_id=agent.id,
            agent=agent,
            compliance_status="PENDING",
            lifecycle_state="DRAFT",
        )
        await self.agent_repo.create_passport(passport)

        # Derive the passport's permissions from the skills it was built from.
        # Without this every agent created through the console holds an empty
        # permission set and is denied on *every* tool call at runtime, while
        # still passing a subset check vacuously — the bug D-043 exists to fix.
        for permission in sorted(granted):
            await self.perm_repo.create_permission(
                Permission(id=uuid4(), passport_id=passport.id, permission=permission)
            )

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

        # FRD-03: four deterministic rules, evaluated by a pure function. Every
        # piece of database state it needs is resolved here and handed in, so
        # the rules themselves stay readable in one file.
        skill_ids = await self.agent_repo.list_skill_ids(agent_id)
        violations = check_compliance(
            owner_id=agent.owner_id,
            owner_is_known=(
                bool(agent.owner_id)
                and await self.agent_repo.owner_is_in_org(agent.owner_id, agent.org_id)
            ),
            skill_ids=skill_ids,
            granted_permissions=[p.permission for p in agent.passport.permissions],
            allowed_permissions=await self._permissions_for_skills(skill_ids),
            forbidden_pairs=await self.perm_repo.list_forbidden_pairs(),
        )

        agent.passport.compliance_checked_at = datetime.now(timezone.utc)
        if violations:
            agent.passport.compliance_status = "FAILED"
            raise ComplianceError(violations)

        agent.passport.compliance_status = "PASSED"
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

        if agent.request_id:
            # Inline import to avoid circular dependency
            from app.domain.agent_requests.repository import AgentRequestRepository
            from app.domain.agent_requests.service import AgentRequestService
            from app.infrastructure.event_bus import event_bus

            request_repo = AgentRequestRepository(self.agent_repo.session)
            request_service = AgentRequestService(request_repo, event_bus=event_bus)
            await request_service.fulfill_request(agent.request_id, agent.id)

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

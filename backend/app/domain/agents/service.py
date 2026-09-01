from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.repository import AgentRepository
from app.domain.permissions.repository import PermissionRepository

class ComplianceError(Exception):
    pass

class AgentService:
    def __init__(self, agent_repo: AgentRepository, perm_repo: PermissionRepository):
        self.agent_repo = agent_repo
        self.perm_repo = perm_repo

    async def create_agent(self, org_id: UUID, owner_id: UUID, name: str, description: str) -> Agent:
        agent = Agent(
            org_id=org_id,
            owner_id=owner_id,
            name=name,
            description=description,
            status="DRAFT"
        )
        await self.agent_repo.create_agent(agent)
        
        passport = AgentPassport(
            agent=agent,
            compliance_status="PENDING",
            lifecycle_state="DRAFT"
        )
        await self.agent_repo.create_passport(passport)
        return agent

    async def submit_for_review(self, agent_id: UUID) -> AgentPassport:
        agent = await self.agent_repo.get_agent(agent_id)
        if not agent or not agent.passport:
            raise ValueError("Agent or passport not found")
            
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
        if agent.passport.lifecycle_state != "APPROVED":
            raise ValueError("Agent must be APPROVED before activation")
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

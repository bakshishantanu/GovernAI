from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.agents.repository import AgentRepository
from app.domain.audit.service import AuditService
from app.infrastructure.event_bus import EventBus, Event

class KillSwitchService:
    def __init__(self, session: AsyncSession, agent_repo: AgentRepository, audit_service: AuditService, event_bus: EventBus):
        self.session = session
        self.agent_repo = agent_repo
        self.audit_service = audit_service
        self.event_bus = event_bus

    async def suspend_agent(self, agent_id: UUID, actor_id: UUID, org_id: UUID, reason: str):
        agent = await self.agent_repo.get_agent(agent_id)
        if not agent or agent.org_id != org_id:
            raise ValueError("Agent not found")
            
        agent.status = "SUSPENDED"
        if agent.passport:
            agent.passport.lifecycle_state = "SUSPENDED"
            
        await self.audit_service.log_agent_suspended(
            org_id=org_id,
            actor_id=actor_id,
            agent_id=agent_id,
            reason=reason
        )
        
        await self.session.commit()
        # org_id travels with the event so a subscriber can attribute it without
        # a database lookup; the automation engine drops any event it cannot
        # attribute rather than guessing.
        await self.event_bus.publish(Event.create("agent.suspended", {
            "org_id": str(org_id),
            "agent_id": str(agent_id),
            "reason": reason,
        }))

    async def reactivate_agent(self, agent_id: UUID, actor_id: UUID, org_id: UUID, reason: str):
        agent = await self.agent_repo.get_agent(agent_id)
        if not agent or agent.org_id != org_id:
            raise ValueError("Agent not found")
            
        if agent.status != "SUSPENDED":
            raise ValueError("Agent is not suspended")
            
        agent.status = "ACTIVE"
        if agent.passport:
            agent.passport.lifecycle_state = "ACTIVE"
            
        await self.audit_service.log_agent_created( # Using created as a placeholder for reactivation log since we don't have reactivate
            org_id=org_id,
            actor_id=actor_id,
            agent_id=agent_id
        )
        
        await self.session.commit()
        await self.event_bus.publish(Event.create("agent.reactivated", {
            "org_id": str(org_id),
            "agent_id": str(agent_id),
            "reason": reason,
        }))

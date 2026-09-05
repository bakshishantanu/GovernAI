import uuid
from uuid import UUID
from datetime import datetime, timezone
from app.domain.audit.models import AuditEvent
from app.domain.audit.repository import AuditRepository
from app.infrastructure.event_bus import Event, EventBus

class AuditService:
    def __init__(self, audit_repo: AuditRepository, event_bus: EventBus):
        self.audit_repo = audit_repo
        self.event_bus = event_bus

    async def log_agent_created(self, org_id: UUID, actor_id: UUID, agent_id: UUID):
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            agent_id=agent_id,
            action="agent_created",
            policy_decision="ALLOW",
            timestamp=datetime.now(timezone.utc)
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(Event.create("audit.agent.created", {"agent_id": str(agent_id), "org_id": str(org_id)}))

    async def log_agent_suspended(self, org_id: UUID, actor_id: UUID, agent_id: UUID, reason: str):
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            agent_id=agent_id,
            action="agent_suspended",
            policy_decision="ALLOW",
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(Event.create("audit.agent.suspended", {"agent_id": str(agent_id), "reason": reason}))

    async def log_tool_call(self, org_id: UUID, agent_id: UUID, execution_id: UUID, tool: str, allowed: bool, reason: str = ""):
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="agent",
            actor_id=agent_id,
            agent_id=agent_id,
            execution_id=execution_id,
            action="tool_call",
            tool=tool,
            policy_decision="ALLOW" if allowed else "DENY",
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
        await self.audit_repo.record_event(event)
        
        topic = "audit.tool.allowed" if allowed else "audit.tool.denied"
        # org_id and agent_id are carried on the event, not just the row.
        # Without them a subscriber cannot tell whose call this was, which
        # blocked both the org-wide event feed and the automation engine —
        # both are given an execution id and no way to resolve it. Both values
        # are already arguments to this method, so this costs nothing.
        await self.event_bus.publish(Event.create(topic, {
            "org_id": str(org_id),
            "agent_id": str(agent_id),
            "execution_id": str(execution_id),
            "tool": tool,
            "reason": reason
        }))

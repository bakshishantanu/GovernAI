import uuid
from datetime import datetime, timezone
from uuid import UUID

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
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create("audit.agent.created", {"agent_id": str(agent_id), "org_id": str(org_id)})
        )

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
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create("audit.agent.suspended", {"agent_id": str(agent_id), "reason": reason})
        )

    async def log_agent_reactivated(
        self, org_id: UUID, actor_id: UUID, agent_id: UUID, reason: str
    ):
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            agent_id=agent_id,
            action="agent_reactivated",
            policy_decision="ALLOW",
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.agent.reactivated",
                {"agent_id": str(agent_id), "org_id": str(org_id), "reason": reason},
            )
        )

    async def log_compliance_passed(self, org_id: UUID, actor_id: UUID, agent_id: UUID) -> None:
        """FRD-02: an audit event exists after every compliance attempt."""
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="system",
            actor_id=actor_id,
            agent_id=agent_id,
            action="compliance_check.passed",
            policy_decision="ALLOW",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.compliance.passed",
                {"agent_id": str(agent_id), "org_id": str(org_id)},
            )
        )

    async def log_compliance_failed(
        self, org_id: UUID, actor_id: UUID, agent_id: UUID, violations: list
    ) -> None:
        """As above, plus the violations themselves.

        They go in `metadata_json` as well as `reason` because the audit log is
        what someone reads afterwards: a decision without its grounds is not an
        audit trail. Every violation is joined into `reason`, not just the
        first - a reason naming one of three problems misleads whoever reads it.
        """
        payload = [{"rule": v.rule, "message": v.message} for v in violations]
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="system",
            actor_id=actor_id,
            agent_id=agent_id,
            action="compliance_check.failed",
            policy_decision="DENY",
            reason="; ".join(v.message for v in violations),
            metadata_json={"violations": payload},
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.compliance.failed",
                {"agent_id": str(agent_id), "org_id": str(org_id), "violations": payload},
            )
        )

    async def log_tool_call(
        self,
        org_id: UUID,
        agent_id: UUID,
        execution_id: UUID,
        tool: str,
        allowed: bool,
        reason: str = "",
    ):
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
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)

        topic = "audit.tool.allowed" if allowed else "audit.tool.denied"
        await self.event_bus.publish(
            Event.create(topic, {"execution_id": str(execution_id), "tool": tool, "reason": reason})
        )

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

    async def log_policy_created(
        self, org_id: UUID, actor_id: UUID, policy_id: UUID, name: str
    ) -> None:
        """A policy is the actual rule set constraining every agent in the
        org -- creating, changing, disabling, or deleting one is exactly the
        kind of action a governance/audit platform must never leave silent."""
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="policy_created",
            resource=str(policy_id),
            policy_decision="ALLOW",
            reason=f"Policy created: {name}",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.policy.created", {"policy_id": str(policy_id), "org_id": str(org_id)}
            )
        )

    async def log_policy_updated(
        self, org_id: UUID, actor_id: UUID, policy_id: UUID, reason: str
    ) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="policy_updated",
            resource=str(policy_id),
            policy_decision="ALLOW",
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.policy.updated", {"policy_id": str(policy_id), "org_id": str(org_id)}
            )
        )

    async def log_policy_deleted(
        self, org_id: UUID, actor_id: UUID, policy_id: UUID, name: str
    ) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="policy_deleted",
            resource=str(policy_id),
            policy_decision="ALLOW",
            reason=f"Policy deleted: {name}",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.policy.deleted", {"policy_id": str(policy_id), "org_id": str(org_id)}
            )
        )

    async def log_policy_rule_added(
        self, org_id: UUID, actor_id: UUID, policy_id: UUID, rule_id: UUID, rule_type: str
    ) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="policy_rule_added",
            resource=str(rule_id),
            policy_decision="ALLOW",
            reason=f"Rule added to policy {policy_id}: {rule_type}",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.policy.rule_added",
                {"policy_id": str(policy_id), "rule_id": str(rule_id), "org_id": str(org_id)},
            )
        )

    async def log_policy_rule_toggled(
        self, org_id: UUID, actor_id: UUID, policy_id: UUID, rule_id: UUID, enabled: bool
    ) -> None:
        """FRD-14's whole point is that disabling a rule takes effect
        immediately with no redeploy -- that same moment is exactly when an
        audit trail matters most, since a disabled rule is a gap in coverage
        someone deliberately opened."""
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="policy_rule_enabled" if enabled else "policy_rule_disabled",
            resource=str(rule_id),
            policy_decision="ALLOW",
            reason=f"Rule {rule_id} on policy {policy_id} {'enabled' if enabled else 'disabled'}",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.policy.rule_toggled",
                {
                    "policy_id": str(policy_id),
                    "rule_id": str(rule_id),
                    "org_id": str(org_id),
                    "enabled": enabled,
                },
            )
        )

    async def log_connection_saved(
        self, org_id: UUID, actor_id: UUID, requirement_key: str, label: str
    ) -> None:
        """A connection (e.g. Jira credentials) is a shared, org-wide
        credential -- one person saving or overwriting it affects every
        agent in the org that needs it, not just the one they were looking
        at. Without this, GovernAI's own audit log couldn't answer "who
        connected/changed our Jira integration, and when" for its own
        governance feature."""
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="connection_saved",
            resource=requirement_key,
            policy_decision="ALLOW",
            reason=f"Connection saved: {label}",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.connection.saved",
                {"org_id": str(org_id), "requirement_key": requirement_key},
            )
        )

    async def log_connection_deleted(
        self, org_id: UUID, actor_id: UUID, requirement_key: str
    ) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            action="connection_deleted",
            resource=requirement_key,
            policy_decision="ALLOW",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.connection.deleted",
                {"org_id": str(org_id), "requirement_key": requirement_key},
            )
        )

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

    async def log_agent_activated(self, org_id: UUID, actor_id: UUID, agent_id: UUID) -> None:
        """The moment an agent goes from APPROVED to ACTIVE -- the single
        most consequential transition an agent has, since only an ACTIVE
        agent may actually run and spend money. Confirmed live this had no
        audit method at all before this fix."""
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            agent_id=agent_id,
            action="agent_activated",
            policy_decision="ALLOW",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create(
                "audit.agent.activated", {"agent_id": str(agent_id), "org_id": str(org_id)}
            )
        )

    async def log_agent_deleted(self, org_id: UUID, actor_id: UUID, agent_id: UUID) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="user",
            actor_id=actor_id,
            agent_id=agent_id,
            action="agent_deleted",
            policy_decision="ALLOW",
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)
        await self.event_bus.publish(
            Event.create("audit.agent.deleted", {"agent_id": str(agent_id), "org_id": str(org_id)})
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
            Event.create(
                "audit.agent.suspended",
                {"agent_id": str(agent_id), "org_id": str(org_id), "reason": reason},
            )
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
        metadata: dict | None = None,
    ):
        """Record one governed tool call.

        `metadata` is whatever the tool judged worth keeping about this
        particular call (see BaseTool.audit_metadata). For retrieval that is
        the chunks it returned, which is the only place they are persisted:
        without it the console can say a search was allowed but not what it
        found, so nobody can check whether an answer was grounded.
        """
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
            metadata_json=metadata,
            timestamp=datetime.now(timezone.utc),
        )
        await self.audit_repo.record_event(event)

        topic = "audit.tool.allowed" if allowed else "audit.tool.denied"
        await self.event_bus.publish(
            Event.create(
                topic,
                {
                    # The persisted row's id, deliberately overriding the bus
                    # event's own uuid in the rendered frame. The console
                    # merges this live event with the same event re-read from
                    # GET /executions/{id}/timeline, and can only recognise
                    # the two as one thing if they share an id space. The bus
                    # uuid is generated per publish and matches nothing.
                    "id": str(event.id),
                    "execution_id": str(execution_id),
                    "agent_id": str(agent_id),
                    "org_id": str(org_id),
                    "tool": tool,
                    "reason": reason,
                    # Carried on the live event too, so a run being watched
                    # shows its sources as they arrive rather than only after
                    # the timeline is re-fetched.
                    "metadata": metadata,
                },
            )
        )

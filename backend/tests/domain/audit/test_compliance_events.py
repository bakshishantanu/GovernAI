"""FRD-02 requires an audit event after every compliance attempt, pass or fail."""

from unittest.mock import AsyncMock
from uuid import uuid4

# Constructing any mapped class configures every mapper in the declarative
# registry, and AgentPassport.permissions is a string reference to a class in
# another module. Importing only the audit models leaves that name unresolved,
# so the mapper cannot be built. main.py imports every model for exactly this
# reason; a focused test has to do the same.
import app.domain.agents.models  # noqa: F401
import app.domain.permissions.models  # noqa: F401
from app.domain.agents.compliance import Violation
from app.domain.audit.service import AuditService

ORG, ACTOR, AGENT = uuid4(), uuid4(), uuid4()


def _service():
    repo, bus = AsyncMock(), AsyncMock()
    return AuditService(repo, bus), repo, bus


async def test_passed_event_is_recorded_and_published():
    service, repo, bus = _service()

    await service.log_compliance_passed(ORG, ACTOR, AGENT)

    event = repo.record_event.await_args.args[0]
    assert event.action == "compliance_check.passed"
    assert event.policy_decision == "ALLOW"
    assert event.agent_id == AGENT
    bus.publish.assert_awaited_once()


async def test_failed_event_carries_the_violations():
    service, repo, _ = _service()
    violations = [Violation(rule="skills", message="Agent must have at least one skill.")]

    await service.log_compliance_failed(ORG, ACTOR, AGENT, violations)

    event = repo.record_event.await_args.args[0]
    assert event.action == "compliance_check.failed"
    assert event.policy_decision == "DENY"
    # The violations must survive into the immutable record, not only the
    # HTTP response - the audit log is what someone reads afterwards.
    assert event.metadata_json["violations"] == [
        {"rule": "skills", "message": "Agent must have at least one skill."}
    ]
    assert "at least one skill" in event.reason


async def test_failed_event_joins_every_violation_into_the_reason():
    """A reason naming one of three problems is a reason that misleads."""
    service, repo, _ = _service()
    violations = [
        Violation(rule="skills", message="Agent must have at least one skill."),
        Violation(rule="forbidden_pair", message="Forbidden permission combination: a with b."),
    ]

    await service.log_compliance_failed(ORG, ACTOR, AGENT, violations)

    event = repo.record_event.await_args.args[0]
    assert event.reason == (
        "Agent must have at least one skill.; Forbidden permission combination: a with b."
    )
    assert [v["rule"] for v in event.metadata_json["violations"]] == ["skills", "forbidden_pair"]

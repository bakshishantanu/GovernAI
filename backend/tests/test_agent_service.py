from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.agents.models import Agent, AgentPassport
from app.domain.agents.service import (
    AgentService,
    ComplianceError,
    InvalidStateTransitionError,
    SkillNotFoundError,
)
from app.domain.permissions.models import Permission


def _service():
    agent_repo = AsyncMock()
    perm_repo = AsyncMock()
    skill_repo = AsyncMock()
    # Explicit defaults rather than AsyncMock's auto-magic. A MagicMock is
    # truthy and iterates as empty, so an agent with no skills configured would
    # silently satisfy the "at least one skill" rule and the test would pass
    # while proving nothing.
    agent_repo.list_skill_ids.return_value = []
    agent_repo.owner_is_in_org.return_value = True
    perm_repo.list_forbidden_pairs.return_value = []
    service = AgentService(agent_repo, perm_repo, skill_repo)
    return service, agent_repo, skill_repo, perm_repo


def _skill(*permissions: str) -> SimpleNamespace:
    """A stub skill shaped like SkillModel: what create_agent actually reads."""
    return SimpleNamespace(permissions=[SimpleNamespace(permission=p) for p in permissions])


def _agent_with_passport(lifecycle_state: str, owner_id=None, permissions=()) -> Agent:
    agent = Agent(
        id=uuid4(),
        org_id=uuid4(),
        owner_id=owner_id or uuid4(),
        name="Support Bot",
        description="Handles L1 tickets",
        status="DRAFT",
    )
    agent.passport = AgentPassport(
        id=uuid4(),
        agent=agent,
        compliance_status="PENDING",
        lifecycle_state=lifecycle_state,
    )
    agent.passport.permissions = [
        Permission(id=uuid4(), passport_id=agent.passport.id, permission=p) for p in permissions
    ]
    return agent


async def test_create_agent_rejects_unknown_skill():
    """Regression: the mock API never validated skill IDs at all, so a typo'd
    skill would silently be accepted instead of failing the request."""
    service, agent_repo, skill_repo, perm_repo = _service()
    skill_repo.get_skill.return_value = None

    with pytest.raises(SkillNotFoundError):
        await service.create_agent(
            org_id=uuid4(),
            owner_id=uuid4(),
            name="Support Bot",
            description="Handles L1 tickets",
            skill_ids=["not_a_real_skill"],
        )

    agent_repo.create_agent.assert_not_called()


async def test_create_agent_links_validated_skills():
    """create_agent re-fetches (rather than returns the in-memory objects)
    since freshly-flushed relationship collections aren't reliably loaded
    under async SQLAlchemy -- see service.py's comment. So the meaningful
    assertions are on what was actually persisted, not on the mocked
    get_agent()'s return value."""
    service, agent_repo, skill_repo, perm_repo = _service()
    skill_repo.get_skill.return_value = _skill("ticket:read", "ticket:create")

    await service.create_agent(
        org_id=uuid4(),
        owner_id=uuid4(),
        name="Support Bot",
        description="Handles L1 tickets",
        skill_ids=["ticketing"],
    )

    created_agent = agent_repo.create_agent.call_args.args[0]
    assert created_agent.id is not None
    agent_repo.add_skill.assert_awaited_once_with(created_agent.id, "ticketing")
    agent_repo.create_passport.assert_awaited_once()
    agent_repo.flush.assert_awaited_once()
    agent_repo.get_agent.assert_awaited_once_with(created_agent.id)


async def test_submit_for_review_rejects_non_draft():
    """Regression: PR #8's service had no state guard at all -- an already
    APPROVED or ACTIVE agent could be resubmitted and silently re-approved."""
    service, agent_repo, _, perm_repo = _service()
    agent = _agent_with_passport(lifecycle_state="APPROVED")
    agent_repo.get_agent.return_value = agent

    with pytest.raises(InvalidStateTransitionError):
        await service.submit_for_review(agent.id)


async def test_submit_for_review_approves_draft_agent():
    service, agent_repo, skill_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT", permissions=["ticket:read"])
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = ["ticketing"]
    skill_repo.get_skill.return_value = _skill("ticket:read", "ticket:create")

    passport = await service.submit_for_review(agent.id)

    assert passport.lifecycle_state == "APPROVED"
    assert passport.compliance_status == "PASSED"
    assert passport.compliance_checked_at is not None


async def test_submit_for_review_fails_compliance_without_owner():
    service, agent_repo, _, perm_repo = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT")
    agent.owner_id = None
    agent_repo.get_agent.return_value = agent

    with pytest.raises(ComplianceError):
        await service.submit_for_review(agent.id)

    assert agent.passport.compliance_status == "FAILED"


async def test_activate_agent_rejects_non_approved():
    service, agent_repo, _, perm_repo = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT")
    agent_repo.get_agent.return_value = agent

    with pytest.raises(InvalidStateTransitionError):
        await service.activate_agent(agent.id)


async def test_activate_agent_activates_approved_agent():
    service, agent_repo, _, perm_repo = _service()
    agent = _agent_with_passport(lifecycle_state="APPROVED")
    agent_repo.get_agent.return_value = agent

    activated = await service.activate_agent(agent.id)

    assert activated.status == "ACTIVE"
    assert activated.passport.lifecycle_state == "ACTIVE"


async def test_create_agent_with_request_and_assigned_user():
    service, agent_repo, skill_repo, perm_repo = _service()
    skill_repo.get_skill.return_value = _skill("ticket:read")
    req_id = uuid4()
    assigned_user = uuid4()

    created_agent = None

    async def capture_created(agent):
        nonlocal created_agent
        created_agent = agent
        return agent

    agent_repo.create_agent.side_effect = capture_created
    agent_repo.get_agent.side_effect = lambda id_: created_agent

    result = await service.create_agent(
        org_id=uuid4(),
        owner_id=uuid4(),
        name="Requested Agent",
        description="Created from request",
        skill_ids=["ticketing"],
        request_id=req_id,
        assigned_user_id=assigned_user,
    )

    assert result.request_id == req_id
    assert result.assigned_user_id == assigned_user


async def test_activate_agent_fulfills_linked_request():
    from unittest.mock import MagicMock, patch

    service, agent_repo, _, perm_repo = _service()
    agent = _agent_with_passport(lifecycle_state="APPROVED")
    agent.request_id = uuid4()
    agent_repo.get_agent.return_value = agent
    agent_repo.session = MagicMock()

    with patch(
        "app.domain.agent_requests.service.AgentRequestService.fulfill_request",
        new_callable=AsyncMock,
    ) as mock_fulfill:
        activated = await service.activate_agent(agent.id)
        assert activated.status == "ACTIVE"
        mock_fulfill.assert_awaited_once_with(agent.request_id, agent.id)


async def test_create_agent_grants_the_permissions_its_skills_declare():
    """The D-043 bug: create_agent was handed a PermissionRepository and never
    called it, so every agent built through the console held an empty permission
    set and was denied on every tool call at runtime."""
    service, agent_repo, skill_repo, perm_repo = _service()
    by_id = {
        "ticketing": _skill("ticket:read", "ticket:create"),
        "sql_query": _skill("sql:read:tickets", "ticket:read"),
    }
    skill_repo.get_skill.side_effect = lambda skill_id: by_id[skill_id]

    await service.create_agent(
        org_id=uuid4(),
        owner_id=uuid4(),
        name="Support Bot",
        description="Handles L1 tickets",
        skill_ids=["ticketing", "sql_query"],
    )

    granted = [c.args[0].permission for c in perm_repo.create_permission.await_args_list]
    # A union, not a concatenation: ticket:read is declared by both skills and
    # must be granted once.
    assert granted == ["sql:read:tickets", "ticket:create", "ticket:read"]

    passport = agent_repo.create_passport.await_args.args[0]
    assert {c.args[0].passport_id for c in perm_repo.create_permission.await_args_list} == {
        passport.id
    }


async def test_create_agent_without_skills_grants_nothing():
    service, agent_repo, skill_repo, perm_repo = _service()

    await service.create_agent(
        org_id=uuid4(), owner_id=uuid4(), name="Bare", description="No skills"
    )

    perm_repo.create_permission.assert_not_awaited()


async def test_submit_for_review_fails_without_skills():
    """Rule 2. An agent with no skills can do nothing, so approving one is a
    passport that certifies nothing."""
    service, agent_repo, _, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT")
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = []

    with pytest.raises(ComplianceError) as exc:
        await service.submit_for_review(agent.id)

    assert [v.rule for v in exc.value.violations] == ["skills"]
    assert agent.passport.compliance_status == "FAILED"
    assert agent.passport.lifecycle_state == "DRAFT"


async def test_submit_for_review_fails_on_permission_not_from_a_skill():
    """Rule 3, and the reason it was vacuous before: with permissions never
    derived, every passport was empty and trivially a subset."""
    service, agent_repo, skill_repo, _ = _service()
    agent = _agent_with_passport(
        lifecycle_state="DRAFT", permissions=["ticket:read", "sql:read:internal_payroll"]
    )
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = ["ticketing"]
    skill_repo.get_skill.return_value = _skill("ticket:read", "ticket:create")

    with pytest.raises(ComplianceError) as exc:
        await service.submit_for_review(agent.id)

    assert [v.rule for v in exc.value.violations] == ["permission_subset"]
    assert "sql:read:internal_payroll" in exc.value.violations[0].message


async def test_submit_for_review_fails_on_a_forbidden_pair():
    """Rule 4 — the pair comes from the table, not from code."""
    service, agent_repo, skill_repo, perm_repo = _service()
    agent = _agent_with_passport(
        lifecycle_state="DRAFT",
        permissions=["sql:read:internal_payroll", "docs:search:public"],
    )
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = ["sql_query", "document_search"]
    skill_repo.get_skill.side_effect = lambda skill_id: _skill(
        "sql:read:internal_payroll", "docs:search:public"
    )
    perm_repo.list_forbidden_pairs.return_value = [
        ("sql:read:internal_payroll", "docs:search:public", "payroll must stay off public surfaces")
    ]

    with pytest.raises(ComplianceError) as exc:
        await service.submit_for_review(agent.id)

    assert [v.rule for v in exc.value.violations] == ["forbidden_pair"]
    assert "payroll must stay off public surfaces" in exc.value.violations[0].message


async def test_submit_for_review_reports_every_violation_at_once():
    """A builder fixing one problem per attempt is a builder wasting an
    afternoon, so the service must not stop at the first failure."""
    service, agent_repo, _, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT", permissions=["ticket:read"])
    agent.owner_id = None
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = []

    with pytest.raises(ComplianceError) as exc:
        await service.submit_for_review(agent.id)

    assert [v.rule for v in exc.value.violations] == ["owner", "skills", "permission_subset"]
    assert "must have an owner" in str(exc.value)


async def test_submit_for_review_fails_when_the_owner_is_not_in_the_org():
    """Rule 1, in the only form that can actually fail through the API.

    owner_id is NOT NULL and comes from the caller's own token, so "is it set"
    can never be false. "Is the owner a person this organisation knows" can be:
    a profile can be deleted, and an id copied from elsewhere points outside
    the org.
    """
    service, agent_repo, skill_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT", permissions=["ticket:read"])
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = ["ticketing"]
    skill_repo.get_skill.return_value = _skill("ticket:read")
    agent_repo.owner_is_in_org.return_value = False

    with pytest.raises(ComplianceError) as exc:
        await service.submit_for_review(agent.id)

    assert [v.rule for v in exc.value.violations] == ["owner"]
    assert "not a member of this organisation" in exc.value.violations[0].message
    agent_repo.owner_is_in_org.assert_awaited_once_with(agent.owner_id, agent.org_id)


async def test_a_missing_owner_is_not_looked_up_at_all():
    """No owner id means there is nothing to look up; the check must not go to
    the database with None and must still report the simpler problem."""
    service, agent_repo, skill_repo, _ = _service()
    agent = _agent_with_passport(lifecycle_state="DRAFT", permissions=["ticket:read"])
    agent.owner_id = None
    agent_repo.get_agent.return_value = agent
    agent_repo.list_skill_ids.return_value = ["ticketing"]
    skill_repo.get_skill.return_value = _skill("ticket:read")

    with pytest.raises(ComplianceError) as exc:
        await service.submit_for_review(agent.id)

    assert [v.rule for v in exc.value.violations] == ["owner"]
    assert exc.value.violations[0].message == "Agent must have an owner."
    agent_repo.owner_is_in_org.assert_not_awaited()

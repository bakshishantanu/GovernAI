"""The four FRD-03 compliance rules, each failing on its own.

These are pure-function tests on purpose: the rules take plain data and do no
I/O, so a rule can be proved wrong here without a database, a session, or a
mock. Anything needing the database belongs in the service tests instead.
"""

from uuid import uuid4

from app.domain.agents.compliance import Violation, check_compliance

OWNER = uuid4()
PAIRS = [("sql:read:internal_payroll", "docs:search:public", "payroll + public surface")]


def _check(**overrides):
    kwargs = dict(
        owner_id=OWNER,
        skill_ids=["ticketing"],
        granted_permissions=["ticket:read"],
        allowed_permissions=["ticket:read", "ticket:create"],
        forbidden_pairs=PAIRS,
    )
    kwargs.update(overrides)
    return check_compliance(**kwargs)


def test_a_valid_agent_has_no_violations():
    assert _check() == []


def test_rule_1_missing_owner():
    violations = _check(owner_id=None)
    assert [v.rule for v in violations] == ["owner"]
    assert "owner" in violations[0].message.lower()


def test_rule_2_no_skills():
    violations = _check(skill_ids=[], granted_permissions=[], allowed_permissions=[])
    assert [v.rule for v in violations] == ["skills"]


def test_rule_3_permission_not_derivable_from_any_bound_skill():
    violations = _check(granted_permissions=["ticket:read", "sql:read:tickets"])
    assert [v.rule for v in violations] == ["permission_subset"]
    # The offending permission must be named — a violation the builder cannot
    # act on is barely better than no violation at all.
    assert "sql:read:tickets" in violations[0].message


def test_rule_4_forbidden_pair_held_together():
    violations = _check(
        granted_permissions=["sql:read:internal_payroll", "docs:search:public"],
        allowed_permissions=["sql:read:internal_payroll", "docs:search:public"],
    )
    assert [v.rule for v in violations] == ["forbidden_pair"]
    assert "payroll + public surface" in violations[0].message


def test_rule_4_silent_when_only_one_member_is_present():
    violations = _check(
        granted_permissions=["sql:read:internal_payroll"],
        allowed_permissions=["sql:read:internal_payroll"],
    )
    assert violations == []


def test_rule_4_order_within_the_pair_does_not_matter():
    violations = _check(
        granted_permissions=["docs:search:public", "sql:read:internal_payroll"],
        allowed_permissions=["docs:search:public", "sql:read:internal_payroll"],
    )
    assert [v.rule for v in violations] == ["forbidden_pair"]


def test_all_rules_report_together_rather_than_stopping_at_the_first():
    violations = _check(
        owner_id=None, skill_ids=[], granted_permissions=["nope"], allowed_permissions=[]
    )
    assert {v.rule for v in violations} == {"owner", "skills", "permission_subset"}


def test_violation_is_comparable():
    assert Violation(rule="owner", message="x") == Violation(rule="owner", message="x")

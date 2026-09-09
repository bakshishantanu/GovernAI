"""DENY_LIST and RATE_LIMIT — the two rule types FRD-14 needs and the engine
only ever had a comment for.

FRD-14's acceptance criterion is behavioural: toggling a DENY_LIST rule off and
on changes the outcome of an identical tool call without a restart. That is only
true if the decision is read from the database on every evaluation, so these
tests assert on the decision, never on a cached rule set.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.policies.engine import PolicyEngine


def _active_agent():
    agent = MagicMock()
    agent.passport.lifecycle_state = "ACTIVE"
    agent.org_id = uuid.uuid4()
    return agent


def _rule(rule_type: str, config: dict, enabled: bool = True):
    rule = MagicMock()
    rule.rule_type = rule_type
    rule.config = config
    rule.enabled = enabled
    return rule


def _policy(name: str, rules: list):
    policy = MagicMock()
    policy.name = name
    policy.rules = rules
    return policy


def _engine(rules: list, audit_repo=None):
    agent_repo, perm_repo, policy_repo = AsyncMock(), AsyncMock(), AsyncMock()
    agent_repo.get_agent.return_value = _active_agent()
    perm_repo.get_permissions_for_passport.return_value = []
    policy_repo.get_active_policies_for_org.return_value = [_policy("House rules", rules)]
    return PolicyEngine(agent_repo, perm_repo, policy_repo, audit_repo=audit_repo)


async def _evaluate(engine, tool_name="delete_ticket", tool_args=None):
    return await engine.evaluate(
        agent_id=uuid.uuid4(),
        tool_name=tool_name,
        tool_args=tool_args or {},
        required_permission="",
    )


# --- DENY_LIST -------------------------------------------------------------


@pytest.mark.asyncio
async def test_deny_list_blocks_a_blocked_tool():
    engine = _engine([_rule("DENY_LIST", {"blocked_tools": ["delete_ticket"]})])

    decision = await _evaluate(engine)

    assert decision.allowed is False
    assert "delete_ticket" in decision.reason
    assert "House rules" in decision.reason


@pytest.mark.asyncio
async def test_deny_list_allows_a_tool_it_does_not_name():
    engine = _engine([_rule("DENY_LIST", {"blocked_tools": ["delete_ticket"]})])

    decision = await _evaluate(engine, tool_name="read_ticket")

    assert decision.allowed is True


@pytest.mark.asyncio
async def test_a_disabled_deny_list_rule_stops_denying():
    """FRD-14's acceptance criterion: the same call, the rule toggled off."""
    engine = _engine([_rule("DENY_LIST", {"blocked_tools": ["delete_ticket"]}, enabled=False)])

    assert (await _evaluate(engine)).allowed is True


@pytest.mark.asyncio
async def test_deny_list_can_block_on_an_argument_as_well_as_a_tool():
    """FRD-03's table says tool *and argument* combinations. A rule that can
    only name a tool cannot express "not on the payroll table"."""
    engine = _engine(
        [_rule("DENY_LIST", {"blocked_tools": ["run_sql_query"], "blocked_args": ["payroll"]})]
    )

    blocked = await _evaluate(engine, "run_sql_query", {"query": "SELECT * FROM payroll"})
    allowed = await _evaluate(engine, "run_sql_query", {"query": "SELECT * FROM tickets"})

    assert blocked.allowed is False
    assert allowed.allowed is True


# --- RATE_LIMIT ------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_blocks_once_the_cap_is_reached():
    audit_repo = AsyncMock()
    audit_repo.count_tool_calls_since.return_value = 30
    engine = _engine([_rule("RATE_LIMIT", {"max_calls_per_minute": 30})], audit_repo=audit_repo)

    decision = await _evaluate(engine, tool_name="read_ticket")

    assert decision.allowed is False
    assert "30" in decision.reason


@pytest.mark.asyncio
async def test_rate_limit_allows_below_the_cap():
    audit_repo = AsyncMock()
    audit_repo.count_tool_calls_since.return_value = 29
    engine = _engine([_rule("RATE_LIMIT", {"max_calls_per_minute": 30})], audit_repo=audit_repo)

    assert (await _evaluate(engine, tool_name="read_ticket")).allowed is True


@pytest.mark.asyncio
async def test_rate_limit_counts_the_last_minute_only():
    audit_repo = AsyncMock()
    audit_repo.count_tool_calls_since.return_value = 0
    engine = _engine([_rule("RATE_LIMIT", {"max_calls_per_minute": 5})], audit_repo=audit_repo)

    await _evaluate(engine, tool_name="read_ticket")

    since = audit_repo.count_tool_calls_since.await_args.kwargs["since"]
    delta = datetime.now(timezone.utc) - since
    assert timedelta(seconds=55) < delta < timedelta(seconds=65)


@pytest.mark.asyncio
async def test_rate_limit_without_an_audit_repo_fails_closed():
    """A rule the engine cannot evaluate must deny, not silently pass. This is
    the whole fail-closed stance: an unevaluable limit is not an absent one."""
    engine = _engine([_rule("RATE_LIMIT", {"max_calls_per_minute": 30})], audit_repo=None)

    decision = await _evaluate(engine, tool_name="read_ticket")

    assert decision.allowed is False
    assert "cannot be evaluated" in decision.reason


@pytest.mark.asyncio
async def test_the_old_sql_blocklist_rule_still_works():
    """The seeded demo policy uses it; adding rule types must not break it."""
    engine = _engine([_rule("sql_blocklist", {"keywords": ["DROP"]})])

    decision = await _evaluate(engine, "sql_query", {"query": "DROP TABLE tickets"})

    assert decision.allowed is False
    assert "DROP" in decision.reason

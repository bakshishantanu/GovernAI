from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.governance.budget import (
    DEFAULT_BUDGET_USD_24H,
    BudgetGuard,
    resolve_cap,
)

AGENT = uuid4()
ORG = uuid4()


class FakeSpendReader:
    def __init__(self, total: float | None = None, raises: Exception | None = None):
        self._total = total
        self._raises = raises
        self.called_since: datetime | None = None

    async def get_total_cost_for_agent(self, agent_id, since):
        if self._raises:
            raise self._raises
        self.called_since = since
        return self._total


def cap_of(value: float):
    return lambda _agent_id: value


@pytest.mark.asyncio
async def test_under_cap_is_allowed():
    guard = BudgetGuard(FakeSpendReader(2.0), cap_resolver=cap_of(5.0))

    decision = await guard.check(AGENT, ORG)

    assert decision.allowed
    assert decision.remaining_usd == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_at_the_cap_is_denied():
    """Exactly at the cap must not be allowed to spend again."""
    guard = BudgetGuard(FakeSpendReader(5.0), cap_resolver=cap_of(5.0))

    decision = await guard.check(AGENT, ORG)

    assert not decision.allowed
    assert "Budget exceeded" in decision.reason
    assert decision.remaining_usd == 0.0


@pytest.mark.asyncio
async def test_breach_suspends_the_agent_once():
    """FRD-11: exceeding the cap denies the call *and* suspends the agent."""
    suspended = []

    async def on_breach(agent_id, org_id, reason):
        suspended.append((agent_id, org_id, reason))

    guard = BudgetGuard(
        FakeSpendReader(9.99), on_breach=on_breach, cap_resolver=cap_of(5.0)
    )

    decision = await guard.check(AGENT, ORG)

    assert not decision.allowed
    assert len(suspended) == 1
    assert suspended[0][0] == AGENT


@pytest.mark.asyncio
async def test_a_failed_suspension_still_denies_the_call():
    async def broken_on_breach(*_args):
        raise RuntimeError("database unavailable")

    guard = BudgetGuard(
        FakeSpendReader(9.99), on_breach=broken_on_breach, cap_resolver=cap_of(5.0)
    )

    decision = await guard.check(AGENT, ORG)

    assert not decision.allowed  # the denial stands regardless


@pytest.mark.asyncio
async def test_unreadable_spend_fails_closed():
    """If we cannot prove the agent is under budget, it does not spend."""
    guard = BudgetGuard(
        FakeSpendReader(raises=RuntimeError("connection lost")),
        cap_resolver=cap_of(5.0),
    )

    decision = await guard.check(AGENT, ORG)

    assert not decision.allowed
    assert "could not be verified" in decision.reason


@pytest.mark.asyncio
async def test_spend_is_measured_over_a_window_not_all_time():
    reader = FakeSpendReader(1.0)
    guard = BudgetGuard(reader, cap_resolver=cap_of(5.0))

    await guard.check(AGENT, ORG)

    assert reader.called_since is not None  # a lower bound was applied


def test_cap_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("AGENT_BUDGET_USD_24H", "12.5")
    assert resolve_cap(AGENT) == 12.5


@pytest.mark.parametrize("bad", ["", "not-a-number", "0", "-4"])
def test_a_missing_or_nonsense_cap_falls_back_to_the_default(monkeypatch, bad):
    """A zero or negative cap would silently disable every agent."""
    monkeypatch.setenv("AGENT_BUDGET_USD_24H", bad)
    assert resolve_cap(AGENT) == DEFAULT_BUDGET_USD_24H

"""The automation engine can suspend an agent, so its decisions are tested.

These cover the logic, not the database: the two measurement queries are
stubbed so each test states exactly what was observed and asserts what the
rule concluded. What matters here is that a rule fires when it should, stays
quiet when it should, records evidence either way, and cannot start a loop.
"""

from uuid import uuid4

import pytest

from app.domain.automations.models import Automation
from app.domain.automations.service import (
    ACTION_RAISE_ALERT,
    ACTION_SUSPEND_AGENT,
    TRIGGER_AGENT_SUSPENDED,
    TRIGGER_SPEND_THRESHOLD,
    TRIGGER_TOOL_DENIED,
    AutomationService,
)

ORG = uuid4()
AGENT = uuid4()


class FakeRepo:
    def __init__(self, automations, already_fired: int = 0):
        self._automations = automations
        self._already_fired = already_fired
        self.recorded = []
        self.session = None

    async def list_enabled(self, org_id=None):
        return self._automations

    def record_run(self, run):
        self.recorded.append(run)
        return run

    async def count_runs_since(self, automation_id, agent_id, since):
        return self._already_fired


class FakeKillSwitch:
    def __init__(self, raises: Exception | None = None):
        self.calls = []
        self._raises = raises

    async def suspend_agent(self, agent_id, actor_id, org_id, reason):
        if self._raises:
            raise self._raises
        self.calls.append({"agent_id": agent_id, "reason": reason})


def make_automation(**overrides) -> Automation:
    defaults = dict(
        id=uuid4(),
        org_id=ORG,
        name="Stop repeat offenders",
        description="",
        enabled=True,
        agent_id=None,
        trigger_type=TRIGGER_TOOL_DENIED,
        trigger_config={"count": 3, "window_minutes": 60},
        action_type=ACTION_SUSPEND_AGENT,
        action_config={},
    )
    defaults.update(overrides)
    return Automation(**defaults)


def service_with(automations, *, denials=0, spend=0.0, already_fired=0, kill_switch=None):
    """An AutomationService whose two measurements are fixed by the test."""
    repo = FakeRepo(automations, already_fired=already_fired)
    svc = AutomationService(repo=repo, kill_switch=kill_switch or FakeKillSwitch())

    async def fake_denials(agent_id, org_id, window_minutes):
        return denials

    async def fake_spend(agent_id, org_id):
        return spend

    svc._count_recent_denials = fake_denials
    svc._spend_in_budget_window = fake_spend
    return svc, repo


def denial_event():
    return "audit.tool.denied", {
        "org_id": str(ORG),
        "agent_id": str(AGENT),
        "tool": "delete_database",
        "reason": "Missing required permission",
    }


# ------------------------------------------------------------------ attribution


@pytest.mark.asyncio
async def test_an_event_without_ids_is_ignored_not_guessed():
    """Before the ids were added to the payload, an engine could only guess."""
    svc, repo = service_with([make_automation()], denials=99)

    runs = await svc.evaluate_event("audit.tool.denied", {"tool": "x"})

    assert runs == []
    assert repo.recorded == []


# ---------------------------------------------------------------- TOOL_DENIED


@pytest.mark.asyncio
async def test_fires_once_the_denial_count_is_reached():
    kill = FakeKillSwitch()
    svc, repo = service_with([make_automation()], denials=3, kill_switch=kill)

    runs = await svc.evaluate_event(*denial_event())

    assert len(runs) == 1
    assert runs[0].outcome == "FIRED"
    assert len(kill.calls) == 1
    assert kill.calls[0]["agent_id"] == AGENT
    # The measurements behind the decision are kept, so it can be audited.
    assert runs[0].context["observed_denials"] == 3
    assert runs[0].context["threshold"] == 3


@pytest.mark.asyncio
async def test_stays_quiet_below_the_threshold_but_still_records_why():
    kill = FakeKillSwitch()
    svc, repo = service_with([make_automation()], denials=2, kill_switch=kill)

    runs = await svc.evaluate_event(*denial_event())

    assert runs[0].outcome == "SKIPPED"
    assert kill.calls == []
    assert "threshold is 3" in runs[0].detail


@pytest.mark.asyncio
async def test_cooldown_stops_a_denial_storm_suspending_repeatedly():
    kill = FakeKillSwitch()
    svc, repo = service_with(
        [make_automation()], denials=50, already_fired=1, kill_switch=kill
    )

    runs = await svc.evaluate_event(*denial_event())

    assert runs[0].outcome == "SKIPPED"
    assert "Already fired" in runs[0].detail
    assert kill.calls == []


@pytest.mark.asyncio
async def test_a_rule_scoped_to_another_agent_is_not_evaluated():
    svc, repo = service_with([make_automation(agent_id=uuid4())], denials=99)

    runs = await svc.evaluate_event(*denial_event())

    assert runs == []


@pytest.mark.asyncio
async def test_a_rule_listening_for_a_different_event_is_not_evaluated():
    svc, repo = service_with([make_automation()], denials=99)

    runs = await svc.evaluate_event(
        "cost.llm.incurred", {"org_id": str(ORG), "agent_id": str(AGENT)}
    )

    assert runs == []


# ------------------------------------------------------------ SPEND_THRESHOLD


@pytest.mark.asyncio
async def test_spend_threshold_measures_against_the_enforced_cap():
    automation = make_automation(
        trigger_type=TRIGGER_SPEND_THRESHOLD,
        trigger_config={"percent_of_cap": 80},
        action_type=ACTION_RAISE_ALERT,
    )
    # The default cap is $5.00, so $4.50 is 90%.
    svc, repo = service_with([automation], spend=4.50)

    runs = await svc.evaluate_event(
        "cost.llm.incurred", {"org_id": str(ORG), "agent_id": str(AGENT)}
    )

    assert runs[0].outcome == "FIRED"
    assert runs[0].context["observed_percent"] == pytest.approx(90.0)
    assert "Alert raised" in runs[0].detail


@pytest.mark.asyncio
async def test_spend_below_the_threshold_does_not_fire():
    automation = make_automation(
        trigger_type=TRIGGER_SPEND_THRESHOLD,
        trigger_config={"percent_of_cap": 80},
        action_type=ACTION_RAISE_ALERT,
    )
    svc, repo = service_with([automation], spend=1.00)  # 20% of $5.00

    runs = await svc.evaluate_event(
        "cost.llm.incurred", {"org_id": str(ORG), "agent_id": str(AGENT)}
    )

    assert runs[0].outcome == "SKIPPED"


# ---------------------------------------------------------- loop protection


@pytest.mark.asyncio
async def test_an_automation_does_not_react_to_its_own_suspension():
    """SUSPEND_AGENT publishes agent.suspended, which is itself a trigger.

    Without this guard, an AGENT_SUSPENDED rule whose action is SUSPEND_AGENT
    would re-trigger on the event it just caused.
    """
    automation = make_automation(
        trigger_type=TRIGGER_AGENT_SUSPENDED,
        trigger_config={},
        action_type=ACTION_SUSPEND_AGENT,
    )
    kill = FakeKillSwitch()
    svc, repo = service_with([automation], kill_switch=kill)

    runs = await svc.evaluate_event(
        "agent.suspended",
        {
            "org_id": str(ORG),
            "agent_id": str(AGENT),
            "reason": "Automation: Stop repeat offenders",
        },
    )

    assert runs[0].outcome == "SKIPPED"
    assert kill.calls == []


@pytest.mark.asyncio
async def test_a_human_suspension_does_trigger_an_agent_suspended_rule():
    automation = make_automation(
        trigger_type=TRIGGER_AGENT_SUSPENDED,
        trigger_config={},
        action_type=ACTION_RAISE_ALERT,
    )
    svc, repo = service_with([automation])

    runs = await svc.evaluate_event(
        "agent.suspended",
        {"org_id": str(ORG), "agent_id": str(AGENT), "reason": "Kill switch by an admin"},
    )

    assert runs[0].outcome == "FIRED"


@pytest.mark.asyncio
async def test_the_suspend_reason_is_marked_as_coming_from_an_automation():
    """The prefix is what the loop guard reads; it must always be applied."""
    kill = FakeKillSwitch()
    svc, repo = service_with(
        [make_automation(action_config={"reason": "too many denials"})],
        denials=3,
        kill_switch=kill,
    )

    await svc.evaluate_event(*denial_event())

    assert kill.calls[0]["reason"].startswith("Automation:")


# --------------------------------------------------------------- containment


@pytest.mark.asyncio
async def test_one_broken_rule_does_not_stop_the_others():
    broken = make_automation(name="broken", action_type="NOT_A_REAL_ACTION")
    working = make_automation(name="working", action_type=ACTION_RAISE_ALERT)
    svc, repo = service_with([broken, working], denials=5)

    runs = await svc.evaluate_event(*denial_event())

    outcomes = {run.detail[:20]: run.outcome for run in runs}
    assert len(runs) == 2
    assert any(run.outcome == "FAILED" for run in runs)
    assert any(run.outcome == "FIRED" for run in runs)


@pytest.mark.asyncio
async def test_a_failing_kill_switch_is_recorded_not_raised():
    svc, repo = service_with(
        [make_automation()], denials=3, kill_switch=FakeKillSwitch(raises=ValueError("gone"))
    )

    runs = await svc.evaluate_event(*denial_event())

    assert runs[0].outcome == "FAILED"
    assert "gone" in runs[0].detail

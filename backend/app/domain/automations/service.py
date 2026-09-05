from __future__ import annotations

"""The automation engine: evaluate rules against real events, and act.

Three principles, in order of importance:

1. **Never invent.** Every trigger is measured from rows the platform actually
   wrote (`audit_events`, `cost_events`) and every action calls a service that
   genuinely enforces something. There is no "send an email" action, because
   there is no mail infrastructure to send one.

2. **Never break a run.** Automations are evaluated off the event bus, not in
   the request or the agent loop, so a broken rule cannot fail a tool call or
   a user's request. `evaluate_event` catches everything and records it.

3. **Always leave evidence.** A rule that can suspend an agent must record
   what it observed and what it decided — including when it decided *not* to
   act. Otherwise the platform cannot answer "why was this agent suspended?",
   which is the product's core question.

Deliberately *not* built: chained automations (an automation triggering
another). The suspend action publishes `agent.suspended`, which is itself a
trigger, so chaining is one line away and one line away from an infinite loop.
`AGENT_SUSPENDED` rules therefore ignore suspensions caused by automations —
see `_is_automation_origin`.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.domain.audit.models import AuditEvent
from app.domain.automations.models import Automation, AutomationRun
from app.domain.automations.repository import AutomationRepository
from app.domain.costs.models import CostEvent
from app.domain.governance.budget import BUDGET_WINDOW, resolve_cap

logger = logging.getLogger(__name__)

#: Trigger vocabulary. Each maps to events the platform already publishes.
TRIGGER_TOOL_DENIED = "TOOL_DENIED"
TRIGGER_SPEND_THRESHOLD = "SPEND_THRESHOLD"
TRIGGER_AGENT_SUSPENDED = "AGENT_SUSPENDED"

TRIGGER_TYPES = (TRIGGER_TOOL_DENIED, TRIGGER_SPEND_THRESHOLD, TRIGGER_AGENT_SUSPENDED)

#: Action vocabulary.
ACTION_SUSPEND_AGENT = "SUSPEND_AGENT"
ACTION_RAISE_ALERT = "RAISE_ALERT"

ACTION_TYPES = (ACTION_SUSPEND_AGENT, ACTION_RAISE_ALERT)

#: Which bus events can wake which trigger.
_EVENTS_FOR_TRIGGER = {
    TRIGGER_TOOL_DENIED: {"audit.tool.denied"},
    TRIGGER_SPEND_THRESHOLD: {"cost.llm.incurred"},
    TRIGGER_AGENT_SUSPENDED: {"agent.suspended"},
}

#: How long a rule stays quiet for one agent after firing. Without this a
#: denial storm writes one suspension row per denied call.
DEFAULT_COOLDOWN_MINUTES = 10

#: The actor recorded for anything an automation does. It is not a real user,
#: and the audit trail must not pretend it was.
AUTOMATION_ACTOR_ID = UUID("00000000-0000-0000-0000-0000000000a1")


@dataclass(frozen=True)
class Decision:
    """What a rule concluded about one event."""

    fired: bool
    detail: str
    context: dict[str, Any]


def _is_automation_origin(reason: str | None) -> bool:
    """Whether a suspension was itself caused by an automation.

    Used to stop `AGENT_SUSPENDED` rules reacting to their own side effects.
    """
    return bool(reason) and reason.startswith("Automation:")


class AutomationService:
    """Evaluates automations and carries out their actions."""

    def __init__(self, repo: AutomationRepository, kill_switch=None) -> None:
        self.repo = repo
        self.session = repo.session
        self.kill_switch = kill_switch

    # ---------------------------------------------------------------- triggers

    async def _count_recent_denials(
        self, agent_id: UUID, org_id: UUID, window_minutes: int
    ) -> int:
        """Denied tool calls for one agent inside the window.

        Counted from `audit_events`, the same rows the audit log shows, so the
        number a rule acted on is the number a human can go and verify.
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        result = await self.session.execute(
            select(func.count(AuditEvent.id))
            .where(AuditEvent.org_id == org_id)
            .where(AuditEvent.agent_id == agent_id)
            .where(AuditEvent.timestamp >= since)
            .where(AuditEvent.policy_decision.in_(("DENY", "DENIED")))
        )
        return int(result.scalar_one() or 0)

    async def _spend_in_budget_window(self, agent_id: UUID, org_id: UUID) -> float:
        since = datetime.now(timezone.utc) - BUDGET_WINDOW
        result = await self.session.execute(
            select(func.coalesce(func.sum(CostEvent.cost_usd), 0.0))
            .where(CostEvent.org_id == org_id)
            .where(CostEvent.agent_id == agent_id)
            .where(CostEvent.timestamp >= since)
        )
        return float(result.scalar_one() or 0.0)

    async def _decide(
        self, automation: Automation, event_type: str, payload: dict, agent_id: UUID
    ) -> Decision:
        config = automation.trigger_config or {}

        if automation.trigger_type == TRIGGER_TOOL_DENIED:
            threshold = int(config.get("count", 1))
            window = int(config.get("window_minutes", 60))
            observed = await self._count_recent_denials(agent_id, automation.org_id, window)
            fired = observed >= threshold
            return Decision(
                fired=fired,
                detail=(
                    f"{observed} denied tool call(s) in the last {window} minute(s); "
                    f"threshold is {threshold}."
                ),
                context={"observed_denials": observed, "threshold": threshold, "window_minutes": window},
            )

        if automation.trigger_type == TRIGGER_SPEND_THRESHOLD:
            percent = float(config.get("percent_of_cap", 80))
            cap = resolve_cap(agent_id)
            spend = await self._spend_in_budget_window(agent_id, automation.org_id)
            observed_percent = (spend / cap * 100) if cap > 0 else 0.0
            fired = observed_percent >= percent
            return Decision(
                fired=fired,
                detail=(
                    f"Spend ${spend:.6f} is {observed_percent:.1f}% of the ${cap:.2f} cap; "
                    f"threshold is {percent:.0f}%."
                ),
                context={
                    "spend_usd": round(spend, 6),
                    "cap_usd": cap,
                    "observed_percent": round(observed_percent, 2),
                    "threshold_percent": percent,
                },
            )

        if automation.trigger_type == TRIGGER_AGENT_SUSPENDED:
            reason = payload.get("reason")
            if _is_automation_origin(reason):
                return Decision(
                    fired=False,
                    detail="Suspension was caused by an automation; not reacting to it.",
                    context={"reason": reason},
                )
            return Decision(
                fired=True,
                detail=f"Agent was suspended: {reason or 'no reason recorded'}.",
                context={"reason": reason},
            )

        return Decision(
            fired=False,
            detail=f"Unknown trigger type {automation.trigger_type!r}; nothing evaluated.",
            context={},
        )

    # ----------------------------------------------------------------- actions

    async def _act(self, automation: Automation, agent_id: UUID, decision: Decision) -> str:
        """Carry out the action. Returns a plain-English account of what happened."""
        if automation.action_type == ACTION_RAISE_ALERT:
            # The alert *is* the AutomationRun row the caller writes. Nothing
            # else happens, and the wording says so rather than implying a
            # notification went somewhere.
            return f"Alert raised. {decision.detail}"

        if automation.action_type == ACTION_SUSPEND_AGENT:
            if self.kill_switch is None:
                raise RuntimeError("No kill switch available to suspend the agent")
            reason = (
                automation.action_config.get("reason")
                or f"Automation: {automation.name}"
            )
            # The prefix matters: `_is_automation_origin` reads it to stop an
            # AGENT_SUSPENDED rule reacting to this very suspension.
            if not reason.startswith("Automation:"):
                reason = f"Automation: {reason}"
            await self.kill_switch.suspend_agent(
                agent_id=agent_id,
                actor_id=AUTOMATION_ACTOR_ID,
                org_id=automation.org_id,
                reason=reason,
            )
            return f"Agent suspended. {decision.detail}"

        raise RuntimeError(f"Unknown action type {automation.action_type!r}")

    # -------------------------------------------------------------- evaluation

    async def evaluate_event(self, event_type: str, payload: dict) -> list[AutomationRun]:
        """Evaluate every enabled automation against one bus event.

        Never raises. A rule that blows up is recorded as FAILED and the rest
        still run — one bad rule must not silence the whole engine.
        """
        org_id_raw = payload.get("org_id")
        agent_id_raw = payload.get("agent_id")
        if not org_id_raw or not agent_id_raw:
            # Events without both ids cannot be attributed to an agent, and a
            # rule that guessed would be worse than one that stayed quiet.
            return []

        try:
            org_id = UUID(str(org_id_raw))
            agent_id = UUID(str(agent_id_raw))
        except (TypeError, ValueError):
            return []

        automations = await self.repo.list_enabled(org_id)
        runs: list[AutomationRun] = []

        for automation in automations:
            if event_type not in _EVENTS_FOR_TRIGGER.get(automation.trigger_type, set()):
                continue
            if automation.agent_id is not None and automation.agent_id != agent_id:
                continue

            try:
                decision = await self._decide(automation, event_type, payload, agent_id)

                if not decision.fired:
                    runs.append(
                        self._record(automation, agent_id, "SKIPPED", decision.detail, decision.context)
                    )
                    continue

                cooldown = int(
                    (automation.trigger_config or {}).get(
                        "cooldown_minutes", DEFAULT_COOLDOWN_MINUTES
                    )
                )
                since = datetime.now(timezone.utc) - timedelta(minutes=cooldown)
                if await self.repo.count_runs_since(automation.id, agent_id, since) > 0:
                    runs.append(
                        self._record(
                            automation,
                            agent_id,
                            "SKIPPED",
                            f"Already fired for this agent within the last {cooldown} minute(s).",
                            decision.context,
                        )
                    )
                    continue

                outcome_detail = await self._act(automation, agent_id, decision)
                runs.append(
                    self._record(automation, agent_id, "FIRED", outcome_detail, decision.context)
                )

            except Exception as exc:  # one bad rule must not stop the others
                logger.exception(
                    "automation.failed", extra={"automation_id": str(automation.id)}
                )
                runs.append(
                    self._record(
                        automation, agent_id, "FAILED", f"{type(exc).__name__}: {exc}", {}
                    )
                )

        return runs

    def _record(
        self,
        automation: Automation,
        agent_id: UUID,
        outcome: str,
        detail: str,
        context: dict,
    ) -> AutomationRun:
        run = AutomationRun(
            id=uuid4(),
            automation_id=automation.id,
            org_id=automation.org_id,
            agent_id=agent_id,
            triggered_at=datetime.now(timezone.utc),
            outcome=outcome,
            detail=detail,
            context=context or {},
        )
        return self.repo.record_run(run)

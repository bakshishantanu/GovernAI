from __future__ import annotations

"""The long-running task that feeds bus events to the automation engine.

Started once at application startup and cancelled at shutdown. It is the only
subscriber that lives for the process's whole life — every other subscriber is
an SSE connection that comes and goes.

Two things this deliberately does not do:

- **It does not share a session.** Each event is handled on a session this
  module opens and closes, the same reasoning as `api/execution_runner.py`:
  a request's session is long gone by the time an event is processed.
- **It does not let an exception escape.** This task has nobody awaiting it,
  so an escaping error would be swallowed by the event loop and the engine
  would silently stop evaluating rules — a governance feature that quietly
  stops working is worse than one that was never built.
"""

import asyncio
import logging

from app.domain.agents.kill_switch import KillSwitchService
from app.domain.agents.repository import AgentRepository
from app.domain.audit.repository import AuditRepository
from app.domain.audit.service import AuditService
from app.domain.automations.repository import AutomationRepository
from app.domain.automations.service import AutomationService
from app.infrastructure.database import async_session_factory
from app.infrastructure.event_bus import event_bus

logger = logging.getLogger(__name__)

#: Only these wake the engine. Everything else is ignored without a session
#: being opened at all — most bus traffic is not automation-relevant.
LISTENS_FOR = frozenset(
    {"audit.tool.denied", "cost.llm.incurred", "agent.suspended"}
)


async def _handle(event_type: str, payload: dict) -> None:
    """Evaluate one event on its own session, and commit whatever it recorded."""
    async with async_session_factory() as session:
        repo = AutomationRepository(session)
        kill_switch = KillSwitchService(
            session=session,
            agent_repo=AgentRepository(session),
            audit_service=AuditService(
                audit_repo=AuditRepository(session), event_bus=event_bus
            ),
            event_bus=event_bus,
        )
        service = AutomationService(repo=repo, kill_switch=kill_switch)

        runs = await service.evaluate_event(event_type, payload)
        if runs:
            await session.commit()


async def run_automation_engine() -> None:
    """Subscribe to the bus and evaluate automations until cancelled."""
    subscription = event_bus.subscribe()
    logger.info("automations.engine.started")

    try:
        while True:
            event = await subscription.__anext__()
            if event.type not in LISTENS_FOR:
                continue
            try:
                await _handle(event.type, event.payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                # One bad event must not kill the engine for every later one.
                logger.exception(
                    "automations.engine.event_failed", extra={"event_type": event.type}
                )
    except asyncio.CancelledError:
        logger.info("automations.engine.stopped")
        raise
    finally:
        # `Subscription` has no __aenter__, so it cannot be used with
        # `async with`; calling its cleanup directly is the supported path.
        await subscription.__aexit__()

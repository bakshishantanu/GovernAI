"""The background runner's job is to always reach a terminal state.

Nobody is awaiting it, so an exception that escapes is swallowed by the event
loop and the execution sits at RUNNING forever — which also means the SSE
stream never closes, because the stream ends when the run reaches a terminal
status.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.api import execution_runner


@pytest.fixture
def ids():
    return {
        "execution_id": uuid.uuid4(),
        "agent_id": uuid.uuid4(),
        "org_id": uuid.uuid4(),
    }


@pytest.mark.asyncio
async def test_a_database_that_is_down_still_ends_the_run(ids):
    """Even opening the session is inside the guard. If it were not, the run
    would stay at RUNNING and its stream would never close."""
    with (
        patch.object(
            execution_runner, "async_session_factory", side_effect=RuntimeError("no database")
        ),
        patch.object(execution_runner, "_mark_failed", new_callable=AsyncMock) as mark_failed,
    ):
        await execution_runner.run_execution(
            **ids,
            goal="anything",
            system_prompt=None,
            max_steps=5,
            llm_service=AsyncMock(),
        )

    mark_failed.assert_awaited_once()
    assert "no database" in mark_failed.await_args.args[1]


@pytest.mark.asyncio
async def test_a_failure_inside_the_run_is_recorded_not_raised(ids):
    """A tool blowing up, the LLM failing, a bad skill — none of it should
    escape, and all of it must end as a FAILED execution."""
    session = AsyncMock()
    session.__aenter__.return_value = session

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "_mark_failed", new_callable=AsyncMock) as mark_failed,
    ):
        load_tools.side_effect = RuntimeError("skill registry exploded")

        await execution_runner.run_execution(
            **ids,
            goal="anything",
            system_prompt=None,
            max_steps=5,
            llm_service=AsyncMock(),
        )

    mark_failed.assert_awaited_once()
    assert mark_failed.await_args.args[0] == ids["execution_id"]
    assert "skill registry exploded" in mark_failed.await_args.args[1]


@pytest.mark.asyncio
async def test_a_run_that_fails_mid_flight_commits_the_same_session_not_mark_failed(ids):
    """Found live: a run that did real governed work (tool calls, LLM calls,
    audit/cost events all added to `session` but not yet committed) and then
    had run_agent() itself raise (e.g. every LLM provider erroring out) used
    to fall through to the bare `except Exception` below, which calls
    `_mark_failed` on a brand new session that knows nothing about any of
    that work -- so it was silently discarded. Session.add() without a
    commit is invisible to any later query, even though the real tool calls
    and LLM spend genuinely happened. The fix commits the SAME session
    (preserving everything already added to it) right where the failure is
    caught, instead of abandoning it for `_mark_failed`'s fresh one."""
    session = AsyncMock()
    session.__aenter__.return_value = session
    exec_service = AsyncMock()

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "ExecutionService", return_value=exec_service),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "run_agent", new_callable=AsyncMock) as run,
        patch.object(execution_runner, "SkillRegistry"),
        patch.object(execution_runner, "PolicyEngine"),
        patch.object(execution_runner, "BudgetGuard"),
        patch.object(execution_runner, "KillSwitchService"),
        patch.object(execution_runner, "_mark_failed", new_callable=AsyncMock) as mark_failed,
    ):
        load_tools.return_value = []
        run.side_effect = RuntimeError(
            "All LLM providers failed: groq attempt 1/2: Client error '429 Too Many Requests'"
        )

        await execution_runner.run_execution(
            **ids,
            goal="do a lot of governed work then hit a rate limit",
            system_prompt=None,
            max_steps=10,
            llm_service=AsyncMock(),
        )

    exec_service.fail.assert_awaited_once()
    assert exec_service.fail.await_args.args[0] == ids["execution_id"]
    assert "429 Too Many Requests" in exec_service.fail.await_args.kwargs["error"]
    session.commit.assert_awaited()
    mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_failed_never_raises_even_if_the_database_is_gone(ids):
    """The last line of defence. If this raised, the exception would surface
    inside the except block that called it and be lost anyway."""
    with patch.object(
        execution_runner, "async_session_factory", side_effect=RuntimeError("still down")
    ):
        await execution_runner._mark_failed(ids["execution_id"], "original error")
    # Reaching here without raising is the assertion.


@pytest.mark.asyncio
async def test_hitting_the_step_limit_is_a_failure_not_a_success(ids):
    """An agent that ran out of steps has not answered the question."""
    session = AsyncMock()
    session.__aenter__.return_value = session
    exec_service = AsyncMock()

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "ExecutionService", return_value=exec_service),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "run_agent", new_callable=AsyncMock) as run,
        patch.object(execution_runner, "SkillRegistry"),
        patch.object(execution_runner, "PolicyEngine"),
        patch.object(execution_runner, "BudgetGuard"),
        patch.object(execution_runner, "KillSwitchService"),
    ):
        load_tools.return_value = []
        run.return_value = {"final_answer": None, "stopped_reason": "max_steps_reached"}

        await execution_runner.run_execution(
            **ids,
            goal="loop forever",
            system_prompt=None,
            max_steps=2,
            llm_service=AsyncMock(),
        )

    exec_service.fail.assert_awaited_once()
    exec_service.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_completed_run_is_marked_complete_with_its_answer(ids):
    session = AsyncMock()
    session.__aenter__.return_value = session
    exec_service = AsyncMock()

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "ExecutionService", return_value=exec_service),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "run_agent", new_callable=AsyncMock) as run,
        patch.object(execution_runner, "SkillRegistry"),
        patch.object(execution_runner, "PolicyEngine"),
        patch.object(execution_runner, "BudgetGuard"),
        patch.object(execution_runner, "KillSwitchService"),
    ):
        load_tools.return_value = []
        run.return_value = {"final_answer": "42", "stopped_reason": "completed"}

        await execution_runner.run_execution(
            **ids,
            goal="the answer",
            system_prompt=None,
            max_steps=5,
            llm_service=AsyncMock(),
        )

    exec_service.mark_running.assert_awaited_once_with(ids["execution_id"])
    exec_service.complete.assert_awaited_once_with(ids["execution_id"], result="42")


@pytest.mark.asyncio
async def test_the_run_is_budget_guarded(ids):
    """An unattended run is exactly where a spend cap matters most, so the
    guard must be passed through rather than left to the request path."""
    session = AsyncMock()
    session.__aenter__.return_value = session

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "ExecutionService", return_value=AsyncMock()),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "run_agent", new_callable=AsyncMock) as run,
        patch.object(execution_runner, "SkillRegistry"),
        patch.object(execution_runner, "PolicyEngine"),
        patch.object(execution_runner, "KillSwitchService"),
    ):
        load_tools.return_value = []
        run.return_value = {"final_answer": "ok", "stopped_reason": "completed"}

        await execution_runner.run_execution(
            **ids,
            goal="spend money",
            system_prompt=None,
            max_steps=5,
            llm_service=AsyncMock(),
        )

    assert run.await_args.kwargs["budget_guard"] is not None


@pytest.mark.asyncio
async def test_budget_exceeded_is_terminated_not_completed(ids):
    """Before this fix, a run stopped by the budget guard fell into the same
    branch as a real success (final_answer is None either way, but only
    max_steps_reached was special-cased) and was recorded as a normal
    COMPLETED execution with a generic message -- a denied, cost-driven stop
    that looked identical to success in the console. It must be recorded as
    TERMINATED, with the real denial reason as the error."""
    session = AsyncMock()
    session.__aenter__.return_value = session
    exec_service = AsyncMock()

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "ExecutionService", return_value=exec_service),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "run_agent", new_callable=AsyncMock) as run,
        patch.object(execution_runner, "SkillRegistry"),
        patch.object(execution_runner, "PolicyEngine"),
        patch.object(execution_runner, "BudgetGuard"),
        patch.object(execution_runner, "KillSwitchService"),
    ):
        load_tools.return_value = []
        run.return_value = {
            "final_answer": None,
            "stopped_reason": "budget_exceeded",
            "messages": [
                {"role": "assistant", "content": "Budget exceeded: $10.00 of $5.00 spent"}
            ],
        }

        await execution_runner.run_execution(
            **ids,
            goal="spend too much",
            system_prompt=None,
            max_steps=5,
            llm_service=AsyncMock(),
        )

    exec_service.complete.assert_not_awaited()
    exec_service.fail.assert_not_awaited()
    exec_service.terminate.assert_awaited_once_with(
        ids["execution_id"], reason="Budget exceeded: $10.00 of $5.00 spent"
    )


@pytest.mark.asyncio
async def test_unpriced_model_is_terminated_not_completed(ids):
    session = AsyncMock()
    session.__aenter__.return_value = session
    exec_service = AsyncMock()

    with (
        patch.object(execution_runner, "async_session_factory", return_value=session),
        patch.object(execution_runner, "ExecutionService", return_value=exec_service),
        patch.object(execution_runner, "load_agent_tools", new_callable=AsyncMock) as load_tools,
        patch.object(execution_runner, "run_agent", new_callable=AsyncMock) as run,
        patch.object(execution_runner, "SkillRegistry"),
        patch.object(execution_runner, "PolicyEngine"),
        patch.object(execution_runner, "BudgetGuard"),
        patch.object(execution_runner, "KillSwitchService"),
    ):
        load_tools.return_value = []
        run.return_value = {
            "final_answer": None,
            "stopped_reason": "unpriced_model",
            "messages": [{"role": "assistant", "content": "Model 'm' has no pricing entry"}],
        }

        await execution_runner.run_execution(
            **ids,
            goal="use an unpriced model",
            system_prompt=None,
            max_steps=5,
            llm_service=AsyncMock(),
        )

    exec_service.complete.assert_not_awaited()
    exec_service.terminate.assert_awaited_once_with(
        ids["execution_id"], reason="Model 'm' has no pricing entry"
    )

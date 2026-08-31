import pytest

from app.runtime.llm.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


class _FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_closed_and_allows_calls():
    breaker = CircuitBreaker()
    breaker.before_call("groq")  # should not raise
    assert not breaker.is_open("groq")


def test_trips_open_after_threshold_failures():
    breaker = CircuitBreaker(failure_threshold=3)

    breaker.record_failure("groq")
    breaker.record_failure("groq")
    assert not breaker.is_open("groq")

    breaker.record_failure("groq")
    assert breaker.is_open("groq")

    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_call("groq")


def test_different_providers_tracked_independently():
    breaker = CircuitBreaker(failure_threshold=1)

    breaker.record_failure("groq")

    assert breaker.is_open("groq")
    assert not breaker.is_open("gemini")
    breaker.before_call("gemini")  # should not raise


def test_transitions_to_half_open_after_cooldown():
    clock = _FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30.0, clock=clock)

    breaker.record_failure("groq")
    assert breaker.is_open("groq")

    clock.advance(31.0)
    breaker.before_call("groq")  # cooldown elapsed -> moves to HALF_OPEN, does not raise
    assert breaker.state_of("groq") == CircuitState.HALF_OPEN


def test_success_resets_to_closed():
    breaker = CircuitBreaker(failure_threshold=1)

    breaker.record_failure("groq")
    assert breaker.is_open("groq")

    breaker.record_success("groq")
    assert not breaker.is_open("groq")
    breaker.before_call("groq")  # should not raise


def test_failure_during_half_open_reopens_immediately():
    clock = _FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30.0, clock=clock)

    breaker.record_failure("groq")
    clock.advance(31.0)
    breaker.before_call("groq")  # now HALF_OPEN

    breaker.record_failure("groq")
    assert breaker.is_open("groq")

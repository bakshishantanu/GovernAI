import time
from dataclasses import dataclass


class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""


@dataclass
class _BreakerState:
    consecutive_failures: int = 0
    state: str = CircuitState.CLOSED
    opened_at: float | None = None


class CircuitBreaker:
    """Tracks consecutive failures per named target (e.g. an LLM provider's
    name) and trips open after too many in a row, so a dead provider isn't
    retried on every call. In-memory only, per FRD/SRS's MVP scope (no Redis).
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        clock=time.monotonic,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._states: dict[str, _BreakerState] = {}

    def _state_for(self, key: str) -> _BreakerState:
        return self._states.setdefault(key, _BreakerState())

    def before_call(self, key: str) -> None:
        """Raises CircuitBreakerOpenError if calls to `key` are currently blocked."""
        state = self._state_for(key)
        if state.state != CircuitState.OPEN:
            return

        elapsed = self._clock() - state.opened_at
        if elapsed >= self._cooldown_seconds:
            state.state = CircuitState.HALF_OPEN
            return

        raise CircuitBreakerOpenError(
            f"circuit open for '{key}', retry after {self._cooldown_seconds - elapsed:.1f}s"
        )

    def record_success(self, key: str) -> None:
        state = self._state_for(key)
        state.consecutive_failures = 0
        state.state = CircuitState.CLOSED
        state.opened_at = None

    def record_failure(self, key: str) -> None:
        state = self._state_for(key)
        state.consecutive_failures += 1
        if state.state == CircuitState.HALF_OPEN or state.consecutive_failures >= self._failure_threshold:
            state.state = CircuitState.OPEN
            state.opened_at = self._clock()

    def is_open(self, key: str) -> bool:
        return self._state_for(key).state == CircuitState.OPEN

    def state_of(self, key: str) -> str:
        return self._state_for(key).state

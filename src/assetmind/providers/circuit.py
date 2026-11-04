"""Per-provider circuit breaker. Three consecutive failures open the circuit."""

from datetime import UTC, datetime, timedelta

from assetmind.providers.errors import CircuitOpen


class CircuitBreaker:
    def __init__(self, *, name: str, failure_threshold: int = 3, reset_after: float = 30) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_after = timedelta(seconds=reset_after)
        self.failures = 0
        self.opened_at: datetime | None = None

    def before_call(self, now: datetime | None = None) -> None:
        clock = now or datetime.now(UTC)
        if self.opened_at is None:
            return
        if clock - self.opened_at >= self.reset_after:
            self.opened_at = None
            self.failures = 0
            return
        raise CircuitOpen(f"{self.name} circuit is open.", provider=self.name)

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self, now: datetime | None = None) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = now or datetime.now(UTC)

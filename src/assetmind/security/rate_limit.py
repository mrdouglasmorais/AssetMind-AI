"""In-process rate limit. One Render web service does not need Redis for this MVP."""

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, now: float | None = None) -> bool:
        clock = time.monotonic() if now is None else now
        recent = [hit for hit in self._hits[key] if clock - hit < self.window_seconds]
        if len(recent) >= self.limit:
            self._hits[key] = recent
            return False
        recent.append(clock)
        self._hits[key] = recent
        return True

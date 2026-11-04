"""Process-local cache. Current prices are returned only inside the freshness window."""

from datetime import datetime, timedelta
from typing import TypeVar

T = TypeVar("T")


class MarketCache[T]:
    def __init__(self) -> None:
        self._items: dict[str, tuple[datetime, T]] = {}

    def put(self, key: str, value: T, *, retrieved_at: datetime) -> None:
        self._items[key] = (retrieved_at, value)

    def get(self, key: str, *, now: datetime, max_age: timedelta) -> T | None:
        item = self._items.get(key)
        if item is None:
            return None
        retrieved_at, value = item
        if now - retrieved_at > max_age:
            return None
        return value

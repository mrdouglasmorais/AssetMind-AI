"""Shared provider types."""

from datetime import datetime
from typing import Protocol

from assetmind.domain.analysis.engine import MarketSnapshot
from assetmind.domain.assets.identity import ResolvedAsset


class MarketProvider(Protocol):
    name: str

    async def fetch(self, asset: ResolvedAsset, *, as_of: datetime | None, now: datetime) -> MarketSnapshot:
        """Return a normalized snapshot. Missing values stay null."""
        ...

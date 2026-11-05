"""Provider registry. Callers cannot pass an arbitrary URL."""

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from assetmind.application.budget import BudgetManager
from assetmind.domain.analysis.engine import MarketSnapshot
from assetmind.domain.assets.identity import AssetClass, ResolvedAsset
from assetmind.domain.errors import BudgetExceededError, DeadlineExceeded
from assetmind.providers.cache import MarketCache
from assetmind.providers.cvm import CvmProvider
from assetmind.providers.errors import ProviderError

T = TypeVar("T")


class ProviderRegistry:
    def __init__(
        self,
        *,
        brapi: object,
        coingecko: object,
        bcb: object,
        cvm: CvmProvider,
        budget: BudgetManager,
        cache: MarketCache[MarketSnapshot] | None = None,
    ) -> None:
        self.brapi = brapi
        self.coingecko = coingecko
        self.bcb = bcb
        self.cvm = cvm
        self.budget = budget
        self.cache = cache or MarketCache()
        self.deadline: datetime | None = None
        self.semaphores = {
            "brapi": asyncio.Semaphore(1),
            "coingecko": asyncio.Semaphore(2),
            "bcb": asyncio.Semaphore(1),
        }
        self._selic_loaded = False

    async def fetch_asset(
        self,
        asset: ResolvedAsset,
        *,
        as_of: datetime | None,
        now: datetime,
    ) -> MarketSnapshot:
        cache_key = f"{asset.asset_class}:{asset.symbol}:{as_of.isoformat() if as_of else 'latest'}"
        cached = self.cache.get(cache_key, now=now, max_age=_cache_window(asset.asset_class))
        if cached is not None and _cache_is_usable(cached, now):
            return cached

        self._reserve(3 if asset.asset_class is AssetClass.EQUITY else 2)
        if asset.asset_class is AssetClass.CRYPTO:
            async with self.semaphores["coingecko"]:
                snapshot = await self._bounded(self.coingecko.fetch(asset, as_of=as_of, now=now))  # type: ignore[attr-defined]
        else:
            async with self.semaphores["brapi"]:
                snapshot = await self._bounded(self.brapi.fetch(asset, as_of=as_of, now=now))  # type: ignore[attr-defined]

        if asset.asset_class is AssetClass.REAL_ESTATE:
            facts = await self.cvm.fund_facts(asset, now=now)
            snapshot = snapshot.model_copy(
                update={
                    "fund": facts,
                    "evidence": snapshot.evidence + facts.evidence,
                }
            )
            if not self._selic_loaded:
                self._reserve(1)
                try:
                    async with self.semaphores["bcb"]:
                        selic = await self._bounded(self.bcb.latest_selic(now=now))  # type: ignore[attr-defined]
                    snapshot = snapshot.model_copy(update={"macro": [selic]})
                    self._selic_loaded = True
                except (ProviderError, BudgetExceededError):
                    self._selic_loaded = True

        self.cache.put(cache_key, snapshot, retrieved_at=now)
        return snapshot

    async def _bounded(self, call: Coroutine[Any, Any, T]) -> T:
        """Cancel a provider call that is still running when the deadline passes."""

        if self.deadline is None:
            return await call
        remaining = (self.deadline - datetime.now(UTC)).total_seconds()
        if remaining <= 0:
            closer = getattr(call, "close", None)
            if closer is not None:
                closer()
            raise DeadlineExceeded("Deadline exceeded.")
        try:
            return await asyncio.wait_for(call, timeout=remaining)
        except TimeoutError as exc:
            raise DeadlineExceeded("Deadline exceeded.") from exc

    def _reserve(self, calls: int) -> None:
        for _ in range(calls):
            self.budget.consume_provider_call()


def _cache_window(asset_class: AssetClass) -> timedelta:
    if asset_class is AssetClass.CRYPTO:
        return timedelta(minutes=15)
    return timedelta(days=1)


def _cache_is_usable(snapshot: MarketSnapshot, now: datetime) -> bool:
    prices = snapshot.evidence
    current = [item for item in prices if item.metric == "price_close" and item.value is not None]
    if not current:
        return False
    observed = current[-1].observed_at
    if observed is None:
        return False
    window = timedelta(minutes=15) if snapshot.asset.asset_class is AssetClass.CRYPTO else timedelta(days=3)
    return now - observed <= window

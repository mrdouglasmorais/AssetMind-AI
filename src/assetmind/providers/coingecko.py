"""CoinGecko public market data adapter.

The public API is rate limited. A demo key can be sent as ``x-cg-demo-api-key``.
Responses are market data, not permission to redistribute CoinGecko content.
"""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from assetmind.domain.analysis.engine import MarketSnapshot
from assetmind.domain.assets.identity import ResolvedAsset
from assetmind.domain.evidence.models import Evidence, PricePoint, QualityStatus
from assetmind.providers.circuit import CircuitBreaker
from assetmind.providers.errors import ProviderError
from assetmind.providers.http import get_json


class CoinGeckoProvider:
    name = "coingecko"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str = "https://api.coingecko.com/api/v3",
        api_key: str | None = None,
        timeout: float = 8,
        max_retries: int = 2,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.breaker = breaker or CircuitBreaker(name=self.name)
        self.allowed_hosts = {urlparse(self.base_url).hostname or ""}

    async def fetch(self, asset: ResolvedAsset, *, as_of: datetime | None, now: datetime) -> MarketSnapshot:
        del as_of
        self.breaker.before_call(now)
        headers = {"x-cg-demo-api-key": self.api_key} if self.api_key else None
        chart_url = f"{self.base_url}/coins/{asset.symbol}/market_chart"
        markets_url = f"{self.base_url}/coins/markets"
        try:
            chart = await get_json(
                self.client,
                chart_url,
                provider=self.name,
                allowed_hosts=self.allowed_hosts,
                params={"vs_currency": "usd", "days": "90", "interval": "daily"},
                headers=headers,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
            markets = await get_json(
                self.client,
                markets_url,
                provider=self.name,
                allowed_hosts=self.allowed_hosts,
                params={"vs_currency": "usd", "ids": asset.symbol},
                headers=headers,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        except ProviderError:
            self.breaker.record_failure(now)
            raise
        self.breaker.record_success()
        prices = normalize_chart(chart)
        evidence = normalize_markets(markets, asset.symbol, now, markets_url)
        if prices and not any(item.metric == "price_close" and item.value is not None for item in evidence):
            last = prices[-1]
            evidence.append(
                Evidence(
                    provider=self.name,
                    source_url=chart_url,
                    asset_id=asset.symbol,
                    observed_at=last.observed_at,
                    retrieved_at=now,
                    metric="price_close",
                    value=last.close,
                    unit="USD",
                    currency="USD",
                    period="daily_close",
                    quality_status=QualityStatus.OK,
                )
            )
        return MarketSnapshot(asset=asset, prices=prices, evidence=evidence)


def normalize_chart(payload: dict[str, Any]) -> list[PricePoint]:
    points: list[PricePoint] = []
    for item in payload.get("prices") or []:
        if not isinstance(item, list) or len(item) < 2:
            continue
        observed_at = _millis(item[0])
        try:
            close = float(item[1])
        except (TypeError, ValueError):
            continue
        if observed_at is None or close <= 0:
            continue
        points.append(PricePoint(observed_at=observed_at, close=close, currency="USD"))
    return points


def normalize_markets(
    payload: list[Any] | dict[str, Any],
    symbol: str,
    retrieved_at: datetime,
    source_url: str,
) -> list[Evidence]:
    row: dict[str, Any] | None = None
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("id") == symbol:
                row = item
                break
        if row is None and payload and isinstance(payload[0], dict):
            row = payload[0]
    if row is None:
        return [
            Evidence(
                provider="coingecko",
                source_url=source_url,
                asset_id=symbol,
                observed_at=None,
                retrieved_at=retrieved_at,
                metric="price_close",
                value=None,
                quality_status=QualityStatus.MISSING,
            )
        ]
    observed_at = _millis(row.get("last_updated")) if not isinstance(row.get("last_updated"), str) else None
    if isinstance(row.get("last_updated"), str):
        observed_at = _iso(row["last_updated"])
    return [
        _observation(
            symbol,
            "price_close",
            row.get("current_price"),
            "USD",
            "USD",
            observed_at,
            retrieved_at,
            source_url,
            "spot",
        ),
        _observation(
            symbol,
            "market_cap",
            row.get("market_cap"),
            "USD",
            "USD",
            observed_at,
            retrieved_at,
            source_url,
            "spot",
        ),
        _observation(
            symbol,
            "volume",
            row.get("total_volume"),
            "USD",
            "USD",
            observed_at,
            retrieved_at,
            source_url,
            "24h",
        ),
    ]


def _observation(
    symbol: str,
    metric: str,
    value: object,
    unit: str,
    currency: str,
    observed_at: datetime | None,
    retrieved_at: datetime,
    source_url: str,
    period: str,
) -> Evidence:
    number = _float(value)
    return Evidence(
        provider="coingecko",
        source_url=source_url,
        asset_id=symbol,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        metric=metric,
        value=number,
        unit=unit,
        currency=currency,
        period=period,
        quality_status=QualityStatus.OK if number is not None else QualityStatus.MISSING,
    )


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _millis(value: object) -> datetime | None:
    if isinstance(value, str):
        return _iso(value)
    try:
        millis = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if millis < 10_000_000_000:
        millis *= 1000
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def _iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed

"""brapi.dev adapter for B3 quotes and daily history.

Free-tier notes, verified against brapi documentation during implementation:
PETR4, VALE3, MGLU3, and ITUB4 can be queried without a token. The free plan
is limited (about 15,000 requests/month, one ticker per request, one concurrent
request, history up to about three months, and delayed quotes). Free access is
not a license to redistribute the data commercially.
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


class BrapiProvider:
    name = "brapi"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str = "https://brapi.dev",
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
        params = {"symbols": asset.symbol}
        if self.api_key:
            params["token"] = self.api_key
        try:
            quote_url = f"{self.base_url}/api/v2/stocks/quote"
            history_url = f"{self.base_url}/api/v2/stocks/historical"
            quote = await get_json(
                self.client,
                quote_url,
                provider=self.name,
                allowed_hosts=self.allowed_hosts,
                params=params,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
            history = await get_json(
                self.client,
                history_url,
                provider=self.name,
                allowed_hosts=self.allowed_hosts,
                params={**params, "range": "3mo", "interval": "1d", "sortOrder": "asc"},
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        except ProviderError:
            self.breaker.record_failure(now)
            raise
        self.breaker.record_success()
        evidence, currency = normalize_quote(quote, asset.symbol, now, quote_url)
        prices = normalize_history(history, asset.symbol, currency or "BRL")
        return MarketSnapshot(asset=asset, prices=prices, evidence=evidence)


def normalize_quote(
    payload: dict[str, Any],
    symbol: str,
    retrieved_at: datetime,
    source_url: str,
) -> tuple[list[Evidence], str | None]:
    row = _result_for(payload, symbol)
    data = _data(row)
    currency = _optional_str(data.get("currency"))
    observed_at = _parse_time(data.get("regularMarketTime"))
    evidence = [
        _metric(
            symbol=symbol,
            metric="price_close",
            value=_optional_float(data.get("regularMarketPrice")),
            unit=currency,
            currency=currency,
            observed_at=observed_at,
            retrieved_at=retrieved_at,
            source_url=source_url,
            period="spot",
        ),
        _metric(
            symbol=symbol,
            metric="volume",
            value=_optional_float(data.get("regularMarketVolume")),
            unit="shares",
            currency=None,
            observed_at=observed_at,
            retrieved_at=retrieved_at,
            source_url=source_url,
            period="session",
        ),
        _metric(
            symbol=symbol,
            metric="market_cap",
            value=_optional_float(data.get("marketCap")),
            unit=currency,
            currency=currency,
            observed_at=observed_at,
            retrieved_at=retrieved_at,
            source_url=source_url,
            period="spot",
        ),
    ]
    return evidence, currency


def normalize_history(payload: dict[str, Any], symbol: str, currency: str) -> list[PricePoint]:
    row = _result_for(payload, symbol)
    data = _data(row)
    points: list[PricePoint] = []
    for item in data.get("historicalDataPrice") or []:
        if not isinstance(item, dict):
            continue
        close = _optional_float(item.get("adjustedClose"))
        if close is None:
            close = _optional_float(item.get("close"))
        observed_at = _parse_unix(item.get("date"))
        if close is None or observed_at is None or close <= 0:
            continue
        points.append(PricePoint(observed_at=observed_at, close=close, currency=currency))
    return points


def _result_for(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ProviderError(f"brapi has no result for {symbol}.", provider="brapi")
    for item in results:
        if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol.upper():
            return item
    first = results[0]
    if isinstance(first, dict):
        return first
    raise ProviderError(f"brapi returned an unexpected payload for {symbol}.", provider="brapi")


def _data(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("data")
    if isinstance(nested, dict):
        return nested
    return row


def _metric(
    *,
    symbol: str,
    metric: str,
    value: float | None,
    unit: str | None,
    currency: str | None,
    observed_at: datetime | None,
    retrieved_at: datetime,
    source_url: str,
    period: str,
) -> Evidence:
    return Evidence(
        provider="brapi",
        source_url=source_url,
        asset_id=symbol,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        metric=metric,
        value=value,
        unit=unit,
        currency=currency,
        period=period,
        quality_status=QualityStatus.OK if value is not None else QualityStatus.MISSING,
    )


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _parse_unix(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        seconds = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if seconds > 10_000_000_000:
        seconds = seconds / 1000
    return datetime.fromtimestamp(seconds, tz=UTC)

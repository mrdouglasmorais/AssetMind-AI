"""Banco Central do Brasil SGS adapter.

Series 432 is the Selic target. The public SGS API does not require a key.
The value is macro context for receivables funds, not a fund-level fact.
"""

from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from assetmind.domain.evidence.models import Evidence, QualityStatus
from assetmind.providers.circuit import CircuitBreaker
from assetmind.providers.errors import ProviderError
from assetmind.providers.http import get_json


class BancoCentralProvider:
    name = "bcb"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str = "https://api.bcb.gov.br",
        timeout: float = 8,
        max_retries: int = 2,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.breaker = breaker or CircuitBreaker(name=self.name)
        self.allowed_hosts = {urlparse(self.base_url).hostname or ""}

    async def latest_selic(self, *, now: datetime) -> Evidence:
        self.breaker.before_call(now)
        url = f"{self.base_url}/dados/serie/bcdata.sgs.432/dados/ultimos/1"
        try:
            payload = await get_json(
                self.client,
                url,
                provider=self.name,
                allowed_hosts=self.allowed_hosts,
                params={"formato": "json"},
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        except ProviderError:
            self.breaker.record_failure(now)
            raise
        self.breaker.record_success()
        return normalize_selic(payload, now, url)


def normalize_selic(payload: object, retrieved_at: datetime, source_url: str) -> Evidence:
    row = payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else None
    value = None
    observed_at = None
    if row is not None:
        raw = row.get("valor")
        try:
            value = float(str(raw).replace(",", ".")) if raw not in (None, "") else None
        except ValueError:
            value = None
        observed_at = _br_date(row.get("data"))
    return Evidence(
        provider="bcb",
        source_url=source_url,
        asset_id="BR:SELIC",
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        metric="selic_target",
        value=value,
        unit="percent",
        currency=None,
        period="daily",
        quality_status=QualityStatus.OK if value is not None else QualityStatus.MISSING,
    )


def _br_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)

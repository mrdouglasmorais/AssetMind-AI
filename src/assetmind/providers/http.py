"""HTTP helper with bounded retries for idempotent GET requests."""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

import httpx

from assetmind.providers.errors import (
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
    UnsafeUrlError,
)

Sleeper = Callable[[float], Awaitable[None]]


def assert_allowed_url(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme not in {"https", "http"} or host not in allowed_hosts:
        raise UnsafeUrlError(f"Refusing to fetch {url}.", provider="http")


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    provider: str,
    allowed_hosts: set[str],
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 8,
    max_retries: int = 2,
    sleeper: Sleeper = asyncio.sleep,
) -> Any:
    """GET JSON. Only this idempotent method is retried, and only for timeout, 429, and 5xx."""

    assert_allowed_url(url, allowed_hosts)
    attempt = 0
    while True:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=timeout)
        except httpx.TimeoutException as exc:
            if attempt >= max_retries:
                raise ProviderTimeout(f"{provider} timed out.", provider=provider) from exc
            await sleeper(_delay(attempt, None))
            attempt += 1
            continue
        except httpx.HTTPError as exc:
            if attempt >= max_retries:
                raise ProviderUnavailable(f"{provider} request failed.", provider=provider) from exc
            await sleeper(_delay(attempt, None))
            attempt += 1
            continue

        if response.status_code == 429:
            if attempt >= max_retries:
                raise ProviderRateLimited(f"{provider} returned 429.", provider=provider)
            await sleeper(_delay(attempt, response.headers.get("Retry-After")))
            attempt += 1
            continue
        if response.status_code >= 500:
            if attempt >= max_retries:
                raise ProviderUnavailable(
                    f"{provider} returned {response.status_code}.",
                    provider=provider,
                )
            await sleeper(_delay(attempt, None))
            attempt += 1
            continue
        if response.status_code >= 400:
            raise ProviderError(
                f"{provider} returned {response.status_code}.",
                provider=provider,
            )
        return response.json()


def _delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 5)
        except ValueError:
            pass
    base = min(0.2 * (2**attempt), 2)
    return base + random.uniform(0, base / 2)

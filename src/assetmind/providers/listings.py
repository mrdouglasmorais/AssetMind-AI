"""B3 and crypto directories from the providers already in use.

brapi `/api/quote/list` supplies stocks and funds. A fund counts as a FII only
when its subtype is `fii`. CoinGecko `/coins/list` supplies crypto ids. The
article and quote history are not part of this directory. Results are cached
in memory so a chat question does not page the providers again.
"""

import time
from urllib.parse import urlparse

import httpx

from assetmind.domain.assets.catalog import CatalogEntry
from assetmind.domain.assets.identity import AssetClass, Market
from assetmind.providers.errors import ProviderError
from assetmind.providers.http import get_json

_CACHE_SECONDS = 6 * 60 * 60
_MAX_PAGES = 20
_cache_rows: list[CatalogEntry] | None = None
_cache_at = 0.0


def clear_listing_cache() -> None:
    global _cache_rows, _cache_at
    _cache_rows = None
    _cache_at = 0.0


def b3_entries(payload: dict[str, object]) -> list[CatalogEntry]:
    """Map one brapi list page. Stocks are equities. Only subtype `fii` is a FII."""

    stocks = payload.get("stocks")
    if not isinstance(stocks, list):
        return []
    entries: list[CatalogEntry] = []
    for item in stocks:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("stock") or "").strip().upper()
        name = " ".join(str(item.get("name") or symbol).split())
        kind = str(item.get("type") or "")
        subtype = str(item.get("subType") or "")
        if len(symbol) < 5 or not name:
            continue
        if kind == "stock":
            asset_class = AssetClass.EQUITY
        elif kind == "fund" and subtype == "fii":
            asset_class = AssetClass.REAL_ESTATE
        else:
            continue
        entries.append(CatalogEntry(symbol=symbol, asset_class=asset_class, market=Market.B3, name=name))
    return entries


def crypto_entries(payload: object) -> list[CatalogEntry]:
    """Map the CoinGecko coin list. The id is the symbol the quote endpoint accepts."""

    if not isinstance(payload, list):
        return []
    entries: list[CatalogEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("id") or "").strip().lower()
        name = " ".join(str(item.get("name") or symbol).split())
        if len(symbol) < 2 or not name or any(character.isspace() for character in symbol):
            continue
        entries.append(CatalogEntry(symbol=symbol, asset_class=AssetClass.CRYPTO, market=Market.CRYPTO, name=name))
    return entries


async def cached_listings(
    client: httpx.AsyncClient,
    *,
    brapi_base_url: str,
    brapi_api_key: str | None,
    coingecko_base_url: str,
    coingecko_api_key: str | None,
    now: float | None = None,
) -> list[CatalogEntry]:
    global _cache_rows, _cache_at
    clock = time.monotonic() if now is None else now
    if _cache_rows is not None and clock - _cache_at < _CACHE_SECONDS:
        return list(_cache_rows)
    entries = await fetch_listings(
        client,
        brapi_base_url=brapi_base_url,
        brapi_api_key=brapi_api_key,
        coingecko_base_url=coingecko_base_url,
        coingecko_api_key=coingecko_api_key,
    )
    _cache_rows = entries
    _cache_at = clock
    return list(entries)


async def fetch_listings(
    client: httpx.AsyncClient,
    *,
    brapi_base_url: str,
    brapi_api_key: str | None,
    coingecko_base_url: str,
    coingecko_api_key: str | None,
) -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    for kind in ("stock", "fund"):
        try:
            rows = await _brapi_rows(
                client,
                base_url=brapi_base_url,
                api_key=brapi_api_key,
                kind=kind,
            )
        except ProviderError:
            continue
        entries.extend(b3_entries({"stocks": rows}))
    try:
        coins = await _coin_list(client, base_url=coingecko_base_url, api_key=coingecko_api_key)
    except ProviderError:
        coins = []
    entries.extend(crypto_entries(coins))
    unique = _dedupe(entries)
    if not unique:
        raise ProviderError("Asset lists were unavailable.", provider="listings")
    return unique


async def _brapi_rows(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str | None,
    kind: str,
) -> list[object]:
    host = urlparse(base_url).hostname or ""
    url = f"{base_url.rstrip('/')}/api/quote/list"
    params: dict[str, object] = {"type": kind, "limit": 100}
    if api_key:
        params["token"] = api_key
    rows: list[object] = []
    for page in range(1, _MAX_PAGES + 1):
        payload = await get_json(
            client,
            url,
            provider="brapi",
            allowed_hosts={host},
            params={**params, "page": page},
            timeout=8,
            max_retries=2,
        )
        if not isinstance(payload, dict):
            break
        stocks = payload.get("stocks")
        if isinstance(stocks, list):
            rows.extend(stocks)
        if not payload.get("hasNextPage"):
            break
    return rows


async def _coin_list(client: httpx.AsyncClient, *, base_url: str, api_key: str | None) -> object:
    host = urlparse(base_url).hostname or ""
    headers = {"x-cg-demo-api-key": api_key} if api_key else None
    return await get_json(
        client,
        f"{base_url.rstrip('/')}/coins/list",
        provider="coingecko",
        allowed_hosts={host},
        headers=headers,
        timeout=8,
        max_retries=2,
    )


def _dedupe(entries: list[CatalogEntry]) -> list[CatalogEntry]:
    seen: set[tuple[str, str]] = set()
    unique: list[CatalogEntry] = []
    for entry in sorted(entries, key=lambda item: (item.asset_class.value, item.symbol)):
        key = (entry.asset_class.value, entry.symbol)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return unique

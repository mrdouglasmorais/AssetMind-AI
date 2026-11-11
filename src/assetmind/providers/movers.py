"""Rising and falling assets from brapi and CoinGecko.

Uses provider sort and pagination. Does not invent prices or volumes.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from assetmind.domain.assets.identity import AssetClass, Market
from assetmind.domain.assets.movers import (
    FIXTURE_MOVERS_LIMITATION,
    MOVERS_LIMITATION,
    MoverAssetType,
    MoverDirection,
    MoverItem,
    MoverSort,
    MoversPagination,
    MoversResult,
)
from assetmind.providers.errors import ProviderError
from assetmind.providers.http import get_json

_CACHE_SECONDS = 90.0
_cache: dict[tuple[object, ...], tuple[float, MoversResult]] = {}


def clear_movers_cache() -> None:
    _cache.clear()


def fixture_movers(
    *,
    direction: MoverDirection = MoverDirection.BOTH,
    asset_type: MoverAssetType = MoverAssetType.ALL,
    limit: int = 10,
    page: int = 1,
    min_volume: float = 0,
    sort_by: MoverSort = MoverSort.CHANGE,
    now: datetime | None = None,
) -> MoversResult:
    """Synthetic movers for fixture mode. Labeled samples, not live quotes."""

    retrieved = now or datetime.now(UTC)
    rows = _fixture_rows()
    filtered = [
        row
        for row in rows
        if (asset_type is MoverAssetType.ALL or row.asset_class.value == asset_type.value)
        and (row.volume is None or row.volume >= min_volume)
    ]
    rising_pool = [row for row in filtered if (row.change_percent or 0) > 0]
    falling_pool = [row for row in filtered if (row.change_percent or 0) < 0]
    rising_pool = _sort_items(rising_pool, sort_by=sort_by, descending=True)
    falling_pool = _sort_items(falling_pool, sort_by=sort_by, descending=sort_by is MoverSort.VOLUME)
    rising, has_next_rising = _page(rising_pool, page=page, limit=limit)
    falling, has_next_falling = _page(falling_pool, page=page, limit=limit)
    if direction is MoverDirection.UP:
        falling, has_next_falling = [], False
    elif direction is MoverDirection.DOWN:
        rising, has_next_rising = [], False
    return MoversResult(
        rising=rising,
        falling=falling,
        pagination=MoversPagination(
            page=page,
            limit=limit,
            has_next_rising=has_next_rising,
            has_next_falling=has_next_falling,
        ),
        retrieved_at=retrieved,
        limitation=FIXTURE_MOVERS_LIMITATION,
    )


async def cached_movers(
    client: httpx.AsyncClient,
    *,
    brapi_base_url: str,
    brapi_api_key: str | None,
    coingecko_base_url: str,
    coingecko_api_key: str | None,
    direction: MoverDirection = MoverDirection.BOTH,
    asset_type: MoverAssetType = MoverAssetType.ALL,
    limit: int = 10,
    page: int = 1,
    min_volume: float = 0,
    sort_by: MoverSort = MoverSort.CHANGE,
    now: float | None = None,
) -> MoversResult:
    key = (direction, asset_type, limit, page, min_volume, sort_by, brapi_base_url, coingecko_base_url)
    clock = time.monotonic() if now is None else now
    hit = _cache.get(key)
    if hit is not None and clock - hit[0] < _CACHE_SECONDS:
        return hit[1].model_copy(deep=True)
    result = await fetch_movers(
        client,
        brapi_base_url=brapi_base_url,
        brapi_api_key=brapi_api_key,
        coingecko_base_url=coingecko_base_url,
        coingecko_api_key=coingecko_api_key,
        direction=direction,
        asset_type=asset_type,
        limit=limit,
        page=page,
        min_volume=min_volume,
        sort_by=sort_by,
    )
    _cache[key] = (clock, result)
    return result.model_copy(deep=True)


async def fetch_movers(
    client: httpx.AsyncClient,
    *,
    brapi_base_url: str,
    brapi_api_key: str | None,
    coingecko_base_url: str,
    coingecko_api_key: str | None,
    direction: MoverDirection = MoverDirection.BOTH,
    asset_type: MoverAssetType = MoverAssetType.ALL,
    limit: int = 10,
    page: int = 1,
    min_volume: float = 0,
    sort_by: MoverSort = MoverSort.CHANGE,
) -> MoversResult:
    retrieved = datetime.now(UTC)
    rising: list[MoverItem] = []
    falling: list[MoverItem] = []
    has_next_rising = False
    has_next_falling = False
    notes: list[str] = []

    need_b3 = asset_type in (MoverAssetType.ALL, MoverAssetType.EQUITY, MoverAssetType.REAL_ESTATE)
    need_crypto = asset_type in (MoverAssetType.ALL, MoverAssetType.CRYPTO)

    if need_b3 and direction in (MoverDirection.BOTH, MoverDirection.UP):
        try:
            rows, more = await _brapi_movers(
                client,
                base_url=brapi_base_url,
                api_key=brapi_api_key,
                asset_type=asset_type,
                sort_order="desc",
                sort_by=sort_by,
                page=page,
                limit=limit,
                min_volume=min_volume,
            )
            rising.extend(rows)
            has_next_rising = has_next_rising or more
        except ProviderError as exc:
            notes.append(f"B3 rising unavailable: {exc.message}")

    if need_b3 and direction in (MoverDirection.BOTH, MoverDirection.DOWN):
        try:
            rows, more = await _brapi_movers(
                client,
                base_url=brapi_base_url,
                api_key=brapi_api_key,
                asset_type=asset_type,
                sort_order="asc",
                sort_by=sort_by,
                page=page,
                limit=limit,
                min_volume=min_volume,
            )
            falling.extend(rows)
            has_next_falling = has_next_falling or more
        except ProviderError as exc:
            notes.append(f"B3 falling unavailable: {exc.message}")

    if need_crypto and direction in (MoverDirection.BOTH, MoverDirection.UP):
        try:
            rows, more = await _crypto_movers(
                client,
                base_url=coingecko_base_url,
                api_key=coingecko_api_key,
                order="price_change_percentage_24h_desc",
                page=page,
                limit=limit,
                min_volume=min_volume,
                sort_by=sort_by,
            )
            rising.extend(rows)
            has_next_rising = has_next_rising or more
        except ProviderError as exc:
            notes.append(f"Crypto rising unavailable: {exc.message}")

    if need_crypto and direction in (MoverDirection.BOTH, MoverDirection.DOWN):
        try:
            rows, more = await _crypto_movers(
                client,
                base_url=coingecko_base_url,
                api_key=coingecko_api_key,
                order="price_change_percentage_24h_asc",
                page=page,
                limit=limit,
                min_volume=min_volume,
                sort_by=sort_by,
            )
            falling.extend(rows)
            has_next_falling = has_next_falling or more
        except ProviderError as exc:
            notes.append(f"Crypto falling unavailable: {exc.message}")

    if asset_type is MoverAssetType.ALL:
        rising = _sort_items(rising, sort_by=sort_by, descending=True)[:limit]
        falling = _sort_items(
            falling,
            sort_by=sort_by,
            descending=sort_by is MoverSort.VOLUME,
        )[:limit]

    limitation = MOVERS_LIMITATION
    if notes:
        limitation = f"{MOVERS_LIMITATION} {' '.join(notes)}"

    return MoversResult(
        rising=rising,
        falling=falling,
        pagination=MoversPagination(
            page=page,
            limit=limit,
            has_next_rising=has_next_rising,
            has_next_falling=has_next_falling,
        ),
        retrieved_at=retrieved,
        limitation=limitation,
    )


async def _brapi_movers(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str | None,
    asset_type: MoverAssetType,
    sort_order: str,
    sort_by: MoverSort,
    page: int,
    limit: int,
    min_volume: float,
) -> tuple[list[MoverItem], bool]:
    host = urlparse(base_url).hostname or ""
    url = f"{base_url.rstrip('/')}/api/quote/list"
    kinds = _brapi_kinds(asset_type)
    items: list[MoverItem] = []
    has_next = False
    for kind, subtype in kinds:
        params: dict[str, object] = {
            "type": kind,
            "sortBy": "volume" if sort_by is MoverSort.VOLUME else "change",
            "sortOrder": sort_order,
            "limit": limit,
            "page": page,
        }
        if subtype:
            params["subType"] = subtype
        if api_key:
            params["token"] = api_key
        payload = await get_json(
            client,
            url,
            provider="brapi",
            allowed_hosts={host},
            params=params,
            timeout=8,
            max_retries=2,
        )
        if not isinstance(payload, dict):
            continue
        stocks = payload.get("stocks")
        if not isinstance(stocks, list):
            continue
        mapped = [row for row in (_map_brapi_row(item) for item in stocks) if row is not None]
        mapped = [row for row in mapped if row.volume is None or row.volume >= min_volume]
        if sort_order == "desc":
            mapped = [row for row in mapped if (row.change_percent or 0) > 0] if sort_by is MoverSort.CHANGE else mapped
        else:
            mapped = [row for row in mapped if (row.change_percent or 0) < 0] if sort_by is MoverSort.CHANGE else mapped
        items.extend(mapped)
        if payload.get("hasNextPage"):
            has_next = True
    items = _sort_items(
        items,
        sort_by=sort_by,
        descending=sort_order == "desc" or sort_by is MoverSort.VOLUME,
    )[:limit]
    return items, has_next


async def _crypto_movers(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str | None,
    order: str,
    page: int,
    limit: int,
    min_volume: float,
    sort_by: MoverSort,
) -> tuple[list[MoverItem], bool]:
    host = urlparse(base_url).hostname or ""
    headers = {"x-cg-demo-api-key": api_key} if api_key else None
    market_order = "volume_desc" if sort_by is MoverSort.VOLUME else order
    payload = await get_json(
        client,
        f"{base_url.rstrip('/')}/coins/markets",
        provider="coingecko",
        allowed_hosts={host},
        params={
            "vs_currency": "usd",
            "order": market_order,
            "per_page": limit,
            "page": page,
            "price_change_percentage": "24h",
        },
        headers=headers,
        timeout=8,
        max_retries=2,
    )
    if not isinstance(payload, list):
        return [], False
    items: list[MoverItem] = []
    for item in payload:
        mapped = _map_coingecko_row(item)
        if mapped is None:
            continue
        if mapped.volume is not None and mapped.volume < min_volume:
            continue
        if "desc" in order and sort_by is MoverSort.CHANGE and (mapped.change_percent or 0) <= 0:
            continue
        if "asc" in order and sort_by is MoverSort.CHANGE and (mapped.change_percent or 0) >= 0:
            continue
        items.append(mapped)
    if sort_by is MoverSort.VOLUME and "asc" in order:
        items = [row for row in items if (row.change_percent or 0) < 0]
        items = _sort_items(items, sort_by=sort_by, descending=True)
    elif sort_by is MoverSort.VOLUME:
        items = [row for row in items if (row.change_percent or 0) > 0]
        items = _sort_items(items, sort_by=sort_by, descending=True)
    has_next = len(payload) >= limit
    return items[:limit], has_next


def _brapi_kinds(asset_type: MoverAssetType) -> list[tuple[str, str | None]]:
    if asset_type is MoverAssetType.EQUITY:
        return [("stock", None)]
    if asset_type is MoverAssetType.REAL_ESTATE:
        return [("fund", "fii")]
    if asset_type is MoverAssetType.ALL:
        return [("stock", None), ("fund", "fii")]
    return []


def _map_brapi_row(item: object) -> MoverItem | None:
    if not isinstance(item, dict):
        return None
    symbol = str(item.get("stock") or "").strip().upper()
    name = " ".join(str(item.get("name") or symbol).split())
    kind = str(item.get("type") or "")
    subtype = str(item.get("subType") or "")
    if len(symbol) < 5 or not name:
        return None
    if kind == "stock":
        asset_class = AssetClass.EQUITY
    elif kind == "fund" and subtype == "fii":
        asset_class = AssetClass.REAL_ESTATE
    else:
        return None
    change = _float(item.get("change"))
    volume = _float(item.get("volume"))
    price = _float(item.get("close"))
    return MoverItem(
        symbol=symbol,
        name=name,
        asset_class=asset_class,
        market=Market.B3,
        price=price,
        change_percent=change,
        volume=volume,
        currency="BRL",
    )


def _map_coingecko_row(item: object) -> MoverItem | None:
    if not isinstance(item, dict):
        return None
    symbol = str(item.get("id") or "").strip().lower()
    name = " ".join(str(item.get("name") or symbol).split())
    if len(symbol) < 2 or not name or any(character.isspace() for character in symbol):
        return None
    change = _float(item.get("price_change_percentage_24h"))
    volume = _float(item.get("total_volume"))
    price = _float(item.get("current_price"))
    return MoverItem(
        symbol=symbol,
        name=name,
        asset_class=AssetClass.CRYPTO,
        market=Market.CRYPTO,
        price=price,
        change_percent=change,
        volume=volume,
        currency="USD",
    )


def _fixture_rows() -> list[MoverItem]:
    return [
        MoverItem(
            symbol="PETR4",
            name="Petrobras PN",
            asset_class=AssetClass.EQUITY,
            market=Market.B3,
            price=36.65,
            change_percent=2.4,
            volume=27_000_000,
            currency="BRL",
        ),
        MoverItem(
            symbol="VALE3",
            name="Vale ON",
            asset_class=AssetClass.EQUITY,
            market=Market.B3,
            price=52.1,
            change_percent=-1.8,
            volume=18_000_000,
            currency="BRL",
        ),
        MoverItem(
            symbol="ITUB4",
            name="Itau Unibanco PN",
            asset_class=AssetClass.EQUITY,
            market=Market.B3,
            price=31.2,
            change_percent=1.1,
            volume=12_000_000,
            currency="BRL",
        ),
        MoverItem(
            symbol="MGLU3",
            name="Magazine Luiza ON",
            asset_class=AssetClass.EQUITY,
            market=Market.B3,
            price=8.4,
            change_percent=-3.2,
            volume=40_000_000,
            currency="BRL",
        ),
        MoverItem(
            symbol="HGLG11",
            name="CSHG Logistica FII",
            asset_class=AssetClass.REAL_ESTATE,
            market=Market.B3,
            price=160.0,
            change_percent=0.8,
            volume=900_000,
            currency="BRL",
        ),
        MoverItem(
            symbol="MXRF11",
            name="Maxi Renda FII",
            asset_class=AssetClass.REAL_ESTATE,
            market=Market.B3,
            price=10.1,
            change_percent=-0.6,
            volume=1_200_000,
            currency="BRL",
        ),
        MoverItem(
            symbol="bitcoin",
            name="Bitcoin",
            asset_class=AssetClass.CRYPTO,
            market=Market.CRYPTO,
            price=68_000.0,
            change_percent=3.5,
            volume=25_000_000_000,
            currency="USD",
        ),
        MoverItem(
            symbol="ethereum",
            name="Ethereum",
            asset_class=AssetClass.CRYPTO,
            market=Market.CRYPTO,
            price=3_400.0,
            change_percent=-2.1,
            volume=12_000_000_000,
            currency="USD",
        ),
    ]


def _sort_items(items: list[MoverItem], *, sort_by: MoverSort, descending: bool) -> list[MoverItem]:
    def by_volume(item: MoverItem) -> float:
        return item.volume if item.volume is not None else float("-inf")

    def by_change(item: MoverItem) -> float:
        return item.change_percent if item.change_percent is not None else float("-inf")

    key = by_volume if sort_by is MoverSort.VOLUME else by_change
    return sorted(items, key=key, reverse=descending)


def _page(items: list[MoverItem], *, page: int, limit: int) -> tuple[list[MoverItem], bool]:
    start = (page - 1) * limit
    end = start + limit
    return items[start:end], end < len(items)


def _float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None

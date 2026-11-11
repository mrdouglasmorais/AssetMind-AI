import httpx
import pytest

from assetmind.domain.assets.identity import AssetClass
from assetmind.domain.assets.movers import MoverAssetType, MoverDirection, MoverSort
from assetmind.providers.movers import clear_movers_cache, fetch_movers, fixture_movers


def test_fixture_movers_split_rising_and_falling() -> None:
    result = fixture_movers(direction=MoverDirection.BOTH, limit=10, page=1)
    assert result.rising
    assert result.falling
    assert all((item.change_percent or 0) > 0 for item in result.rising)
    assert all((item.change_percent or 0) < 0 for item in result.falling)
    assert "synthetic" in result.limitation.lower() or "fixture" in result.limitation.lower()


def test_fixture_movers_respect_type_limit_volume_and_direction() -> None:
    equity = fixture_movers(asset_type=MoverAssetType.EQUITY, direction=MoverDirection.UP, limit=1)
    assert len(equity.rising) == 1
    assert equity.rising[0].asset_class is AssetClass.EQUITY
    assert equity.falling == []
    filtered = fixture_movers(min_volume=20_000_000, direction=MoverDirection.DOWN)
    assert all((item.volume or 0) >= 20_000_000 for item in filtered.falling)
    page_two = fixture_movers(direction=MoverDirection.UP, limit=1, page=2)
    assert page_two.rising
    assert page_two.pagination.page == 2


@pytest.mark.asyncio
async def test_live_movers_map_brapi_and_coingecko_pages() -> None:
    clear_movers_cache()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "brapi.test":
            order = request.url.params.get("sortOrder")
            kind = request.url.params.get("type")
            if kind == "stock" and order == "desc":
                body = {
                    "stocks": [
                        {
                            "stock": "PETR4",
                            "name": "Petrobras",
                            "type": "stock",
                            "subType": "stock",
                            "close": 36.0,
                            "change": 2.0,
                            "volume": 10_000_000,
                        }
                    ],
                    "hasNextPage": False,
                }
            elif kind == "stock" and order == "asc":
                body = {
                    "stocks": [
                        {
                            "stock": "VALE3",
                            "name": "Vale",
                            "type": "stock",
                            "subType": "stock",
                            "close": 50.0,
                            "change": -1.5,
                            "volume": 8_000_000,
                        }
                    ],
                    "hasNextPage": False,
                }
            elif kind == "fund":
                body = {"stocks": [], "hasNextPage": False}
            else:
                body = {"stocks": [], "hasNextPage": False}
            return httpx.Response(200, json=body)
        if request.url.host == "coingecko.test":
            order = request.url.params.get("order", "")
            if "desc" in order:
                body = [
                    {
                        "id": "bitcoin",
                        "name": "Bitcoin",
                        "current_price": 68000,
                        "price_change_percentage_24h": 3.0,
                        "total_volume": 1_000_000_000,
                    }
                ]
            else:
                body = [
                    {
                        "id": "ethereum",
                        "name": "Ethereum",
                        "current_price": 3400,
                        "price_change_percentage_24h": -2.0,
                        "total_volume": 500_000_000,
                    }
                ]
            return httpx.Response(200, json=body)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await fetch_movers(
            client,
            brapi_base_url="https://brapi.test",
            brapi_api_key=None,
            coingecko_base_url="https://coingecko.test/api/v3",
            coingecko_api_key=None,
            direction=MoverDirection.BOTH,
            asset_type=MoverAssetType.ALL,
            limit=10,
            page=1,
            sort_by=MoverSort.CHANGE,
        )
    symbols_up = {item.symbol for item in result.rising}
    symbols_down = {item.symbol for item in result.falling}
    assert "PETR4" in symbols_up
    assert "bitcoin" in symbols_up
    assert "VALE3" in symbols_down
    assert "ethereum" in symbols_down

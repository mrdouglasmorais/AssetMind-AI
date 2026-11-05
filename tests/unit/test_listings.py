import httpx
import pytest

from assetmind.agents.chat import assets_from_message
from assetmind.domain.assets.catalog import CatalogEntry, search_entries
from assetmind.domain.assets.identity import AssetClass, Market
from assetmind.providers.errors import ProviderError
from assetmind.providers.listings import b3_entries, clear_listing_cache, crypto_entries, fetch_listings


def test_brapi_stocks_and_fii_subtype_become_catalog_rows() -> None:
    entries = b3_entries(
        {
            "stocks": [
                {"stock": "WEGE3", "name": "WEG S.A.", "type": "stock", "subType": "stock"},
                {"stock": "HGLG11", "name": "Patria Log", "type": "fund", "subType": "fii"},
                {"stock": "BOVA11", "name": "ETF", "type": "fund", "subType": "etf"},
                {"stock": "AAPL34", "name": "Apple", "type": "bdr", "subType": "bdr"},
            ]
        }
    )
    assert [(item.symbol, item.asset_class) for item in entries] == [
        ("WEGE3", AssetClass.EQUITY),
        ("HGLG11", AssetClass.REAL_ESTATE),
    ]


def test_coingecko_ids_are_crypto_and_web_is_not_an_asset_word() -> None:
    entries = crypto_entries(
        [
            {"id": "solana", "symbol": "sol", "name": "Solana"},
            {"id": "web", "symbol": "web", "name": "Web"},
        ]
    )
    assert entries[0].symbol == "solana"
    assert entries[0].market is Market.CRYPTO
    found = assets_from_message("analise de web", entries + b3_entries({"stocks": []}))
    assert found == []
    solana = assets_from_message("analise solana", entries)
    assert solana[0].symbol == "solana"
    weg = assets_from_message(
        "analise WEGE3",
        [
            CatalogEntry(symbol="WEGE3", asset_class=AssetClass.EQUITY, market=Market.B3, name="WEG S.A."),
        ],
    )
    assert weg[0].asset_class is AssetClass.EQUITY
    assert search_entries(entries, "sol", limit=5)[0].symbol == "solana"


@pytest.mark.asyncio
async def test_listing_fetch_reads_brapi_pages_and_coingecko_ids() -> None:
    clear_listing_cache()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "brapi.test":
            kind = request.url.params["type"]
            if kind == "stock":
                body = {
                    "stocks": [{"stock": "PETR4", "name": "Petrobras", "type": "stock", "subType": "stock"}],
                    "hasNextPage": False,
                }
            else:
                body = {
                    "stocks": [{"stock": "MXRF11", "name": "Maxi", "type": "fund", "subType": "fii"}],
                    "hasNextPage": False,
                }
            return httpx.Response(200, json=body)
        return httpx.Response(200, json=[{"id": "bitcoin", "name": "Bitcoin"}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        entries = await fetch_listings(
            client,
            brapi_base_url="https://brapi.test",
            brapi_api_key=None,
            coingecko_base_url="https://gecko.test",
            coingecko_api_key=None,
        )
    symbols = {item.symbol for item in entries}
    assert symbols == {"PETR4", "MXRF11", "bitcoin"}


@pytest.mark.asyncio
async def test_listing_fetch_reports_when_every_source_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError):
            await fetch_listings(
                client,
                brapi_base_url="https://brapi.test",
                brapi_api_key=None,
                coingecko_base_url="https://gecko.test",
                coingecko_api_key=None,
            )

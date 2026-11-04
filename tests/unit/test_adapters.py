"""HTTP adapters exercised with a mock transport. No live network."""

from datetime import UTC, datetime

import httpx
import pytest

from assetmind.application.budget import BudgetManager
from assetmind.domain.assets.identity import AssetClass, AssetRequest, resolve_asset
from assetmind.domain.errors import BudgetExceededError
from assetmind.providers.bcb import BancoCentralProvider
from assetmind.providers.brapi import BrapiProvider
from assetmind.providers.circuit import CircuitBreaker
from assetmind.providers.coingecko import CoinGeckoProvider
from assetmind.providers.cvm import CvmProvider
from assetmind.providers.errors import ProviderError, ProviderTimeout, ProviderUnavailable
from assetmind.providers.http import get_json
from assetmind.providers.registry import ProviderRegistry


def _equity():
    return resolve_asset(AssetRequest(symbol="PETR4"))


def _crypto():
    return resolve_asset(AssetRequest(symbol="bitcoin", asset_class=AssetClass.CRYPTO))


@pytest.mark.asyncio
async def test_brapi_coingecko_and_bcb_fetch() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)

    def brapi(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("quote"):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": "PETR4",
                            "regularMarketPrice": 10,
                            "currency": "BRL",
                            "regularMarketTime": "2026-11-04T12:00:00+00:00",
                            "regularMarketVolume": 5,
                            "marketCap": 100,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "PETR4",
                        "historicalDataPrice": [{"date": 1762200000, "close": 10, "adjustedClose": 10}],
                    }
                ]
            },
        )

    def gecko(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("market_chart"):
            return httpx.Response(200, json={"prices": [[1762200000000, 20.0]]})
        return httpx.Response(
            200,
            json=[{"id": "bitcoin", "current_price": 20, "market_cap": 30, "total_volume": 40}],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(brapi)) as client:
        snapshot = await BrapiProvider(client, api_key="token").fetch(_equity(), as_of=None, now=now)
    assert snapshot.evidence[0].value == 10
    assert snapshot.prices[0].close == 10

    async with httpx.AsyncClient(transport=httpx.MockTransport(gecko)) as client:
        crypto = await CoinGeckoProvider(client, api_key="demo").fetch(_crypto(), as_of=None, now=now)
    assert any(item.metric == "market_cap" and item.value == 30 for item in crypto.evidence)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[{"data": "04/11/2026", "valor": "15"}]))
    ) as client:
        selic = await BancoCentralProvider(client).latest_selic(now=now)
    assert selic.value == 15


@pytest.mark.asyncio
async def test_http_timeout_server_error_and_client_error() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ProviderTimeout):
            await get_json(
                client,
                "https://brapi.dev/quote",
                provider="brapi",
                allowed_hosts={"brapi.dev"},
                max_retries=0,
                sleeper=_noop,
            )

    def server(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(server)) as client:
        with pytest.raises(ProviderUnavailable):
            await get_json(
                client,
                "https://brapi.dev/quote",
                provider="brapi",
                allowed_hosts={"brapi.dev"},
                max_retries=0,
                sleeper=_noop,
            )

    def missing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(missing)) as client:
        with pytest.raises(ProviderError):
            await get_json(
                client,
                "https://brapi.dev/quote",
                provider="brapi",
                allowed_hosts={"brapi.dev"},
                max_retries=0,
                sleeper=_noop,
            )


@pytest.mark.asyncio
async def test_registry_cache_budget_and_live_cvm_gap() -> None:
    from assetmind.providers.fixtures import FixtureMacroProvider, FixtureMarketProvider

    now = datetime(2026, 11, 4, tzinfo=UTC)
    budget = BudgetManager()
    registry = ProviderRegistry(
        brapi=FixtureMarketProvider(),
        coingecko=FixtureMarketProvider(),
        bcb=FixtureMacroProvider(),
        cvm=CvmProvider(use_fixtures=True),
        budget=budget,
    )
    asset = resolve_asset(AssetRequest(symbol="HGLG11", asset_class=AssetClass.REAL_ESTATE))
    first = await registry.fetch_asset(asset, as_of=None, now=now)
    calls = budget.provider_calls
    second = await registry.fetch_asset(asset, as_of=None, now=now)
    assert second.asset.symbol == first.asset.symbol
    assert budget.provider_calls == calls

    blocked = ProviderRegistry(
        brapi=FixtureMarketProvider(),
        coingecko=FixtureMarketProvider(),
        bcb=FixtureMacroProvider(),
        cvm=CvmProvider(use_fixtures=False),
        budget=BudgetManager(),
    )
    blocked.budget.limits.max_provider_calls = 0
    with pytest.raises(BudgetExceededError):
        await blocked.fetch_asset(_equity(), as_of=None, now=now)
    facts = await CvmProvider(use_fixtures=False).fund_facts(_equity(), now=now)
    assert facts.classification.value == "unknown"
    missing = await CvmProvider(use_fixtures=True).fund_facts(_equity(), now=now)
    assert missing.classification.value == "unknown"


def test_circuit_closes_after_the_window() -> None:
    breaker = CircuitBreaker(name="brapi", failure_threshold=1, reset_after=0)
    past = datetime(2020, 1, 1, tzinfo=UTC)
    breaker.record_failure(past)
    breaker.before_call(datetime(2026, 1, 1, tzinfo=UTC))
    breaker.record_success()
    assert breaker.failures == 0


async def _noop(_: float) -> None:
    return None

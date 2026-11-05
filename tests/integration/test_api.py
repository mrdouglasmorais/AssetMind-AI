import json

import httpx
import pytest

from assetmind.api.app import create_app
from assetmind.config.settings import Settings


@pytest.mark.asyncio
async def test_public_health_and_authenticated_analysis(api_client: httpx.AsyncClient) -> None:
    health = await api_client.get("/health")
    assert health.status_code == 200
    ready = await api_client.get("/ready")
    assert ready.status_code == 200
    rejected = await api_client.post("/api/v1/analyses", json={"assets": [{"symbol": "PETR4"}]})
    assert rejected.status_code == 401
    ambiguous = await api_client.post(
        "/api/v1/analyses",
        headers={"X-API-Key": "test-key-123"},
        json={"assets": [{"symbol": "HGLG11"}]},
    )
    assert ambiguous.status_code == 422
    created = await api_client.post(
        "/api/v1/analyses",
        headers={"X-API-Key": "test-key-123", "X-Correlation-ID": "corr-1234"},
        json={
            "assets": [
                {"symbol": "PETR4"},
                {"symbol": "bitcoin", "asset_class": "crypto"},
                {"symbol": "HGLG11", "asset_class": "real_estate"},
                {"symbol": "MXRF11", "asset_class": "real_estate"},
            ]
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["correlation_id"] == "corr-1234"
    assert body["status"] in {"completed", "partial"}
    rendered = json.dumps(body["report"])
    assert "guaranteed buy" not in rendered
    assert "PETR4" in rendered
    assert "bitcoin" in rendered
    report = await api_client.get(
        f"/api/v1/analyses/{body['analysis_id']}/report",
        headers={"X-API-Key": "test-key-123"},
    )
    assert report.status_code == 200
    events = await api_client.get(
        f"/api/v1/analyses/{body['analysis_id']}/events",
        headers={"X-API-Key": "test-key-123"},
    )
    assert "data:" in events.text
    search = await api_client.get(
        "/api/v1/assets/search",
        params={"q": "petro"},
        headers={"X-API-Key": "test-key-123"},
    )
    assert search.json()["results"][0]["symbol"] == "PETR4"
    listed = await api_client.get(
        "/api/v1/assets/search",
        params={"q": ""},
        headers={"X-API-Key": "test-key-123"},
    )
    body = listed.json()
    assert {row["symbol"] for row in body["by_type"]["equity"]} >= {"PETR4", "VALE3"}
    assert body["by_type"]["real_estate"][0]["symbol"] == "HGLG11"
    assert {row["symbol"] for row in body["by_type"]["crypto"]} == {"bitcoin", "ethereum"}


@pytest.mark.asyncio
async def test_usage_balance_reports_the_allowance(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/usage/balance", headers={"X-API-Key": "test-key-123"})
    assert response.status_code == 200
    body = response.json()
    assert body["analyses"] == 0
    assert body["remaining_tokens"] == body["allowance_tokens"]
    assert body["estimated_tokens"] == 0


@pytest.mark.asyncio
async def test_invalid_symbol_and_agentos_disabled(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/analyses",
        headers={"X-API-Key": "test-key-123"},
        json={"assets": [{"symbol": "???"}]},
    )
    assert response.status_code == 422
    hidden = await api_client.get("/workflows")
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_agentos_requires_a_token(tmp_path: object) -> None:
    database = tmp_path / "os.db"  # type: ignore[operator]
    settings = Settings(
        api_key="test-key-123",
        provider_mode="fixtures",
        database_url=f"sqlite+pysqlite:///{database}",
        agentos_enabled=True,
        agentos_jwt_secret="test-secret-value-which-is-long",
    )
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.json()["status"] == "ok"
        blocked = await client.get("/workflows")
        assert blocked.status_code in {401, 403}


def test_state_machine_and_catalog() -> None:
    from assetmind.application.state import RunState, StateMachine
    from assetmind.domain.assets.catalog import search_catalog

    machine = StateMachine()
    machine.finish(RunState.PARTIAL)
    assert machine.state is RunState.PARTIAL
    assert search_catalog("hglg")[0].asset_class.value == "real_estate"

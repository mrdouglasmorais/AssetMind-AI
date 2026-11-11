import httpx
import pytest


@pytest.mark.asyncio
async def test_movers_endpoint_returns_fixture_lists(api_client: httpx.AsyncClient) -> None:
    missing = await api_client.get("/api/v1/assets/movers")
    assert missing.status_code == 401

    response = await api_client.get(
        "/api/v1/assets/movers",
        headers={"X-API-Key": "test-key-123"},
        params={
            "direction": "both",
            "type": "equity",
            "limit": 2,
            "page": 1,
            "min_volume": 0,
            "sort_by": "change",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rising"]
    assert body["falling"]
    assert body["pagination"]["limit"] == 2
    assert body["pagination"]["page"] == 1
    assert all(item["asset_class"] == "equity" for item in body["rising"] + body["falling"])
    assert "limitation" in body

    invalid = await api_client.get(
        "/api/v1/assets/movers",
        headers={"X-API-Key": "test-key-123"},
        params={"limit": 0},
    )
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_openapi_lists_movers_and_scalar_path(api_client: httpx.AsyncClient) -> None:
    schema = await api_client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/v1/assets/movers" in paths
    assert "/scalar" not in paths

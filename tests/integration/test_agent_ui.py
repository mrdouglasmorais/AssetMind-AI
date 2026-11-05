import httpx
import pytest

from assetmind.agents.chat import assets_from_message
from assetmind.api.app import create_app
from assetmind.config.settings import Settings


def test_chat_resolves_catalog_names_and_aliases() -> None:
    assets = assets_from_message("Compare Petrobras with BTC and HGLG11")
    symbols = [asset.symbol for asset in assets]
    assert symbols == ["PETR4", "HGLG11", "bitcoin"]
    assert [asset.symbol for asset in assets_from_message("analise completa NATU3")] == ["NATU3"]


@pytest.mark.asyncio
async def test_docs_redirect_to_the_agent_ui(api_client: httpx.AsyncClient) -> None:
    docs = await api_client.get("/docs")
    assert docs.status_code == 307
    assert docs.headers["location"] == "http://127.0.0.1:3000"
    assert "swagger" not in docs.text.lower()
    home = await api_client.get("/")
    assert home.status_code == 307


@pytest.mark.asyncio
async def test_agent_ui_run_uses_the_deterministic_report(tmp_path: object) -> None:
    database = tmp_path / "ui.db"  # type: ignore[operator]
    settings = Settings(
        api_key="test-key-123",
        provider_mode="fixtures",
        database_url=f"sqlite+pysqlite:///{database}",
        agentos_enabled=True,
        agentos_jwt_secret=None,
        groq_api_key=None,
        os_security_key="ui-token",
    )
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        hidden = await client.get("/agents")
        assert hidden.status_code == 401
        listed = await client.get("/agents", headers={"Authorization": "Bearer ui-token"})
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == "assetmind-analyst"
        analysis = await client.post(
            "/api/v1/analyses",
            headers={"X-API-Key": "test-key-123"},
            json={"assets": [{"symbol": "PETR4"}]},
        )
        assert analysis.status_code == 200
        run = await client.post(
            "/agents/assetmind-analyst/runs",
            headers={"Authorization": "Bearer ui-token"},
            data={"message": "Analise PETR4", "stream": "false"},
        )
        assert run.status_code == 200
        body = run.text
        assert "PETR4" in body
        assert "guaranteed buy" not in body

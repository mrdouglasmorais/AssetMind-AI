"""Test helpers."""

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from assetmind.api.app import create_app
from assetmind.config.settings import Settings


@pytest.fixture
def settings(tmp_path: object) -> Settings:
    database = tmp_path / "test.db"  # type: ignore[operator]
    return Settings(
        api_key="test-key-123",
        provider_mode="fixtures",
        database_url=f"sqlite+pysqlite:///{database}",
        agentos_enabled=False,
        cors_origins="",
        rate_limit_per_minute=100,
    )


@pytest.fixture
async def api_client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

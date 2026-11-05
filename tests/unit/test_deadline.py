import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest

from assetmind.application.budget import BudgetManager
from assetmind.application.service import AnalysisService
from assetmind.domain.assets.identity import AssetRequest, resolve_asset
from assetmind.domain.errors import DeadlineExceeded
from assetmind.observability.logging import configure_logging
from assetmind.persistence.db import create_db_engine, create_schema, create_session_factory
from assetmind.persistence.repository import AnalysisRepository
from assetmind.providers.cvm import CvmProvider
from assetmind.providers.registry import ProviderRegistry


class _Slow:
    async def fetch(self, asset: object, *, as_of: object, now: object) -> object:
        await asyncio.sleep(5)
        raise AssertionError("the deadline must cancel this fetch")


@pytest.mark.asyncio
async def test_in_flight_provider_call_is_cancelled_at_the_deadline() -> None:
    registry = ProviderRegistry(
        brapi=_Slow(),
        coingecko=_Slow(),
        bcb=_Slow(),
        cvm=CvmProvider(use_fixtures=True),
        budget=BudgetManager(),
    )
    registry.deadline = datetime.now(UTC) + timedelta(milliseconds=50)
    started = time.perf_counter()
    with pytest.raises(DeadlineExceeded):
        await registry.fetch_asset(resolve_asset(AssetRequest(symbol="PETR4")), as_of=None, now=datetime.now(UTC))
    assert time.perf_counter() - started < 1


@pytest.mark.asyncio
async def test_analysis_stops_when_the_deadline_passes_during_fetch(tmp_path: object) -> None:
    database = tmp_path / "deadline.db"  # type: ignore[operator]
    engine = create_db_engine(f"sqlite+pysqlite:///{database}")
    create_schema(engine)
    repository = AnalysisRepository(create_session_factory(engine))

    def registry_factory(budget: BudgetManager) -> ProviderRegistry:
        return ProviderRegistry(
            brapi=_Slow(),
            coingecko=_Slow(),
            bcb=_Slow(),
            cvm=CvmProvider(use_fixtures=True),
            budget=budget,
        )

    service = AnalysisService(repository, registry_factory, configure_logging(), lambda _count: BudgetManager())
    started = time.perf_counter()
    stored = await service.run(
        assets=[AssetRequest(symbol="PETR4")],
        scenarios=None,
        correlation_id="corr-deadline",
        as_of=None,
        deadline_seconds=0.05,
    )
    assert time.perf_counter() - started < 1
    assert stored.status == "failed"
    assert stored.error_code in {None, "deadline"}
    engine.dispose()

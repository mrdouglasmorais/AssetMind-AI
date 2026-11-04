from datetime import UTC, datetime, timedelta

import pytest

from assetmind.application.context import build_narrative_context
from assetmind.application.report import parse_structured_narrative
from assetmind.domain.analysis.engine import AssetAnalysis
from assetmind.domain.analysis.metrics import MetricResult
from assetmind.domain.assets.identity import AssetClass, Market, ResolvedAsset
from assetmind.domain.errors import StructuredOutputError
from assetmind.persistence.db import normalize_database_url


def test_context_truncation_and_database_urls() -> None:
    analysis = AssetAnalysis(
        asset=ResolvedAsset(
            symbol="PETR4",
            asset_class=AssetClass.EQUITY,
            market=Market.B3,
            classification_confidence="pattern",
        ),
        status="completed",
        metrics=[
            MetricResult(
                name="reference_price",
                value=10,
                unit="BRL",
                formula="latest",
                sampling="1",
                interpretation="reference",
            )
        ],
    )
    text = build_narrative_context([analysis], max_chars=30)
    assert "truncated" in text
    assert normalize_database_url("postgres://db/app").startswith("postgresql+psycopg://")
    assert normalize_database_url("postgresql://db/app").startswith("postgresql+psycopg://")
    with pytest.raises(StructuredOutputError):
        parse_structured_narrative({"narrative": "  "})


def test_gateway_rate_limit_and_terminal_state() -> None:
    from assetmind.application.state import InvalidTransition, RunState, StateMachine
    from assetmind.models.gateway import build_openrouter
    from assetmind.security.rate_limit import RateLimiter
    from assetmind.tools import assert_allowed_url

    assert_allowed_url("https://brapi.dev/api", {"brapi.dev"})
    model = build_openrouter(model_id="openai/gpt-4o-mini", api_key="test", max_tokens=16)
    assert model.id == "openai/gpt-4o-mini"
    limiter = RateLimiter(limit=1)
    assert limiter.allow("client", now=10)
    assert limiter.allow("client", now=10) is False
    machine = StateMachine(RunState.COMPLETED)
    with pytest.raises(InvalidTransition):
        machine.move(RunState.FAILED)
    with pytest.raises(ValueError):
        build_openrouter(model_id="", api_key="test", max_tokens=16)
    from assetmind.domain.assets.identity import AssetRequest, resolve_asset
    from assetmind.domain.errors import InvalidAssetError
    from assetmind.domain.scenarios.policy import ScenarioAssumptions, resolve_scenarios

    scenarios = resolve_scenarios(ScenarioAssumptions(bear=-0.2, base=0, bull=0.2))
    assert scenarios[0].label == "user_assumption"
    with pytest.raises(InvalidAssetError):
        resolve_asset(AssetRequest(symbol="bad ticker"))
    with pytest.raises(InvalidAssetError):
        resolve_asset(AssetRequest(symbol="bitcoin", asset_class=AssetClass.EQUITY))
    now = datetime(2026, 11, 4, tzinfo=UTC)
    assert now - timedelta(days=1) < now

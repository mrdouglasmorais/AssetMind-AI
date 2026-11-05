from datetime import UTC, datetime, timedelta

import pytest

from assetmind.application.budget import BudgetManager
from assetmind.domain.analysis.engine import MarketSnapshot, analyze_snapshot
from assetmind.domain.assets.identity import AssetClass, AssetRequest, resolve_asset
from assetmind.domain.errors import AmbiguousAssetError, InvalidAssetError
from assetmind.domain.evidence.models import (
    Evidence,
    FundClassification,
    FundFacts,
    PricePoint,
    QualityStatus,
)
from assetmind.domain.scenarios.policy import resolve_scenarios


def _prices(now: datetime, closes: list[float]) -> list[PricePoint]:
    return [
        PricePoint(observed_at=now - timedelta(days=len(closes) - 1 - index), close=close, currency="BRL")
        for index, close in enumerate(closes)
    ]


def test_resolves_equity_crypto_and_rejects_ambiguous_fii() -> None:
    equity = resolve_asset(AssetRequest(symbol="petr4"))
    crypto = resolve_asset(AssetRequest(symbol="BTC"))
    assert equity.asset_class is AssetClass.EQUITY
    assert crypto.symbol == "bitcoin"
    with pytest.raises(AmbiguousAssetError):
        resolve_asset(AssetRequest(symbol="HGLG11"))
    fund = resolve_asset(AssetRequest(symbol="HGLG11", asset_class=AssetClass.REAL_ESTATE))
    assert fund.asset_class is AssetClass.REAL_ESTATE
    with pytest.raises(InvalidAssetError):
        resolve_asset(AssetRequest(symbol="PETR4", asset_class=AssetClass.CRYPTO))


def test_stale_price_is_not_used_as_the_reference() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    old = now - timedelta(days=30)
    prices = [PricePoint(observed_at=old, close=10, currency="BRL")]
    evidence = [
        Evidence(
            provider="brapi",
            asset_id="PETR4",
            observed_at=old,
            retrieved_at=now,
            metric="price_close",
            value=10,
            currency="BRL",
        )
    ]
    analysis = analyze_snapshot(
        MarketSnapshot(
            asset=resolve_asset(AssetRequest(symbol="PETR4")),
            prices=prices,
            evidence=evidence,
        ),
        scenarios=resolve_scenarios(None),
        now=now,
        as_of=None,
    )
    assert analysis.status == "partial"
    assert all(metric.name != "reference_price" for metric in analysis.metrics)
    assert analysis.scenarios == []


def test_a_fresh_quote_is_the_reference_when_the_daily_bar_has_another_clock_time() -> None:
    now = datetime(2026, 11, 4, 21, 30, tzinfo=UTC)
    prices = _prices(now, [40, 45, 47.12])
    evidence = [
        Evidence(
            provider="brapi",
            asset_id="PETR4",
            observed_at=now - timedelta(minutes=5),
            retrieved_at=now,
            metric="price_close",
            value=47.12,
            currency="BRL",
            quality_status=QualityStatus.OK,
        )
    ]
    analysis = analyze_snapshot(
        MarketSnapshot(
            asset=resolve_asset(AssetRequest(symbol="PETR4")),
            prices=prices,
            evidence=evidence,
        ),
        scenarios=resolve_scenarios(None),
        now=now,
        as_of=None,
    )
    reference = next(metric for metric in analysis.metrics if metric.name == "reference_price")
    assert reference.value == pytest.approx(47.12)
    assert analysis.scenarios


def test_conflicting_prices_are_not_averaged() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    observed = now - timedelta(hours=1)
    asset = resolve_asset(AssetRequest(symbol="VALE3"))
    evidence = [
        Evidence(
            provider="left",
            asset_id="VALE3",
            observed_at=observed,
            retrieved_at=now,
            metric="price_close",
            value=10,
            currency="BRL",
        ),
        Evidence(
            provider="right",
            asset_id="VALE3",
            observed_at=observed,
            retrieved_at=now,
            metric="price_close",
            value=12,
            currency="BRL",
        ),
    ]
    analysis = analyze_snapshot(
        MarketSnapshot(asset=asset, prices=_prices(now, [10, 11, 12]), evidence=evidence),
        scenarios=resolve_scenarios(None),
        now=now,
        as_of=None,
    )
    assert any(issue.code == "conflicting_sources" for issue in analysis.issues)
    assert all(metric.name != "reference_price" for metric in analysis.metrics)


def test_paper_fii_ignores_vacancy_and_brick_fii_keeps_it() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    observed = now - timedelta(hours=1)
    prices = _prices(now, [10, 12, 9, 11, 11])

    def facts(classification: FundClassification) -> FundFacts:
        return FundFacts(
            classification=classification,
            vacancy_rate=0.2,
            distribution_trailing=1.2,
            distribution_period="trailing_12m",
            evidence=[
                Evidence(
                    provider="cvm",
                    asset_id="FUND11",
                    observed_at=observed,
                    retrieved_at=now,
                    metric="p_vp",
                    value=1.01,
                    unit="ratio",
                    quality_status=QualityStatus.ESTIMATED,
                )
            ],
        )

    paper = analyze_snapshot(
        MarketSnapshot(
            asset=resolve_asset(AssetRequest(symbol="MXRF11", asset_class=AssetClass.REAL_ESTATE)),
            prices=prices,
            evidence=[
                Evidence(
                    provider="brapi",
                    asset_id="MXRF11",
                    observed_at=prices[-1].observed_at,
                    retrieved_at=now,
                    metric="price_close",
                    value=11,
                    currency="BRL",
                )
            ],
            fund=facts(FundClassification.PAPER),
        ),
        scenarios=resolve_scenarios(None),
        now=now,
        as_of=None,
    )
    brick = analyze_snapshot(
        MarketSnapshot(
            asset=resolve_asset(AssetRequest(symbol="HGLG11", asset_class=AssetClass.REAL_ESTATE)),
            prices=prices,
            evidence=[
                Evidence(
                    provider="brapi",
                    asset_id="HGLG11",
                    observed_at=prices[-1].observed_at,
                    retrieved_at=now,
                    metric="price_close",
                    value=11,
                    currency="BRL",
                )
            ],
            fund=facts(FundClassification.BRICK),
        ),
        scenarios=resolve_scenarios(None),
        now=now,
        as_of=None,
    )
    assert all(metric.name != "vacancy_rate" for metric in paper.metrics)
    assert any("paper FII" in item for item in paper.uncertainties)
    assert any(metric.name == "vacancy_rate" and metric.value == 0.2 for metric in brick.metrics)
    assert any(metric.name == "dividend_yield" for metric in brick.metrics)


def test_missing_indicator_is_not_zero() -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    analysis = analyze_snapshot(
        MarketSnapshot(
            asset=resolve_asset(AssetRequest(symbol="ITUB4")),
            prices=_prices(now, [10, 10.5, 11]),
            evidence=[
                Evidence(
                    provider="brapi",
                    asset_id="ITUB4",
                    observed_at=now,
                    retrieved_at=now,
                    metric="price_close",
                    value=11,
                    currency="BRL",
                ),
                Evidence(
                    provider="brapi",
                    asset_id="ITUB4",
                    observed_at=now,
                    retrieved_at=now,
                    metric="trailing_pe",
                    value=None,
                    quality_status=QualityStatus.MISSING,
                ),
            ],
        ),
        scenarios=resolve_scenarios(None),
        now=now,
        as_of=None,
    )
    assert any(issue.code == "missing_value" for issue in analysis.issues)
    assert all(metric.value != 0 for metric in analysis.metrics if metric.name == "trailing_pe")


def test_budget_blocks_the_next_call_and_keeps_estimate_separate() -> None:
    budget = BudgetManager()
    budget.authorize_llm_call(100, 100)
    budget.record_actual_usage(80, 40)
    assert budget.estimated_input_tokens == 100
    assert budget.actual_input_tokens == 80
    tiny = BudgetManager().scaled_for_assets(1)
    tiny.limits.max_provider_calls = 1
    tiny.consume_provider_call()
    with pytest.raises(Exception, match="Provider call budget"):
        tiny.consume_provider_call()


def test_future_prices_are_excluded() -> None:
    from assetmind.domain.analysis.metrics import compound_return, truncate_prices

    now = datetime(2026, 11, 4, tzinfo=UTC)
    prices = [
        PricePoint(observed_at=now - timedelta(days=1), close=10, currency="BRL"),
        PricePoint(observed_at=now + timedelta(days=1), close=50, currency="BRL"),
    ]
    visible = truncate_prices(prices, now)
    metric = compound_return(visible)
    assert len(visible) == 1
    assert metric is None

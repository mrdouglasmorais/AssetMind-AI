"""Turn a normalized snapshot into a specialist result. No model calls."""

from datetime import datetime

from pydantic import BaseModel, Field

from assetmind.domain.analysis.metrics import (
    FieldCoverage,
    MetricResult,
    annualized_volatility,
    buy_and_hold_backtest,
    compound_return,
    dividend_yield,
    field_coverage,
    historical_distribution,
    maximum_drawdown,
    price_shock,
    simple_moving_average,
    truncate_prices,
    windowed_return,
)
from assetmind.domain.assets.identity import AssetClass, ResolvedAsset
from assetmind.domain.evidence.freshness import assess_freshness
from assetmind.domain.evidence.models import (
    Evidence,
    FundClassification,
    FundFacts,
    PricePoint,
    QualityStatus,
)
from assetmind.domain.evidence.validation import (
    EvidenceValidation,
    ValidationIssue,
    reconcile_evidence,
)
from assetmind.domain.scenarios.policy import ResolvedScenario


class ScenarioResult(BaseModel):
    name: str
    price_shock: float
    shocked_price: float | None
    label: str
    disclosure: str


class AssetAnalysis(BaseModel):
    asset: ResolvedAsset
    status: str
    metrics: list[MetricResult] = Field(default_factory=list)
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    coverage: FieldCoverage = Field(default_factory=FieldCoverage)


class MarketSnapshot(BaseModel):
    asset: ResolvedAsset
    prices: list[PricePoint] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    fund: FundFacts | None = None
    macro: list[Evidence] = Field(default_factory=list)


def analyze_snapshot(
    snapshot: MarketSnapshot,
    *,
    scenarios: list[ResolvedScenario],
    now: datetime,
    as_of: datetime | None,
) -> AssetAnalysis:
    prices = truncate_prices(snapshot.prices, as_of)
    prepared = _prepare_evidence(snapshot, now)
    validation = reconcile_evidence(prepared)
    metrics: list[MetricResult] = []
    uncertainties: list[str] = list(snapshot.asset.notes)
    risks = _class_risks(snapshot.asset.asset_class, snapshot.fund)

    current = _current_price(prices, validation, snapshot.asset.asset_class, now)
    if current is None:
        uncertainties.append("No fresh reference price was available, so scenarios were omitted.")
    else:
        metrics.append(current)

    if len(prices) < 2:
        uncertainties.append("Insufficient history for return, volatility, drawdown, and in-sample backtest.")
    else:
        for metric in (
            compound_return(prices),
            maximum_drawdown(prices),
            simple_moving_average(prices, 3),
            buy_and_hold_backtest(prices),
            windowed_return(prices, name="return_3m", horizon_days=92, tolerance_days=7),
            windowed_return(prices, name="return_6m", horizon_days=183, tolerance_days=7),
            windowed_return(prices, name="return_12m", horizon_days=365, tolerance_days=10),
        ):
            if metric is not None:
                metrics.append(metric)
        periods = 365 if snapshot.asset.asset_class is AssetClass.CRYPTO else 252
        volatility = annualized_volatility(prices, periods_per_year=periods)
        if volatility is None:
            uncertainties.append("Volatility needs at least two simple returns.")
        else:
            metrics.append(volatility)
        if len(prices) < 20:
            uncertainties.append("The price window is shorter than 20 observations.")
        metrics.extend(historical_distribution(prices))

    metrics.extend(_fundamental_metrics(snapshot, validation, current))
    scenario_results = _scenarios(current, scenarios) if current is not None else []
    fund = snapshot.fund
    if fund is not None and fund.classification is FundClassification.PAPER and fund.vacancy_rate is not None:
        uncertainties.append("A vacancy figure was present and was not applied because this is a paper FII.")
    if any(item.quality_status is QualityStatus.ESTIMATED for item in validation.evidence):
        uncertainties.append("At least one figure comes from a recorded fixture, not a live filing.")
    if any(item.quality_status is QualityStatus.STALE for item in validation.evidence):
        uncertainties.append("At least one observation is older than the freshness policy.")
    if any(issue.code == "missing_value" for issue in validation.issues):
        uncertainties.append("At least one requested indicator was missing and was left empty.")

    status = "completed"
    if any(issue.severity == "error" for issue in validation.issues) or current is None:
        status = "partial" if metrics else "failed"
    if len(prices) < 2:
        status = "partial" if metrics or prices else "failed"

    brick = fund is not None and fund.classification is FundClassification.BRICK
    return AssetAnalysis(
        asset=snapshot.asset,
        status=status,
        metrics=metrics,
        scenarios=scenario_results,
        evidence=validation.evidence + snapshot.macro,
        uncertainties=_unique(uncertainties),
        risks=risks,
        issues=validation.issues,
        coverage=field_coverage(
            snapshot.asset.asset_class.value,
            metrics,
            include_vacancy=brick,
        ),
    )


def _prepare_evidence(snapshot: MarketSnapshot, now: datetime) -> list[Evidence]:
    family_for_metric = {
        "price_close": "price",
        "market_cap": "fundamental",
        "volume": "fundamental",
        "p_vp": "fundamental",
        "week52_low": "price",
        "week52_high": "price",
        "price_to_earnings": "fundamental",
        "earnings_per_share": "fundamental",
        "dividend_yield": "fundamental",
        "vacancy_rate": "fundamental",
        "distribution_trailing": "distribution",
    }
    prepared: list[Evidence] = []
    for item in snapshot.evidence:
        family = family_for_metric.get(item.metric, "fundamental")
        prepared.append(assess_freshness(item, asset_class=snapshot.asset.asset_class, family=family, now=now))
    return prepared


def _current_price(
    prices: list[PricePoint],
    validation: EvidenceValidation,
    asset_class: AssetClass,
    now: datetime,
) -> MetricResult | None:
    if not prices:
        return None
    fresh: list[Evidence] = []
    for item in validation.evidence:
        if item.metric != "price_close":
            continue
        checked = assess_freshness(item, asset_class=asset_class, family="price", now=now)
        if checked.quality_status is QualityStatus.OK and checked.value is not None:
            fresh.append(checked)
    if len({item.value for item in fresh}) != 1:
        return None
    chosen = fresh[-1]
    return MetricResult(
        name="reference_price",
        value=chosen.value,
        unit=chosen.currency or prices[-1].currency,
        formula="latest fresh close",
        sampling="last observation inside the freshness window",
        assumptions=["The reference price is the latest non-conflicting fresh close."],
        limitations=["A fresh close can still be delayed by the provider plan."],
        interpretation="Reference price for scenarios. Stale and conflicting prices are excluded.",
    )


def _fundamental_metrics(
    snapshot: MarketSnapshot,
    validation: EvidenceValidation,
    current: MetricResult | None,
) -> list[MetricResult]:
    metrics: list[MetricResult] = []
    for name in ("market_cap", "volume"):
        item = _single_ok(validation, name)
        if item is None or item.value is None:
            continue
        metrics.append(
            MetricResult(
                name=name,
                value=item.value,
                unit=item.unit or item.currency or "native",
                formula=f"provider observation of {name}",
                sampling=item.period or "point in time",
                assumptions=["Value is copied from the provider and not recalculated."],
                limitations=["Coverage and delay depend on the provider plan."],
                interpretation=f"Observed {name}.",
            )
        )
    if snapshot.asset.asset_class is AssetClass.EQUITY:
        metrics.extend(_equity_card(validation))

    fund = snapshot.fund
    if fund is None or snapshot.asset.asset_class is not AssetClass.REAL_ESTATE:
        return metrics

    if fund.classification is FundClassification.BRICK and fund.vacancy_rate is not None:
        metrics.append(
            MetricResult(
                name="vacancy_rate",
                value=fund.vacancy_rate,
                unit="fraction",
                formula="reported vacancy for a brick FII",
                sampling="reported period",
                assumptions=["Vacancy is applied only when the fund is classified as brick."],
                limitations=["Vacancy does not describe paper funds or direct property."],
                interpretation="Reported physical vacancy.",
            )
        )
    if fund.distribution_trailing is not None and fund.distribution_period and current is not None and current.value:
        metrics.append(dividend_yield(fund.distribution_trailing, current.value, fund.distribution_period))
    pvp = _single_ok(validation, "p_vp")
    if pvp is not None and pvp.value is not None:
        metrics.append(
            MetricResult(
                name="p_vp",
                value=pvp.value,
                unit="ratio",
                formula="price / book value as reported",
                sampling=pvp.period or "point in time",
                assumptions=["P/VP is used only when the source observation is fresh."],
                limitations=["Accounting book value is not a transaction price for the properties."],
                interpretation="Reported price-to-book ratio.",
            )
        )
    return metrics


def _equity_card(validation: EvidenceValidation) -> list[MetricResult]:
    specs = (
        ("week52_low", "BRL", "52-week low reported by the quote"),
        ("week52_high", "BRL", "52-week high reported by the quote"),
        ("price_to_earnings", "ratio", "trailing price / earnings reported by the provider"),
        ("earnings_per_share", "BRL", "trailing earnings per share reported by the provider"),
        ("p_vp", "ratio", "price / book value reported by the provider"),
        ("dividend_yield", "fraction", "trailing dividend yield reported by the provider"),
    )
    metrics: list[MetricResult] = []
    for name, unit, formula in specs:
        observed = [item for item in validation.evidence if item.metric == name]
        if not observed:
            continue
        fresh = _single_ok(validation, name)
        metrics.append(
            MetricResult(
                name=name,
                value=None if fresh is None else fresh.value,
                unit=unit if fresh is None or fresh.unit is None else fresh.unit,
                formula=formula,
                sampling="provider current observation" if fresh is None else (fresh.period or "current"),
                assumptions=["The figure is copied from the provider and not recomputed from the 3-month series."],
                limitations=[
                    "A missing or stale observation stays empty.",
                    "The 52-week range is not the return window.",
                ],
                interpretation="Reported fundamental or 52-week quote field.",
            )
        )
    return metrics


def _single_ok(validation: EvidenceValidation, metric: str) -> Evidence | None:
    matches = [
        item
        for item in validation.evidence
        if item.metric == metric
        and item.quality_status in {QualityStatus.OK, QualityStatus.ESTIMATED}
        and item.value is not None
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _scenarios(current: MetricResult, scenarios: list[ResolvedScenario]) -> list[ScenarioResult]:
    if current.value is None:
        return []
    return [
        ScenarioResult(
            name=item.name,
            price_shock=item.price_shock,
            shocked_price=price_shock(current.value, item.price_shock),
            label=item.label,
            disclosure=item.disclosure,
        )
        for item in scenarios
    ]


def _class_risks(asset_class: AssetClass, fund: FundFacts | None) -> list[str]:
    if asset_class is AssetClass.EQUITY:
        return ["Equity prices can move with the business, the market, and liquidity."]
    if asset_class is AssetClass.CRYPTO:
        return ["Crypto prices can gap, and reported volume is not proof of executable liquidity."]
    risks = ["FII quotas can diverge from reported book value and from property-level outcomes."]
    if fund and fund.classification is FundClassification.PAPER:
        risks.append("Paper FIIs add credit and indexer risk; vacancy is not an applicable metric.")
    if fund and fund.classification is FundClassification.UNKNOWN:
        risks.append("Fund classification is unknown, so vacancy was not applied.")
    return risks


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered

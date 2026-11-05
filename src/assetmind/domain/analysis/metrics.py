"""Deterministic market calculations.

Each function documents its formula in the returned metric. Price series must
already be truncated at the analysis clock so later observations cannot leak in.
"""

import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from assetmind.domain.evidence.models import PricePoint


class FieldCoverage(BaseModel):
    """Share of requested card fields that arrived with a number.

    The score is present / requested. It is not a buy or sell grade.
    """

    requested: list[str] = Field(default_factory=list)
    present: list[str] = Field(default_factory=list)
    refused: list[str] = Field(default_factory=list)
    score: float = 0.0


_EQUITY_FIELDS = (
    "reference_price",
    "compound_return",
    "return_3m",
    "return_6m",
    "return_12m",
    "annualized_volatility",
    "maximum_drawdown",
    "week52_low",
    "week52_high",
    "price_to_earnings",
    "earnings_per_share",
    "p_vp",
    "dividend_yield",
)
_FUND_FIELDS = (
    "reference_price",
    "compound_return",
    "return_3m",
    "return_6m",
    "return_12m",
    "annualized_volatility",
    "maximum_drawdown",
    "p_vp",
    "dividend_yield",
)
_CRYPTO_FIELDS = (
    "reference_price",
    "compound_return",
    "return_3m",
    "return_6m",
    "return_12m",
    "annualized_volatility",
    "maximum_drawdown",
)


class MetricResult(BaseModel):
    name: str
    value: float | None
    unit: str
    formula: str
    sampling: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    interpretation: str


def field_coverage(
    asset_class: str,
    metrics: list[MetricResult],
    *,
    include_vacancy: bool,
) -> FieldCoverage:
    """requested are the card fields. present have a number. refused do not."""

    fields = _EQUITY_FIELDS
    if asset_class == "crypto":
        fields = _CRYPTO_FIELDS
    elif asset_class == "real_estate":
        fields = _FUND_FIELDS
    requested: list[str] = list(fields)
    if include_vacancy:
        requested.append("vacancy_rate")
    by_name = {metric.name: metric for metric in metrics}
    present = [name for name in requested if (item := by_name.get(name)) is not None and item.value is not None]
    refused = [name for name in requested if name not in present]
    score = len(present) / len(requested) if requested else 0.0
    return FieldCoverage(requested=requested, present=present, refused=refused, score=score)


def truncate_prices(prices: list[PricePoint], as_of: datetime | None) -> list[PricePoint]:
    ordered = sorted(prices, key=lambda point: point.observed_at)
    if as_of is None:
        return ordered
    return [point for point in ordered if point.observed_at <= as_of]


def price_frame(prices: list[PricePoint]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observed_at": [point.observed_at for point in prices],
            "close": [point.close for point in prices],
        }
    )


def observation_window(prices: list[PricePoint]) -> str:
    start = prices[0].observed_at.date().isoformat()
    end = prices[-1].observed_at.date().isoformat()
    return f"{start} to {end}, {len(prices)} observations"


def simple_returns(prices: list[PricePoint]) -> list[float]:
    """r_t = close_t / close_{t-1} - 1."""

    frame = price_frame(prices)
    closes = frame["close"].tolist()
    return [closes[index] / closes[index - 1] - 1 for index in range(1, len(closes))]


def compound_return(prices: list[PricePoint]) -> MetricResult | None:
    """Total return = close_end / close_start - 1."""

    if len(prices) < 2:
        return None
    value = prices[-1].close / prices[0].close - 1
    return MetricResult(
        name="compound_return",
        value=value,
        unit="fraction",
        formula="close_end / close_start - 1",
        sampling=observation_window(prices),
        assumptions=["Prices are positive and ordered by observation time."],
        limitations=["Ignores cash flows unless the series is already adjusted."],
        interpretation="Buy-and-hold return over the supplied window.",
    )


def annualized_volatility(
    prices: list[PricePoint],
    *,
    periods_per_year: int,
) -> MetricResult | None:
    """Sample standard deviation of simple returns, scaled by sqrt(periods_per_year)."""

    returns = simple_returns(prices)
    if len(returns) < 2:
        return None
    deviation = float(np.std(np.array(returns, dtype=float), ddof=1))
    value = deviation * math.sqrt(periods_per_year)
    return MetricResult(
        name="annualized_volatility",
        value=value,
        unit="fraction",
        formula="stdev(simple_returns, ddof=1) * sqrt(periods_per_year)",
        sampling=f"{observation_window(prices)}; {len(returns)} simple returns; {periods_per_year} periods/year",
        assumptions=["Returns are the simple close-to-close series in this window."],
        limitations=[
            "Not a forecast.",
            "The annualization factor is a convention, not evidence of independent periods.",
        ],
        interpretation="Historical dispersion of simple returns, annualized by convention.",
    )


def maximum_drawdown(prices: list[PricePoint]) -> MetricResult | None:
    """min_t(close_t / running_peak_t - 1). The result is zero or negative."""

    if len(prices) < 2:
        return None
    peak = prices[0].close
    worst = 0.0
    for point in prices:
        peak = max(peak, point.close)
        worst = min(worst, point.close / peak - 1)
    return MetricResult(
        name="maximum_drawdown",
        value=worst,
        unit="fraction",
        formula="min(close_t / running_peak_t - 1)",
        sampling=observation_window(prices),
        assumptions=["The running peak uses only prices inside the supplied window."],
        limitations=["A short window can hide earlier drawdowns."],
        interpretation="Largest peak-to-trough decline inside the window.",
    )


def simple_moving_average(prices: list[PricePoint], window: int) -> MetricResult | None:
    if window < 2 or len(prices) < window:
        return None
    closes = price_frame(prices)["close"].tolist()
    value = sum(closes[-window:]) / window
    return MetricResult(
        name=f"sma_{window}",
        value=value,
        unit=prices[-1].currency,
        formula=f"mean(close over the last {window} observations)",
        sampling=f"{observation_window(prices)}; window={window}",
        assumptions=["Equal weight for each observation in the window."],
        limitations=["A moving average is a smoother, not a trading signal."],
        interpretation="Average close of the latest window.",
    )


def historical_distribution(prices: list[PricePoint]) -> list[MetricResult]:
    returns = simple_returns(prices)
    if len(returns) < 2:
        return []
    array = np.array(returns, dtype=float)
    percentiles = {
        "return_p05": float(np.percentile(array, 5)),
        "return_p50": float(np.percentile(array, 50)),
        "return_p95": float(np.percentile(array, 95)),
    }
    return [
        MetricResult(
            name=name,
            value=value,
            unit="fraction",
            formula=f"empirical percentile of simple returns ({name[-3:]})",
            sampling=f"{observation_window(prices)}; {len(returns)} simple returns",
            assumptions=["Each simple return in the window is one observation."],
            limitations=["An empirical percentile is not a calibrated probability of future returns."],
            interpretation="Historical distribution summary, not a forecast.",
        )
        for name, value in percentiles.items()
    ]


def dividend_yield(distribution: float, price: float, period: str) -> MetricResult:
    """trailing distribution / reference price, for the stated period only."""

    return MetricResult(
        name="dividend_yield",
        value=distribution / price,
        unit="fraction",
        formula="trailing_distribution / reference_price",
        sampling=period,
        assumptions=["The distribution and the price cover the same stated period."],
        limitations=["Yield changes when the price changes. It is not a forward dividend promise."],
        interpretation=f"Trailing yield for {period}.",
    )


def price_shock(price: float, shock: float) -> float:
    """shocked_price = reference_price * (1 + shock)."""

    return price * (1 + shock)


def windowed_return(
    prices: list[PricePoint],
    *,
    name: str,
    horizon_days: int,
    tolerance_days: int,
) -> MetricResult:
    """Realized return = close_end / close_horizon_start - 1.

    Horizon start is the first close at or after (end - horizon_days).
    The value stays empty when that span is shorter than horizon_days - tolerance_days.
    Units are a fraction of the starting close. This is not a forecast.
    """

    limitations = [
        "Empty when the received series does not reach the horizon.",
        "Ignores cash flows unless the series is already adjusted.",
    ]
    if len(prices) < 2:
        return _empty_window(name, horizon_days, limitations)
    end = prices[-1].observed_at
    window = [point for point in prices if point.observed_at >= end - timedelta(days=horizon_days)]
    if len(window) < 2:
        return _empty_window(name, horizon_days, limitations)
    span_days = (window[-1].observed_at - window[0].observed_at).days
    if span_days < horizon_days - tolerance_days or window[0].close <= 0:
        return _empty_window(name, horizon_days, limitations)
    value = window[-1].close / window[0].close - 1
    return MetricResult(
        name=name,
        value=value,
        unit="fraction",
        formula="close_end / first_close_inside_horizon - 1",
        sampling=f"{observation_window(window)}; horizon {horizon_days} calendar days",
        assumptions=["Prices are positive and already truncated at the analysis clock."],
        limitations=["The horizon is calendar days, not a count of trading sessions."],
        interpretation=f"Realized buy-and-hold return over about {horizon_days} calendar days.",
    )


def _empty_window(name: str, horizon_days: int, limitations: list[str]) -> MetricResult:
    return MetricResult(
        name=name,
        value=None,
        unit="fraction",
        formula="close_end / first_close_inside_horizon - 1",
        sampling=f"horizon {horizon_days} calendar days",
        limitations=limitations,
        interpretation="No close covers this horizon in the received series.",
    )


def buy_and_hold_backtest(prices: list[PricePoint]) -> MetricResult | None:
    """Same formula as compound return, named as an in-sample backtest of buy-and-hold.

    The caller must pass a series that ends at the analysis clock.
    """

    metric = compound_return(prices)
    if metric is None:
        return None
    return metric.model_copy(
        update={
            "name": "buy_and_hold_backtest",
            "interpretation": "In-sample buy-and-hold result. It does not use observations after as_of.",
            "limitations": [
                "In-sample description of the supplied window.",
                "No transaction costs, taxes, or slippage.",
            ],
        }
    )

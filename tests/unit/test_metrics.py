import math
from datetime import UTC, datetime, timedelta

import pytest

from assetmind.domain.analysis.metrics import (
    annualized_volatility,
    buy_and_hold_backtest,
    compound_return,
    field_coverage,
    maximum_drawdown,
    price_shock,
    simple_moving_average,
    simple_returns,
    windowed_return,
)
from assetmind.domain.evidence.models import PricePoint


def _prices(closes: list[float]) -> list[PricePoint]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        PricePoint(observed_at=start + timedelta(days=index), close=close, currency="BRL")
        for index, close in enumerate(closes)
    ]


def test_known_return_drawdown_and_volatility() -> None:
    prices = _prices([10, 12, 9, 11, 11])
    assert simple_returns(prices)[0] == pytest.approx(0.2)
    compound = compound_return(prices)
    drawdown = maximum_drawdown(prices)
    assert compound is not None and compound.value == pytest.approx(0.1)
    assert drawdown is not None and drawdown.value == pytest.approx(-0.25)
    volatility = annualized_volatility(_prices([10, 11, 9.9]), periods_per_year=252)
    expected = math.sqrt((0.1**2 + (-0.1) ** 2) / 1) * math.sqrt(252)
    assert volatility is not None
    assert abs((volatility.value or 0) - expected) < 1e-9
    assert simple_moving_average(prices, 2) is not None
    assert price_shock(10, -0.2) == 8
    backtest = buy_and_hold_backtest(prices)
    assert backtest is not None and backtest.name == "buy_and_hold_backtest"


def test_three_month_return_uses_the_horizon_and_refuses_a_short_span() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    prices = [
        PricePoint(observed_at=start + timedelta(days=index), close=10 + index, currency="BRL") for index in range(100)
    ]
    three = windowed_return(prices, name="return_3m", horizon_days=92, tolerance_days=7)
    six = windowed_return(prices, name="return_6m", horizon_days=183, tolerance_days=7)
    assert three.value == pytest.approx(109 / 17 - 1)
    assert six.value is None
    coverage = field_coverage("equity", [three, six], include_vacancy=False)
    assert coverage.present == ["return_3m"]
    assert "return_6m" in coverage.refused
    assert coverage.score == pytest.approx(1 / 13)


def test_short_sample_has_no_volatility() -> None:
    assert annualized_volatility(_prices([10, 11]), periods_per_year=252) is None

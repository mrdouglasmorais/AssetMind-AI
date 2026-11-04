"""Scenario assumptions. These are inputs, not calibrated forecasts."""

from typing import Literal

from pydantic import BaseModel, Field

ScenarioName = Literal["bear", "base", "bull"]
ScenarioLabel = Literal["illustrative_assumption", "user_assumption"]

# Documented engineering placeholders. They are not expected returns.
ILLUSTRATIVE_SHOCKS: dict[ScenarioName, float] = {
    "bear": -0.15,
    "base": 0.0,
    "bull": 0.15,
}


class ScenarioAssumptions(BaseModel):
    bear: float = Field(ge=-0.95, le=3)
    base: float = Field(ge=-0.95, le=3)
    bull: float = Field(ge=-0.95, le=3)


class ResolvedScenario(BaseModel):
    name: ScenarioName
    price_shock: float
    label: ScenarioLabel
    disclosure: str


def resolve_scenarios(requested: ScenarioAssumptions | None) -> list[ResolvedScenario]:
    if requested is None:
        return [
            ResolvedScenario(
                name=name,
                price_shock=shock,
                label="illustrative_assumption",
                disclosure=(
                    "Illustrative price shock selected by the MVP policy. "
                    "It is not a forecast and has no calibrated probability."
                ),
            )
            for name, shock in ILLUSTRATIVE_SHOCKS.items()
        ]
    return [
        ResolvedScenario(
            name=name,
            price_shock=getattr(requested, name),
            label="user_assumption",
            disclosure="Price shock supplied in the request. It is an assumption, not a forecast.",
        )
        for name in ("bear", "base", "bull")
    ]

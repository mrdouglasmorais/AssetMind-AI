"""HTTP schemas for the versioned analysis API."""

from datetime import datetime

from pydantic import BaseModel, Field

from assetmind.domain.assets.identity import AssetClass, Market


class AssetInput(BaseModel):
    symbol: str = Field(min_length=2, max_length=64)
    asset_class: AssetClass | None = None
    market: Market | None = None


class ScenarioInput(BaseModel):
    bear: float = Field(ge=-0.95, le=3)
    base: float = Field(ge=-0.95, le=3)
    bull: float = Field(ge=-0.95, le=3)


class AnalysisCreate(BaseModel):
    assets: list[AssetInput] = Field(min_length=1, max_length=5)
    scenarios: ScenarioInput | None = None
    as_of: datetime | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str


class AnalysisAccepted(BaseModel):
    analysis_id: str
    correlation_id: str
    status: str
    report: dict[str, object] | None
    error_code: str | None = None

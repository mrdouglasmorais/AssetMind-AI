"""Normalized evidence. Observation time and retrieval time stay distinct."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class QualityStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    STALE = "stale"
    CONFLICTING = "conflicting"
    ESTIMATED = "estimated"
    NOT_APPLICABLE = "not_applicable"


class Evidence(BaseModel):
    provider: str
    source_url: str | None = None
    asset_id: str
    observed_at: datetime | None = None
    retrieved_at: datetime
    metric: str
    value: float | None = None
    unit: str | None = None
    currency: str | None = None
    period: str | None = None
    quality_status: QualityStatus = QualityStatus.OK
    text_value: str | None = None


class PricePoint(BaseModel):
    observed_at: datetime
    close: float = Field(gt=0)
    currency: str


class FundClassification(StrEnum):
    BRICK = "brick"
    PAPER = "paper"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class FundFacts(BaseModel):
    """Official or recorded FII facts. Vacancy applies only to brick funds."""

    classification: FundClassification = FundClassification.UNKNOWN
    vacancy_rate: float | None = None
    p_vp: float | None = None
    distribution_trailing: float | None = None
    distribution_period: str | None = None
    exposure_notes: list[str] = Field(default_factory=list)
    credit_risk: str | None = None
    indexer: str | None = None
    concentration: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

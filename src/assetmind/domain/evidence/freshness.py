"""Freshness policy by indicator family.

A stale observation is retained as evidence and is not reused as a current price.
"""

from datetime import datetime, timedelta

from assetmind.domain.assets.identity import AssetClass
from assetmind.domain.evidence.models import Evidence, QualityStatus

_MAX_AGE: dict[tuple[AssetClass, str], timedelta] = {
    (AssetClass.EQUITY, "price"): timedelta(days=3),
    (AssetClass.REAL_ESTATE, "price"): timedelta(days=3),
    (AssetClass.CRYPTO, "price"): timedelta(minutes=15),
    (AssetClass.EQUITY, "fundamental"): timedelta(days=120),
    (AssetClass.REAL_ESTATE, "fundamental"): timedelta(days=120),
    (AssetClass.CRYPTO, "fundamental"): timedelta(days=2),
    (AssetClass.REAL_ESTATE, "distribution"): timedelta(days=45),
}


def max_age(asset_class: AssetClass, family: str) -> timedelta:
    try:
        return _MAX_AGE[(asset_class, family)]
    except KeyError as exc:
        raise KeyError(f"No freshness policy for {asset_class}/{family}.") from exc


def assess_freshness(
    evidence: Evidence,
    *,
    asset_class: AssetClass,
    family: str,
    now: datetime,
) -> Evidence:
    if evidence.value is None and evidence.text_value is None:
        return evidence.model_copy(update={"quality_status": QualityStatus.MISSING})
    if evidence.observed_at is None:
        return evidence.model_copy(update={"quality_status": QualityStatus.MISSING})
    if now - evidence.observed_at > max_age(asset_class, family):
        return evidence.model_copy(update={"quality_status": QualityStatus.STALE})
    return evidence

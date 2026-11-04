"""CVM fund-facts adapter.

Live parsing of the monthly FII informe (a ZIP of official files) is not part
of this MVP. Fixture mode returns recorded examples and labels them as fixtures.
Live mode returns an unknown classification and missing fundamentals instead of
presenting fixture numbers as official data.
"""

from datetime import datetime

from assetmind.domain.assets.identity import ResolvedAsset
from assetmind.domain.evidence.models import Evidence, FundClassification, FundFacts, QualityStatus


class CvmProvider:
    name = "cvm"

    def __init__(self, *, use_fixtures: bool = False) -> None:
        self.use_fixtures = use_fixtures

    async def fund_facts(self, asset: ResolvedAsset, *, now: datetime) -> FundFacts:
        if not self.use_fixtures:
            return FundFacts(
                classification=FundClassification.UNKNOWN,
                evidence=[
                    Evidence(
                        provider=self.name,
                        source_url="https://dados.cvm.gov.br/",
                        asset_id=asset.symbol,
                        observed_at=None,
                        retrieved_at=now,
                        metric="fund_classification",
                        value=None,
                        text_value="live_cvm_informe_not_parsed",
                        quality_status=QualityStatus.MISSING,
                    )
                ],
            )
        recorded = _FIXTURES.get(asset.symbol)
        if recorded is None:
            return FundFacts(classification=FundClassification.UNKNOWN)
        return recorded.model_copy(deep=True)


def _facts(
    symbol: str,
    classification: FundClassification,
    *,
    vacancy: float | None,
    p_vp: float | None,
    distribution: float | None,
    credit_risk: str | None,
    indexer: str | None,
    concentration: list[str],
) -> FundFacts:
    observed = datetime.fromisoformat("2026-09-30T00:00:00+00:00")
    retrieved = datetime.fromisoformat("2026-10-01T00:00:00+00:00")
    evidence = [
        Evidence(
            provider="cvm",
            source_url="fixture://cvm/fii",
            asset_id=symbol,
            observed_at=observed,
            retrieved_at=retrieved,
            metric="p_vp",
            value=p_vp,
            unit="ratio",
            period="monthly_report",
            quality_status=QualityStatus.ESTIMATED if p_vp is not None else QualityStatus.MISSING,
            text_value="recorded_fixture",
        )
    ]
    return FundFacts(
        classification=classification,
        vacancy_rate=vacancy,
        p_vp=p_vp,
        distribution_trailing=distribution,
        distribution_period="trailing_12m",
        exposure_notes=["Recorded fixture, not a live CVM filing."],
        credit_risk=credit_risk,
        indexer=indexer,
        concentration=concentration,
        evidence=evidence,
    )


_FIXTURES = {
    "HGLG11": _facts(
        "HGLG11",
        FundClassification.BRICK,
        vacancy=0.04,
        p_vp=1.02,
        distribution=9.6,
        credit_risk=None,
        indexer=None,
        concentration=["logistics properties"],
    ),
    "MXRF11": _facts(
        "MXRF11",
        FundClassification.PAPER,
        vacancy=0.2,
        p_vp=1.01,
        distribution=12.0,
        credit_risk="Receivables credit risk is material for a paper FII.",
        indexer="CDI",
        concentration=["CRI portfolio"],
    ),
}

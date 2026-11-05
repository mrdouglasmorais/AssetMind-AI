"""Brazilian Portuguese report assembled only from structured results.

The composer copies symbols, metric values, and fixed disclosures. It does not
copy provider prose, so instruction-like source text cannot enter the narrative.
"""

from pydantic import BaseModel, Field

from assetmind.domain.analysis.engine import AssetAnalysis
from assetmind.domain.analysis.metrics import MetricResult

DISCLAIMER = (
    "Material educacional. Nao e recomendacao de investimento, oferta ou promessa de retorno. "
    "Cenarios bear, base e bull sao premissas ilustrativas ou informadas na solicitacao, "
    "nao previsoes com probabilidade calibrada."
)


class ReportDocument(BaseModel):
    language: str = "pt-BR"
    status: str
    composer: str
    summary: str
    assets: list[dict[str, object]] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    validation_issues: list[dict[str, str]] = Field(default_factory=list)
    orchestration: list[str] = Field(default_factory=list)
    usage: dict[str, object] = Field(default_factory=dict)


_PRICE_SERIES_METRICS = {
    "reference_price",
    "compound_return",
    "annualized_volatility",
    "maximum_drawdown",
    "return_p05",
    "return_p50",
    "return_p95",
    "buy_and_hold_backtest",
    "return_3m",
    "return_6m",
    "return_12m",
    "dividend_yield",
    "volume",
    "market_cap",
}


def compose_report(
    analyses: list[AssetAnalysis],
    *,
    status: str,
    composer: str,
    orchestration: list[str] | None = None,
) -> ReportDocument:
    sections: list[dict[str, object]] = []
    issues: list[dict[str, str]] = []
    for analysis in analyses:
        synthetic = _synthetic_price(analysis)
        metrics = _publishable_metrics(analysis, synthetic=synthetic)
        scenarios = _publishable_scenarios(analysis, synthetic=synthetic)
        lines = [_asset_lines(analysis, metrics=metrics, scenarios=scenarios, synthetic=synthetic)]
        sections.append(
            {
                "symbol": analysis.asset.symbol,
                "asset_class": analysis.asset.asset_class.value,
                "status": analysis.status,
                "narrative": "\n".join(lines),
                "metrics": [metric.model_dump() for metric in metrics],
                "scenarios": scenarios,
                "uncertainties": analysis.uncertainties,
                "risks": analysis.risks,
                "sources": _sources(analysis),
                "coverage": analysis.coverage.model_dump(),
            }
        )
        for issue in analysis.issues:
            issues.append({"symbol": analysis.asset.symbol, "code": issue.code, "message": issue.message})
    summary = _summary(analyses, status)
    return ReportDocument(
        status=status,
        composer=composer,
        summary=summary,
        assets=sections,
        validation_issues=issues,
        orchestration=orchestration if orchestration is not None else _orchestration(analyses),
    )


def _synthetic_price(analysis: AssetAnalysis) -> bool:
    return any(item.provider == "fixture" and item.metric == "price_close" for item in analysis.evidence)


def _from_price_series(name: str) -> bool:
    return name in _PRICE_SERIES_METRICS or name.startswith("sma_")


def _publishable_metrics(analysis: AssetAnalysis, *, synthetic: bool) -> list[MetricResult]:
    if not synthetic:
        return list(analysis.metrics)
    return [metric for metric in analysis.metrics if not _from_price_series(metric.name)]


def _publishable_scenarios(analysis: AssetAnalysis, *, synthetic: bool) -> list[dict[str, object]]:
    published: list[dict[str, object]] = []
    for scenario in analysis.scenarios:
        dumped = scenario.model_dump()
        if synthetic:
            dumped["shocked_price"] = None
        published.append(dumped)
    return published


def _asset_lines(
    analysis: AssetAnalysis,
    *,
    metrics: list[MetricResult],
    scenarios: list[dict[str, object]],
    synthetic: bool,
) -> str:
    rows = [f"Ativo {analysis.asset.symbol} ({analysis.asset.asset_class.value}), status {analysis.status}."]
    rows.append(_coverage_line(analysis))
    if synthetic:
        rows.append(
            "Cotacao de mercado indisponivel. A serie local e sintetica de teste e nao e preco, volume ou retorno."
        )
    elif not metrics:
        rows.append("Nenhum indicador numerico pode ser apresentado com a evidencia disponivel.")
    for metric in metrics:
        if metric.value is None:
            rows.append(f"{metric.name}: indisponivel.")
        else:
            rows.append(f"{metric.name}: {_format_number(metric.value)} {metric.unit}. Amostra: {metric.sampling}.")
    if synthetic:
        rows.append("Cenarios de preco omitidos: nao ha cotacao de mercado para aplicar o choque.")
    for scenario in [] if synthetic else scenarios:
        shocked = scenario.get("shocked_price")
        price = "indisponivel" if not isinstance(shocked, (int, float)) else _format_number(float(shocked))
        shock = scenario.get("price_shock")
        shock_text = "indisponivel" if not isinstance(shock, (int, float)) else _format_number(float(shock))
        rows.append(
            f"Cenario {scenario.get('name')} ({scenario.get('label')}): choque {shock_text}, "
            f"preco ilustrativo {price}. {scenario.get('disclosure')}"
        )
    if analysis.asset.asset_class.value == "equity":
        headlines = [
            item
            for item in analysis.evidence
            if item.metric == "headline" and item.text_value and item.quality_status.value == "ok"
        ][:3]
        if headlines:
            rows.append("Manchetes:")
            for item in headlines:
                when = item.observed_at.date().isoformat() if item.observed_at else "sem data"
                rows.append(f"- {item.text_value} | {item.provider} | {when} | {item.source_url}")
        else:
            rows.append(
                "Manchetes: nao incluidas neste relatorio. "
                "A consulta de noticias devolve ate 3 titulos da fonte Google News. "
                "O texto da materia nao e copiado."
            )
    for uncertainty in analysis.uncertainties:
        rows.append(f"Incerteza: {uncertainty}")
    for risk in analysis.risks:
        rows.append(f"Risco: {risk}")
    sources = _sources(analysis)
    rows.append("Fontes: " + (", ".join(sources) if sources else "nenhuma fonte registrada."))
    return "\n".join(rows)


def _coverage_line(analysis: AssetAnalysis) -> str:
    coverage = analysis.coverage
    missing = ", ".join(coverage.refused) if coverage.refused else "nenhum"
    return (
        f"Cobertura da ficha: {_format_number(coverage.score)} "
        f"({len(coverage.present)} de {len(coverage.requested)}). "
        f"Ausentes: {missing}. Nao e nota de compra."
    )


def _sources(analysis: AssetAnalysis) -> list[str]:
    return sorted({item.provider for item in analysis.evidence if item.provider})


def _orchestration(analyses: list[AssetAnalysis]) -> list[str]:
    grouped: dict[str, list[str]] = {}
    for analysis in analyses:
        grouped.setdefault(analysis.asset.asset_class.value, []).append(analysis.asset.symbol)
    return [f"{name}: {', '.join(symbols)}" for name, symbols in sorted(grouped.items())]


def _summary(analyses: list[AssetAnalysis], status: str) -> str:
    symbols = ", ".join(item.asset.symbol for item in analyses) or "nenhum ativo"
    if any(_synthetic_price(item) for item in analyses):
        return (
            f"Analise {status} para {symbols}. "
            "Nenhum preco de mercado foi publicado porque a unica serie disponivel e sintetica de teste."
        )
    return (
        f"Analise {status} para {symbols}. Os numeros abaixo repetem os calculos deterministicos e a fonte registrada."
    )


def _format_number(value: float) -> str:
    return f"{value:.4f}"


def parse_structured_narrative(payload: object) -> str:
    """Accept only a mapping with a narrative string. Anything else is invalid."""

    from assetmind.domain.errors import StructuredOutputError

    if not isinstance(payload, dict) or not isinstance(payload.get("narrative"), str):
        raise StructuredOutputError("Structured narrative did not match the required schema.")
    narrative = payload["narrative"].strip()
    if not narrative:
        raise StructuredOutputError("Structured narrative was empty.")
    return narrative

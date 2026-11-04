"""Brazilian Portuguese report assembled only from structured results.

The composer copies symbols, metric values, and fixed disclosures. It does not
copy provider prose, so instruction-like source text cannot enter the narrative.
"""

from pydantic import BaseModel, Field

from assetmind.domain.analysis.engine import AssetAnalysis

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


def compose_report(analyses: list[AssetAnalysis], *, status: str, composer: str) -> ReportDocument:
    sections: list[dict[str, object]] = []
    issues: list[dict[str, str]] = []
    for analysis in analyses:
        lines = [_asset_lines(analysis)]
        sections.append(
            {
                "symbol": analysis.asset.symbol,
                "asset_class": analysis.asset.asset_class.value,
                "status": analysis.status,
                "narrative": "\n".join(lines),
                "metrics": [metric.model_dump() for metric in analysis.metrics],
                "scenarios": [scenario.model_dump() for scenario in analysis.scenarios],
                "uncertainties": analysis.uncertainties,
                "risks": analysis.risks,
                "sources": _sources(analysis),
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
    )


def _asset_lines(analysis: AssetAnalysis) -> str:
    rows = [f"Ativo {analysis.asset.symbol} ({analysis.asset.asset_class.value}), status {analysis.status}."]
    if not analysis.metrics:
        rows.append("Nenhum indicador numerico pode ser apresentado com a evidencia disponivel.")
    for metric in analysis.metrics:
        if metric.value is None:
            rows.append(f"{metric.name}: indisponivel.")
        else:
            rows.append(f"{metric.name}: {_format_number(metric.value)} {metric.unit}.")
    for scenario in analysis.scenarios:
        price = "indisponivel" if scenario.shocked_price is None else _format_number(scenario.shocked_price)
        rows.append(
            f"Cenario {scenario.name} ({scenario.label}): choque {_format_number(scenario.price_shock)}, "
            f"preco ilustrativo {price}. {scenario.disclosure}"
        )
    for uncertainty in analysis.uncertainties:
        rows.append(f"Incerteza: {uncertainty}")
    for risk in analysis.risks:
        rows.append(f"Risco: {risk}")
    sources = _sources(analysis)
    rows.append("Fontes: " + (", ".join(sources) if sources else "nenhuma fonte registrada."))
    return "\n".join(rows)


def _sources(analysis: AssetAnalysis) -> list[str]:
    return sorted({item.provider for item in analysis.evidence if item.provider})


def _summary(analyses: list[AssetAnalysis], status: str) -> str:
    symbols = ", ".join(item.asset.symbol for item in analyses) or "nenhum ativo"
    return f"Analise {status} para {symbols}. Os numeros abaixo repetem os calculos deterministicos."


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

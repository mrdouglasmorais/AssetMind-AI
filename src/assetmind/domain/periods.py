"""Evaluation windows. These are provider limits, not forecasts."""

import re

from assetmind.domain.assets.identity import AssetClass, AssetRequest

_COMPLETE = re.compile(r"completa|diversas|tudo sobre", re.IGNORECASE)
_CHOSEN = re.compile(r"cotacao|retorno|multiplo|manchete|notici|cenario|faixa|52", re.IGNORECASE)
_NEWS = re.compile(r"notici", re.IGNORECASE)
_PROJECTION = re.compile(r"proje|valoriza|cenario", re.IGNORECASE)
_HORIZON = re.compile(r"\b(\d+\s*(mes|meses|ano|anos)|curto|medio|longo)\b", re.IGNORECASE)
_LONG_RETURN = re.compile(r"\b(5|cinco)\s+anos\b|52\s*semanas", re.IGNORECASE)
_RETURN_WORD = re.compile(r"retorno|desvaloriz", re.IGNORECASE)

PERIODS: dict[AssetClass, list[str]] = {
    AssetClass.EQUITY: [
        "Preco de referencia: fechamento com no maximo 3 dias.",
        "Retorno, volatilidade e drawdown: cerca de 3 meses de pregoes diarios.",
        "Faixa de 52 semanas: campo da cotacao, separado da janela de retorno.",
        "P/L, P/VP, LPA e dividend yield: estatistica current, com o trimestre informado pelo provedor.",
        "Manchetes: ate 3, dos ultimos 7 dias, so titulo, fonte e data.",
    ],
    AssetClass.REAL_ESTATE: [
        "Preco de referencia: fechamento com no maximo 3 dias.",
        "Retorno, volatilidade e drawdown: cerca de 3 meses de pregoes diarios.",
        "Distribuicao do fundo: observacao com no maximo 45 dias.",
        "Vacancia: so para fundo de tijolo.",
    ],
    AssetClass.CRYPTO: [
        "Preco de referencia: observacao com no maximo 15 minutos.",
        "Retorno e volatilidade: janela recebida do provedor, anualizada com 365 periodos.",
        "Manchetes: ate 3, dos ultimos 7 dias, so titulo, fonte e data.",
    ],
}


def periods_for(asset_class: AssetClass) -> list[str]:
    return list(PERIODS[asset_class])


def continues_session(text: str) -> bool:
    return bool(_HORIZON.search(text) or re.search(r"os dois|3 meses|faixa", text, re.IGNORECASE))


def intake_question(text: str, assets: list[AssetRequest]) -> str | None:
    """Question that must be answered before this turn runs."""

    for asset in assets:
        if asset.symbol.endswith("11") and asset.asset_class is None:
            return f"{asset.symbol} termina em 11. Devo tratar como acao ou como fundo imobiliario?"
    if _COMPLETE.search(text) and not _CHOSEN.search(text):
        return (
            "Para agregar esta execucao, escolha o que entra agora: "
            "cotacao e retorno de cerca de 3 meses; multiplos atuais; "
            "faixa de 52 semanas; ate 3 manchetes; cenario ilustrativo de preco. "
            "Pode marcar mais de um."
        )
    if _PROJECTION.search(text) and not _HORIZON.search(text):
        return (
            "O cenario ilustrativo aplica um choque de -15%, 0% ou +15% no preco de referencia. "
            "Nao e uma projecao de valorizacao. Qual horizonte devo registrar no rotulo: "
            "curto, medio, longo, ou um numero de meses?"
        )
    if _LONG_RETURN.search(text) and _RETURN_WORD.search(text):
        return (
            "O retorno calculado usa cerca de 3 meses de pregoes. "
            "A faixa de 52 semanas e um campo da cotacao e nao e o retorno desse intervalo. "
            "Sigo com o retorno de 3 meses, com a faixa de 52 semanas, ou com os dois?"
        )
    if _NEWS.search(text) and not assets:
        return "De qual ativo devo buscar as manchetes?"
    return None

"""Evaluation windows. These are provider limits, not forecasts."""

import json
import re
from dataclasses import dataclass

from assetmind.domain.assets.catalog import CATALOG
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


_ANSWERED_WINDOW = re.compile(r"os dois|3 meses|faixa", re.IGNORECASE)
_CHOICE_FOLLOW = re.compile(r"cotacao|multiplo|noticia|cenario|faixa|3 meses|os dois", re.IGNORECASE)


@dataclass(frozen=True)
class ChoiceOption:
    label: str
    value: str


@dataclass(frozen=True)
class ChoicePrompt:
    mode: str
    prompt: str
    options: tuple[ChoiceOption, ...]


def continues_session(text: str) -> bool:
    return bool(_HORIZON.search(text) or _ANSWERED_WINDOW.search(text) or _CHOICE_FOLLOW.search(text))


def render_choice(prompt: ChoicePrompt) -> str:
    payload = {
        "mode": prompt.mode,
        "prompt": prompt.prompt,
        "options": [{"label": option.label, "value": option.value} for option in prompt.options],
    }
    return f"{prompt.prompt}\n\n```assetmind-choices\n{json.dumps(payload, ensure_ascii=False)}\n```"


def intake_question(text: str, assets: list[AssetRequest]) -> ChoicePrompt | None:
    """Question that must be answered before this turn runs."""

    for asset in assets:
        if asset.symbol.endswith("11") and asset.asset_class is None:
            return ChoicePrompt(
                mode="single",
                prompt=f"{asset.symbol} termina em 11. Devo tratar como acao ou como fundo imobiliario?",
                options=(
                    ChoiceOption("Ação", f"{asset.symbol} e uma acao"),
                    ChoiceOption("Fundo imobiliário", f"{asset.symbol} e um fundo imobiliario"),
                ),
            )
    if _COMPLETE.search(text) and not _CHOSEN.search(text):
        return ChoicePrompt(
            mode="multiple",
            prompt=(
                "Para agregar esta execucao, escolha o que entra agora. "
                "Pode marcar mais de um: cotacao, multiplos, faixa de 52 semanas, manchetes ou cenario."
            ),
            options=(
                ChoiceOption("Cotação e retorno de 3 meses", "cotacao e retorno"),
                ChoiceOption("Múltiplos atuais", "multiplos atuais"),
                ChoiceOption("Faixa de 52 semanas", "faixa de 52 semanas"),
                ChoiceOption("Até 3 manchetes", "noticias"),
                ChoiceOption("Cenário ilustrativo", "cenario ilustrativo"),
            ),
        )
    if _PROJECTION.search(text) and not _HORIZON.search(text):
        return ChoicePrompt(
            mode="single",
            prompt=(
                "O cenario ilustrativo aplica um choque de -15%, 0% ou +15% no preco de referencia. "
                "Nao e uma projecao de valorizacao. Qual horizonte devo registrar no rotulo?"
            ),
            options=(
                ChoiceOption("Curto prazo", "curto prazo"),
                ChoiceOption("Médio prazo", "medio prazo"),
                ChoiceOption("Longo prazo", "longo prazo"),
            ),
        )
    if _LONG_RETURN.search(text) and _RETURN_WORD.search(text) and not _ANSWERED_WINDOW.search(text):
        return ChoicePrompt(
            mode="single",
            prompt=(
                "O retorno calculado usa cerca de 3 meses de pregoes. "
                "A faixa de 52 semanas e um campo da cotacao e nao e o retorno desse intervalo. "
                "Sigo com o retorno de 3 meses, com a faixa de 52 semanas, ou com os dois?"
            ),
            options=(
                ChoiceOption("Retorno de 3 meses", "retorno de 3 meses"),
                ChoiceOption("Faixa de 52 semanas", "faixa de 52 semanas"),
                ChoiceOption("Os dois", "os dois"),
            ),
        )
    if _NEWS.search(text) and not assets:
        return ChoicePrompt(
            mode="single",
            prompt="De qual ativo devo buscar as manchetes?",
            options=tuple(ChoiceOption(entry.symbol, f"noticias {entry.symbol}") for entry in CATALOG),
        )
    return None

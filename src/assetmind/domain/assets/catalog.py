"""Small local catalog used by asset search.

This is not a market-wide search index. It avoids unbounded provider calls.
"""

import re

from pydantic import BaseModel

from assetmind.domain.assets.identity import AssetClass, Market


class CatalogEntry(BaseModel):
    symbol: str
    asset_class: AssetClass
    market: Market
    name: str


CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry(symbol="PETR4", asset_class=AssetClass.EQUITY, market=Market.B3, name="Petrobras PN"),
    CatalogEntry(symbol="VALE3", asset_class=AssetClass.EQUITY, market=Market.B3, name="Vale ON"),
    CatalogEntry(symbol="ITUB4", asset_class=AssetClass.EQUITY, market=Market.B3, name="Itau Unibanco PN"),
    CatalogEntry(
        symbol="MGLU3",
        asset_class=AssetClass.EQUITY,
        market=Market.B3,
        name="Magazine Luiza ON",
    ),
    CatalogEntry(
        symbol="HGLG11",
        asset_class=AssetClass.REAL_ESTATE,
        market=Market.B3,
        name="CSHG Logistica FII",
    ),
    CatalogEntry(
        symbol="MXRF11",
        asset_class=AssetClass.REAL_ESTATE,
        market=Market.B3,
        name="Maxi Renda FII",
    ),
    CatalogEntry(
        symbol="bitcoin",
        asset_class=AssetClass.CRYPTO,
        market=Market.CRYPTO,
        name="Bitcoin",
    ),
    CatalogEntry(
        symbol="ethereum",
        asset_class=AssetClass.CRYPTO,
        market=Market.CRYPTO,
        name="Ethereum",
    ),
)


_CLASS_QUERY: dict[str, AssetClass] = {
    "acao": AssetClass.EQUITY,
    "acoes": AssetClass.EQUITY,
    "ação": AssetClass.EQUITY,
    "ações": AssetClass.EQUITY,
    "equity": AssetClass.EQUITY,
    "fii": AssetClass.REAL_ESTATE,
    "fiis": AssetClass.REAL_ESTATE,
    "fundo": AssetClass.REAL_ESTATE,
    "fundos": AssetClass.REAL_ESTATE,
    "real_estate": AssetClass.REAL_ESTATE,
    "cripto": AssetClass.CRYPTO,
    "criptos": AssetClass.CRYPTO,
    "criptomoeda": AssetClass.CRYPTO,
    "criptomoedas": AssetClass.CRYPTO,
    "crypto": AssetClass.CRYPTO,
}
_EQUITY_WORD = re.compile(r"\b(acoes|ações|acao|ação|equity|equities)\b", re.IGNORECASE)
_FII_WORD = re.compile(r"fundo imobili|\bfii\b|\bfiis\b|real_estate", re.IGNORECASE)
_CRYPTO_WORD = re.compile(r"\b(cripto\w*|crypto)\b", re.IGNORECASE)

CATALOG_LIMITATION = "Search uses the local catalog, not a live market listing."
LIVE_LISTING_LIMITATION = "Rows come from the brapi quote list and the CoinGecko coin list. This page is not every row."
CHAT_PAGE = 12
MESSAGE_STOP = frozenset(
    {
        "web",
        "site",
        "http",
        "https",
        "google",
        "news",
        "analise",
        "análise",
        "noticia",
        "noticias",
        "manchete",
        "manchetes",
        "mercado",
        "preco",
        "preço",
        "retorno",
        "ativo",
        "ativos",
        "tipo",
        "tipos",
        "qual",
        "quais",
        "sobre",
        "para",
        "como",
        "acao",
        "ação",
        "acoes",
        "ações",
        "fii",
        "fiis",
        "fundo",
        "fundos",
        "cripto",
        "criptos",
        "crypto",
        "criptomoeda",
        "criptomoedas",
    }
)


def search_entries(
    entries: list[CatalogEntry] | tuple[CatalogEntry, ...],
    query: str,
    limit: int = 10,
) -> list[CatalogEntry]:
    needle = query.strip().lower()
    if not needle:
        return list(entries)[:limit]
    kind = _CLASS_QUERY.get(needle)
    if kind is not None:
        return [entry for entry in entries if entry.asset_class is kind][:limit]
    matches = [entry for entry in entries if needle in entry.symbol.lower() or needle in entry.name.lower()]
    return matches[:limit]


def search_catalog(query: str, limit: int = 10) -> list[CatalogEntry]:
    return search_entries(CATALOG, query, limit)


def classes_mentioned(text: str) -> set[AssetClass]:
    found: set[AssetClass] = set()
    if _EQUITY_WORD.search(text):
        found.add(AssetClass.EQUITY)
    if _FII_WORD.search(text):
        found.add(AssetClass.REAL_ESTATE)
    if _CRYPTO_WORD.search(text):
        found.add(AssetClass.CRYPTO)
    return found


def choice_page(
    entries: list[CatalogEntry] | tuple[CatalogEntry, ...],
    text: str = "",
    limit: int = CHAT_PAGE,
) -> list[CatalogEntry]:
    """A short page of the universe. An unnamed class returns a slice of each type."""

    kinds = classes_mentioned(text)
    if kinds:
        return [entry for entry in entries if entry.asset_class in kinds][:limit]
    per_class = max(1, limit // 3)
    page: list[CatalogEntry] = []
    for kind in (AssetClass.EQUITY, AssetClass.REAL_ESTATE, AssetClass.CRYPTO):
        page.extend([entry for entry in entries if entry.asset_class is kind][:per_class])
    return page[:limit]


def browse_catalog(text: str = "") -> list[CatalogEntry]:
    """Catalog rows the search API would return, narrowed when the text names a class."""

    return choice_page(CATALOG, text, limit=len(CATALOG))


def catalog_payload(entries: list[CatalogEntry], *, limitation: str = CATALOG_LIMITATION) -> dict[str, object]:
    by_type: dict[str, list[dict[str, str]]] = {}
    results: list[dict[str, str]] = []
    for entry in entries:
        row = entry.model_dump(mode="json")
        results.append(row)
        by_type.setdefault(entry.asset_class.value, []).append(row)
    return {"results": results, "by_type": by_type, "limitation": limitation}

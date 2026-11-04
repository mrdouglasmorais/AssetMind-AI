"""Small local catalog used by asset search.

This is not a market-wide search index. It avoids unbounded provider calls.
"""

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


def search_catalog(query: str, limit: int = 10) -> list[CatalogEntry]:
    needle = query.strip().lower()
    if not needle:
        return []
    matches = [entry for entry in CATALOG if needle in entry.symbol.lower() or needle in entry.name.lower()]
    return matches[:limit]

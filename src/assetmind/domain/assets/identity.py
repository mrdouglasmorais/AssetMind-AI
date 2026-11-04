"""Asset identity, taxonomy, and deterministic classification."""

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from assetmind.domain.errors import AmbiguousAssetError, InvalidAssetError

_B3_SYMBOL = re.compile(r"^[A-Z]{4}\d{1,2}$")
_CRYPTO_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_CRYPTO_ALIASES = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
}


class AssetClass(StrEnum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"


class Market(StrEnum):
    B3 = "b3"
    CRYPTO = "crypto"


class AssetRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=64)
    asset_class: AssetClass | None = None
    market: Market | None = None


class ResolvedAsset(BaseModel):
    symbol: str
    asset_class: AssetClass
    market: Market
    classification_confidence: str
    notes: list[str] = Field(default_factory=list)


def resolve_asset(request: AssetRequest) -> ResolvedAsset:
    """Classify an asset without calling a model.

    Tickers that end in 11 are ambiguous on B3: they can be FII quotas or equity
    units. The caller must set ``asset_class`` for those symbols.
    """

    raw = request.symbol.strip()
    if not raw or any(character.isspace() for character in raw):
        raise InvalidAssetError("Asset symbol must be a single token.")

    if request.asset_class is AssetClass.CRYPTO or _looks_like_crypto(raw):
        if _B3_SYMBOL.match(raw.upper()):
            raise InvalidAssetError(f"{raw.upper()} is a B3 ticker and cannot be analyzed as crypto.")
        symbol = _normalize_crypto(raw)
        if request.asset_class not in (None, AssetClass.CRYPTO):
            raise InvalidAssetError(f"{raw} cannot be classified as {request.asset_class}.")
        if request.market not in (None, Market.CRYPTO):
            raise InvalidAssetError("Crypto assets use the crypto market.")
        return ResolvedAsset(
            symbol=symbol,
            asset_class=AssetClass.CRYPTO,
            market=Market.CRYPTO,
            classification_confidence="explicit" if request.asset_class else "alias",
        )

    symbol = raw.upper()
    if not _B3_SYMBOL.match(symbol):
        raise InvalidAssetError("Unsupported symbol. Use a B3 ticker such as PETR4 or a crypto id such as bitcoin.")

    if symbol.endswith("11") and request.asset_class is None:
        raise AmbiguousAssetError(
            f"{symbol} ends in 11 and can be either an equity unit or a FII. Set asset_class to equity or real_estate."
        )

    asset_class = request.asset_class or AssetClass.EQUITY
    if asset_class is AssetClass.CRYPTO:
        raise InvalidAssetError(f"{symbol} is a B3 ticker and cannot be analyzed as crypto.")
    if request.market not in (None, Market.B3):
        raise InvalidAssetError("B3 tickers use the b3 market.")

    notes: list[str] = []
    if symbol.endswith("11") and asset_class is AssetClass.EQUITY:
        notes.append("Treated as a B3 equity unit, not as a FII.")
    if symbol.endswith("11") and asset_class is AssetClass.REAL_ESTATE:
        notes.append("Treated as a Brazilian FII quota, not as a CRI or direct property.")

    return ResolvedAsset(
        symbol=symbol,
        asset_class=asset_class,
        market=Market.B3,
        classification_confidence="explicit" if request.asset_class else "pattern",
        notes=notes,
    )


def _looks_like_crypto(raw: str) -> bool:
    lowered = raw.lower()
    if lowered in _CRYPTO_ALIASES or lowered in _CRYPTO_ALIASES.values():
        return True
    upper = raw.upper()
    return _CRYPTO_ID.match(lowered) is not None and _B3_SYMBOL.match(upper) is None


def _normalize_crypto(raw: str) -> str:
    lowered = raw.lower()
    if not _CRYPTO_ID.match(_CRYPTO_ALIASES.get(lowered, lowered)):
        raise InvalidAssetError("Crypto ids must be lowercase CoinGecko identifiers.")
    return _CRYPTO_ALIASES.get(lowered, lowered)

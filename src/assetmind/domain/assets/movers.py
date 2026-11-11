"""Market movers: rising and falling assets from provider quotes.

Rows are reading patterns over emitted quotes. They are not recommendations.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from assetmind.domain.assets.identity import AssetClass, Market


class MoverDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    BOTH = "both"


class MoverSort(StrEnum):
    CHANGE = "change"
    VOLUME = "volume"


class MoverAssetType(StrEnum):
    EQUITY = "equity"
    REAL_ESTATE = "real_estate"
    CRYPTO = "crypto"
    ALL = "all"


class MoverItem(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    market: Market
    price: float | None = None
    change_percent: float | None = None
    volume: float | None = None
    currency: str | None = None


class MoversPagination(BaseModel):
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=50)
    has_next_rising: bool = False
    has_next_falling: bool = False


class MoversResult(BaseModel):
    rising: list[MoverItem] = Field(default_factory=list)
    falling: list[MoverItem] = Field(default_factory=list)
    pagination: MoversPagination
    retrieved_at: datetime
    limitation: str


MOVERS_LIMITATION = (
    "Change and volume come from the market provider for this page. "
    "B3 values follow brapi quote list change/volume. Crypto uses CoinGecko 24h change. "
    "This is not a recommendation."
)

FIXTURE_MOVERS_LIMITATION = (
    "Fixture movers are synthetic samples for offline demos. They are not live quotes."
)

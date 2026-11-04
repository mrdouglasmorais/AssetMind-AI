"""API key authentication for write and analysis routes."""

import hmac

from assetmind.config.settings import Settings


class AuthenticationError(Exception):
    pass


def require_api_key(settings: Settings, presented: str | None) -> None:
    expected = settings.api_key
    if not expected:
        raise AuthenticationError("ASSETMIND_API_KEY is not configured.")
    if not presented or not hmac.compare_digest(presented, expected):
        raise AuthenticationError("Invalid API key.")

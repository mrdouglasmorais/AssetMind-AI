"""Tools exposed to the application. There is no general URL fetch tool."""

from assetmind.providers.http import assert_allowed_url

__all__ = ["assert_allowed_url"]

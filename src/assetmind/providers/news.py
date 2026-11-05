"""Headline lookup. Titles and links only. Article bodies are not stored."""

import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote

import httpx

from assetmind.providers.errors import ProviderError
from assetmind.providers.http import assert_allowed_url

SOURCE_NAME = "Google News"
ALLOWED_HOSTS = {"news.google.com"}
_MAX_ITEMS = 3


def news_search_url(symbol: str) -> str:
    query = quote(f"{symbol} when:7d")
    return f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def parse_headlines(xml_text: str, *, limit: int = _MAX_ITEMS) -> list[dict[str, str | None]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ProviderError("News feed was not valid XML.", provider="google-news") from exc
    items: list[dict[str, str | None]] = []
    for node in root.iter("item"):
        title = _text(node, "title")
        link = _text(node, "link")
        if not title or not link:
            continue
        published = _published(node.findtext("pubDate"))
        source = node.find("source")
        publisher = source.text.strip() if source is not None and source.text else SOURCE_NAME
        items.append(
            {
                "title": title,
                "url": link,
                "published_at": published,
                "publisher": publisher,
            }
        )
        if len(items) >= limit:
            break
    return items


async def fetch_headlines(client: httpx.AsyncClient, symbol: str, *, limit: int = _MAX_ITEMS) -> dict[str, object]:
    url = news_search_url(symbol)
    assert_allowed_url(url, ALLOWED_HOSTS)
    try:
        response = await client.get(url, timeout=8, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise ProviderError("News source did not respond.", provider="google-news") from exc
    if response.status_code >= 400:
        raise ProviderError(f"News source returned {response.status_code}.", provider="google-news")
    return {
        "symbol": symbol,
        "source": SOURCE_NAME,
        "source_url": url,
        "window": "7d",
        "items": parse_headlines(response.text, limit=limit),
    }


def _text(node: ET.Element, tag: str) -> str | None:
    value = node.findtext(tag)
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _published(value: str | None) -> str | None:
    if not value:
        return None
    parsed = email.utils.parsedate_to_datetime(value)
    if not isinstance(parsed, datetime):
        return None
    return parsed.isoformat()

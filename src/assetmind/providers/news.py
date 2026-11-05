"""Headline lookup. Titles and links only. Article bodies are not stored."""

import asyncio
import email.utils
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from urllib.parse import quote, urlparse

import httpx

from assetmind.providers.errors import ProviderError, ProviderTimeout
from assetmind.providers.http import assert_allowed_url

SOURCE_NAME = "Google News"
ALLOWED_HOSTS = {"news.google.com"}
_MAX_ITEMS = 3
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
_MEDIA = "{http://search.yahoo.com/mrss/}"
_IMAGE_SRC = re.compile(r"""<img\b[^>]*\bsrc=["'](https://[^"']+)["']""", re.IGNORECASE)


def news_search_url(symbol: str) -> str:
    query = quote(f"{symbol} when:7d")
    return f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def parse_headlines(
    xml_text: str,
    *,
    symbol: str = "",
    retrieved_at: datetime | None = None,
    limit: int = _MAX_ITEMS,
) -> list[dict[str, str | None]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ProviderError("News feed was not valid XML.", provider="google-news") from exc
    collected = retrieved_at or datetime.now(UTC)
    stamp = collected.isoformat()
    items: list[dict[str, str | None]] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    for node in root.iter("item"):
        title = _text(node, "title")
        link = _text(node, "link")
        if not title or not link or not valid_headline_url(link):
            continue
        title_key = title.casefold()
        if title_key in seen_titles or link in seen_urls:
            continue
        seen_titles.add(title_key)
        seen_urls.add(link)
        published = _published(node.findtext("pubDate"))
        source = node.find("source")
        publisher = source.text.strip() if source is not None and source.text else SOURCE_NAME
        items.append(
            {
                "title": title,
                "url": link,
                "published_at": published,
                "publisher": publisher,
                "retrieved_at": stamp,
                "relevance": _relevance(symbol, title, link),
                "image_url": _image_url(node),
            }
        )
    items.sort(key=lambda item: item["relevance"] != "symbol")
    return items[:limit]


def valid_headline_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if host in _BLOCKED_HOSTS or host.endswith(".local"):
        return False
    return True


async def fetch_headlines(client: httpx.AsyncClient, symbol: str, *, limit: int = _MAX_ITEMS) -> dict[str, object]:
    url = news_search_url(symbol)
    assert_allowed_url(url, ALLOWED_HOSTS)
    retrieved_at = datetime.now(UTC)
    try:
        response = await asyncio.wait_for(client.get(url, timeout=8, follow_redirects=True), timeout=8)
    except TimeoutError as exc:
        raise ProviderTimeout("News source timed out.", provider="google-news") from exc
    except httpx.HTTPError as exc:
        raise ProviderError("News source did not respond.", provider="google-news") from exc
    if response.status_code >= 400:
        raise ProviderError(f"News source returned {response.status_code}.", provider="google-news")
    return {
        "symbol": symbol,
        "source": SOURCE_NAME,
        "source_url": url,
        "window": "7d",
        "retrieved_at": retrieved_at.isoformat(),
        "items": parse_headlines(response.text, symbol=symbol, retrieved_at=retrieved_at, limit=limit),
    }


def _relevance(symbol: str, title: str, url: str) -> str:
    token = symbol.casefold()
    if token and (token in title.casefold() or token in url.casefold()):
        return "symbol"
    return "search"


def _image_url(node: ET.Element) -> str | None:
    """Https image declared on the item. The article page is not requested."""

    for tag in (f"{_MEDIA}content", f"{_MEDIA}thumbnail", "content", "thumbnail"):
        media = node.find(tag)
        if media is None:
            continue
        medium = (media.attrib.get("medium") or "image").lower()
        url = media.attrib.get("url")
        if medium == "image" and url and valid_headline_url(url):
            return url
    description = node.findtext("description") or ""
    match = _IMAGE_SRC.search(description)
    if match and valid_headline_url(match.group(1)):
        return match.group(1)
    return None


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

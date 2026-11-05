import httpx
import pytest

from assetmind.agents.chat import (
    _headline_text,
    _periods_tool,
    _shock_tool,
    answer_message,
    assets_from_message,
)
from assetmind.api.app import create_app
from assetmind.config.settings import Settings
from assetmind.domain.assets.identity import AssetClass, AssetRequest
from assetmind.domain.periods import continues_session, intake_question, periods_for, render_choice
from assetmind.providers.errors import ProviderError
from assetmind.providers.news import fetch_headlines, parse_headlines

_FEED = """<?xml version="1.0"?>
<rss><channel>
<item>
<title>Titulo um</title>
<link>https://news.google.com/rss/articles/a</link>
<pubDate>Wed, 04 Nov 2026 18:00:00 GMT</pubDate>
<source>Fonte A</source>
</item>
<item><title>Titulo dois</title><link>https://news.google.com/rss/articles/b</link></item>
<item><title>Titulo tres</title><link>https://news.google.com/rss/articles/c</link></item>
<item><title>Titulo quatro</title><link>https://news.google.com/rss/articles/d</link></item>
</channel></rss>"""


def test_headlines_keep_three_titles_and_drop_the_rest() -> None:
    from datetime import UTC, datetime

    collected = datetime(2026, 11, 5, tzinfo=UTC)
    items = parse_headlines(_FEED, symbol="PETR4", retrieved_at=collected)
    assert len(items) == 3
    assert items[0]["title"] == "Titulo um"
    assert items[0]["publisher"] == "Fonte A"
    assert items[0]["published_at"] == "2026-11-04T18:00:00+00:00"
    assert items[0]["retrieved_at"] == "2026-11-05T00:00:00+00:00"
    assert items[0]["relevance"] == "search"
    assert items[0]["image_url"] is None


def test_periods_keep_the_return_window_separate_from_52_weeks() -> None:
    lines = periods_for(AssetClass.EQUITY)
    assert any("3 meses" in line for line in lines)
    assert any("52 semanas" in line and "separado" in line for line in lines)


async def test_asking_for_asset_types_returns_the_catalog_grouped() -> None:
    class _Idle:
        async def run(self, **_kwargs: object) -> object:
            raise AssertionError("a catalog list must not fetch the market")

    text = await answer_message(
        _Idle(),  # type: ignore[arg-type]
        Settings(api_key="local", groq_api_key=None, embedding_provider="hashed"),
        "tipos de ativos",
    )
    assert "Ações: PETR4" in text
    assert "FIIs: HGLG11" in text
    assert "Cripto: bitcoin" in text
    assert "```assetmind-choices" in text
    assert '"value": "analise PETR4"' in text
    equities = await answer_message(
        _Idle(),  # type: ignore[arg-type]
        Settings(api_key="local", groq_api_key=None, embedding_provider="hashed"),
        "quais acoes",
    )
    assert "PETR4" in equities
    assert "bitcoin" not in equities


def test_a_ticker_ending_in_11_keeps_the_class_from_the_reply() -> None:
    fund = assets_from_message("ABCD11 e um fundo imobiliario")
    share = assets_from_message("WXYZ11 e uma acao")
    assert fund[0].asset_class is AssetClass.REAL_ESTATE
    assert share[0].asset_class is AssetClass.EQUITY
    assert intake_question("ABCD11 e um fundo imobiliario", fund) is None


def test_a_broad_request_asks_which_blocks_belong() -> None:
    question = intake_question("analise completa PETR4", [])
    assert question is not None
    assert question.mode == "multiple"
    assert "manchetes" in question.prompt
    rendered = render_choice(question)
    assert "```assetmind-choices" in rendered
    assert '"prompt": "Para agregar esta execucao' in rendered
    assert '"label": "Até 3 manchetes"' in rendered


def test_a_projection_asks_for_a_horizon_before_it_runs() -> None:
    question = intake_question("projecao de valorizacao PETR4", [])
    assert question is not None
    assert question.mode == "single"
    assert "Nao e uma projecao" in question.prompt
    assert [option.value for option in question.options] == ["curto prazo", "medio prazo", "longo prazo"]


def test_missing_class_horizon_and_news_each_ask_one_question() -> None:
    ambiguous = intake_question("analise ABCD11", [AssetRequest(symbol="ABCD11")])
    assert ambiguous is not None
    assert "fundo imobiliario" in ambiguous.prompt
    assert [option.label for option in ambiguous.options] == ["Ação", "Fundo imobiliário"]
    news = intake_question("noticias", [])
    assert news is not None
    assert news.prompt == "De qual ativo devo buscar as manchetes?"
    assert any(option.value == "noticias PETR4" for option in news.options)
    assert any(option.label.startswith("Ações · PETR4") for option in news.options)
    assert any(option.label.startswith("FIIs · HGLG11") for option in news.options)
    long_window = intake_question("retorno em 5 anos da PETR4", [])
    assert long_window is not None
    assert "3 meses" in long_window.prompt
    assert intake_question("retorno de 3 meses", []) is None
    assert continues_session("12 meses") is True
    assert continues_session("os dois") is True
    assert continues_session("cotacao e retorno") is True


def test_invalid_duplicate_and_off_symbol_headlines_are_filtered() -> None:
    from datetime import UTC, datetime

    feed = """<?xml version="1.0"?>
<rss><channel>
<item><title>Outro assunto</title><link>http://news.google.com/insecure</link></item>
<item><title>PETR4 no pregao</title><link>https://news.google.com/rss/articles/petr4</link></item>
<item><title>PETR4 no pregao</title><link>https://news.google.com/rss/articles/copy</link></item>
<item><title>Sem o codigo</title><link>https://news.google.com/rss/articles/other</link></item>
<item><title>Local</title><link>https://user:secret@localhost/a</link></item>
</channel></rss>"""
    items = parse_headlines(feed, symbol="PETR4", retrieved_at=datetime(2026, 11, 5, tzinfo=UTC))
    assert [item["title"] for item in items] == ["PETR4 no pregao", "Sem o codigo"]
    assert items[0]["relevance"] == "symbol"
    assert items[1]["relevance"] == "search"


def test_invalid_or_incomplete_feed_items_are_dropped() -> None:
    with pytest.raises(ProviderError):
        parse_headlines("<rss>")
    blank = "<rss><channel><item><title>   </title><link>https://news.google.com/a</link></item></channel></rss>"
    assert parse_headlines(blank) == []
    kept = parse_headlines(
        "<rss><channel><item><title>Um</title><link>https://news.google.com/a</link></item></channel></rss>"
    )
    assert kept[0]["publisher"] == "Google News"
    assert kept[0]["published_at"] is None


def test_item_image_is_kept_and_the_article_is_not_fetched() -> None:
    feed = """<?xml version="1.0"?>
<rss xmlns:media="http://search.yahoo.com/mrss/"><channel>
<image><url>https://lh3.googleusercontent.com/logo</url></image>
<item>
<title>Com foto</title>
<link>https://news.google.com/rss/articles/img</link>
<media:content url="http://insecure.example/a.jpg" medium="image"/>
</item>
<item>
<title>Foto segura</title>
<link>https://news.google.com/rss/articles/ok</link>
<description>&lt;img src="https://news.google.com/api/attachments/thumb"&gt;</description>
</item>
<item>
<title>Local</title>
<link>https://news.google.com/rss/articles/local</link>
<media:content url="https://127.0.0.1/a.jpg" medium="image"/>
</item>
</channel></rss>"""
    items = parse_headlines(feed, symbol="PETR4")
    by_title = {item["title"]: item["image_url"] for item in items}
    assert by_title["Com foto"] is None
    assert by_title["Foto segura"] == "https://news.google.com/api/attachments/thumb"
    assert by_title["Local"] is None


@pytest.mark.asyncio
async def test_news_lookup_reports_a_source_failure() -> None:
    class _Down:
        async def get(self, url: str, timeout: float = 8, follow_redirects: bool = True) -> object:
            raise httpx.ConnectError("down")

    with pytest.raises(ProviderError):
        await fetch_headlines(_Down(), "PETR4")  # type: ignore[arg-type]

    class _Rejected:
        status_code = 503
        text = ""

        async def get(self, url: str, timeout: float = 8, follow_redirects: bool = True) -> "_Rejected":
            return self

    with pytest.raises(ProviderError):
        await fetch_headlines(_Rejected(), "PETR4")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_news_only_turn_names_the_source_and_does_not_analyze(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(client: object, symbol: str, *, limit: int = 3) -> dict[str, object]:
        return {
            "symbol": symbol,
            "source": "Google News",
            "source_url": "https://news.google.com/rss/search?q=PETR4",
            "window": "7d",
            "items": [
                {
                    "title": "Titulo um",
                    "publisher": "Fonte A",
                    "published_at": "2026-11-04T18:00:00+00:00",
                    "url": "https://news.google.com/rss/articles/a",
                }
            ],
        }

    monkeypatch.setattr("assetmind.agents.chat.fetch_headlines", _fake)

    class _Idle:
        async def run(self, **_kwargs: object) -> object:
            raise AssertionError("news only must not run the analysis")

    text = await answer_message(_Idle(), Settings(api_key="local"), "noticias PETR4")  # type: ignore[arg-type]
    assert "Fonte de consulta: Google News." in text
    assert "```assetmind-news" in text
    assert "Titulo um" in text
    assert "nao e copiado" in text


@pytest.mark.asyncio
async def test_tools_ask_for_class_or_horizon_and_list_periods() -> None:
    periods = _periods_tool()
    listed = await periods.entrypoint(asset_class="acao")
    assert "3 meses" in listed
    unknown = await periods.entrypoint(asset_class="outro")
    assert "acao, fii ou cripto" in unknown
    shocks = _shock_tool(None, Settings(api_key="local"), None)  # type: ignore[arg-type]
    asked = await shocks.entrypoint(symbol="PETR4", horizon_label="  ")
    assert "horizonte" in asked


@pytest.mark.asyncio
async def test_headline_text_reports_a_source_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _down(client: object, symbol: str, *, limit: int = 3) -> dict[str, object]:
        raise ProviderError("timeout", provider="google-news")

    monkeypatch.setattr("assetmind.agents.chat.fetch_headlines", _down)
    text = await _headline_text("PETR4")
    assert "Fonte de consulta: Google News." in text
    assert "timeout" in text


@pytest.mark.asyncio
async def test_complete_analysis_asks_and_does_not_fetch(tmp_path: object) -> None:
    class _Idle:
        async def run(self, **_kwargs: object) -> object:
            raise AssertionError("a broad request must ask before fetching")

    text = await answer_message(
        _Idle(),  # type: ignore[arg-type]
        Settings(api_key="local", database_url=f"sqlite+pysqlite:///{tmp_path}/unused.db"),  # type: ignore[operator]
        "analise completa da PETR4",
    )
    assert "manchetes" in text


@pytest.mark.asyncio
async def test_news_route_returns_the_source_and_three_headlines(tmp_path: object) -> None:
    class _Response:
        status_code = 200
        text = _FEED

    class _Client:
        async def get(self, url: str, timeout: float = 8, follow_redirects: bool = True) -> _Response:
            assert url.startswith("https://news.google.com/rss/search?")
            assert "PETR4" in url
            return _Response()

    database = tmp_path / "news.db"  # type: ignore[operator]
    app = create_app(
        Settings(
            api_key="test-key-123",
            provider_mode="fixtures",
            database_url=f"sqlite+pysqlite:///{database}",
            agentos_enabled=False,
            agentos_jwt_secret=None,
            groq_api_key=None,
        )
    )
    app.state.http_client = _Client()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/assets/PETR4/news", headers={"X-API-Key": "test-key-123"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "Google News"
    assert body["window"] == "7d"
    assert body["retrieved_at"]
    assert len(body["items"]) == 3
    assert body["items"][0]["title"] == "Titulo um"

import json

import httpx

from assetmind.application.budget import TokenBalance
from assetmind.application.embeddings import LedgerEmbedder, build_session_embedder
from assetmind.application.session_vectors import SessionVectorStore
from assetmind.config.settings import Settings
from assetmind.domain.errors import BudgetExceededError
from assetmind.domain.memory.chunks import chunk_text
from assetmind.domain.memory.embedder import EmbeddingError, HashedEmbedder
from assetmind.providers.embeddings import GroqEmbedder, parse_embeddings


def test_a_short_turn_stays_one_chunk_and_a_report_is_split() -> None:
    assert chunk_text("  analise   o   bitcoin  ") == ["analise o bitcoin"]
    assert chunk_text("   ") == []
    report = "retorno do periodo. " * 40 + "drawdown maximo da janela"
    chunks = chunk_text(report)
    assert len(chunks) > 1
    assert chunks[-1].endswith("drawdown maximo da janela")
    assert chunks[0].startswith("retorno do periodo")


def test_recall_finds_a_figure_that_sits_past_the_first_window() -> None:
    store = SessionVectorStore(":memory:")
    report = "retorno do periodo. " * 40 + "drawdown maximo da janela"
    store.remember("s", "assistant", report, ["PETR4"])
    found = store.recall("s", "drawdown maximo")
    assert found
    assert "drawdown maximo da janela" in found[0]["memoria"]


class _Meaning:
    name = "test-model"
    prompt_tokens = 0

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "bitcoin" in text or "criptomoeda" in text else [0.0, 1.0] for text in texts]


def test_a_model_embedder_retrieves_a_paraphrase() -> None:
    store = SessionVectorStore(":memory:", embedder=_Meaning())
    store.remember("s", "user", "qual o preco", [])
    store.remember("s", "user", "analise o bitcoin", ["bitcoin"])
    store.remember("s", "user", "analise a petrobras", ["PETR4"])
    body = store.recall("s", "situacao daquela criptomoeda")[0]["memoria"]
    assert body.index("analise o bitcoin") < body.index("analise a petrobras")


class _Down:
    name = "groq:down"
    prompt_tokens = 0

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError("down")


def test_a_failed_model_call_stores_the_hashed_vector() -> None:
    store = SessionVectorStore(":memory:", embedder=_Down())
    store.remember("s", "user", "analise o bitcoin", ["bitcoin"])
    row = store._connection.execute("SELECT embedder FROM session_vectors").fetchone()
    assert row is not None
    assert row[0] == "hashed-64"
    assert "analise o bitcoin" in store.recall("s", "bitcoin")[0]["memoria"]


def test_parse_embeddings_restores_the_request_order() -> None:
    vectors, tokens = parse_embeddings(
        {
            "data": [
                {"index": 1, "embedding": [0.0, 2.0]},
                {"index": 0, "embedding": [1.0, 0.0]},
            ],
            "usage": {"prompt_tokens": 9},
        },
        expected=2,
    )
    assert vectors == [[1.0, 0.0], [0.0, 2.0]]
    assert tokens == 9


def test_groq_embedder_posts_the_batch_and_reads_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.host == "api.groq.com"
        assert request.headers["authorization"] == "Bearer test-key"
        assert body["model"] == "nomic-embed-text-v1.5"
        rows = [{"index": index, "embedding": [float(index), 1.0]} for index, _text in enumerate(body["input"])]
        return httpx.Response(200, json={"data": rows, "usage": {"prompt_tokens": 14}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        embedder = GroqEmbedder(api_key="test-key", client=client)
        assert embedder.embed_many(["um", "dois"]) == [[0.0, 1.0], [1.0, 1.0]]
        assert embedder.prompt_tokens == 14


class _Inner:
    name = "groq:nomic-embed-text-v1.5"
    prompt_tokens = 7

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _text in texts]


class _Repo:
    def __init__(self, remaining: int) -> None:
        self.remaining = remaining
        self.kind = ""

    def token_balance(self, allowance_tokens: int) -> TokenBalance:
        return TokenBalance(
            analyses=0,
            estimated_input_tokens=0,
            estimated_output_tokens=0,
            estimated_tokens=0,
            actual_input_tokens=0,
            actual_output_tokens=0,
            llm_calls=0,
            provider_calls=0,
            estimated_cost_usd=0,
            allowance_tokens=allowance_tokens,
            remaining_tokens=self.remaining,
        )

    def record_usage(self, *, kind: str, usage: object) -> str:
        self.kind = kind
        return "usage"


def test_the_ledger_records_an_embedding_and_blocks_when_the_allowance_is_gone() -> None:
    settings = Settings(api_key="local", embedding_provider="hashed", groq_api_key=None)
    repo = _Repo(remaining=1000)
    embedder = LedgerEmbedder(_Inner(), repo, settings)  # type: ignore[arg-type]
    assert embedder.embed_many(["analise"]) == [[1.0]]
    assert repo.kind == "embedding"
    blocked = LedgerEmbedder(_Inner(), _Repo(remaining=0), settings)  # type: ignore[arg-type]
    try:
        blocked.embed_many(["analise"])
    except BudgetExceededError:
        return
    raise AssertionError("an empty allowance must stop the embedding call")


def test_the_session_embedder_stays_hashed_without_a_groq_key() -> None:
    settings = Settings(api_key="local", embedding_provider="groq", groq_api_key="")
    assert isinstance(build_session_embedder(settings, None), HashedEmbedder)

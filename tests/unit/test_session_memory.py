import hashlib

from assetmind.agents.chat import answer_message, resolve_assets
from assetmind.application.session_vectors import SessionVectorStore
from assetmind.config.settings import Settings
from assetmind.domain.assets.catalog import CATALOG
from assetmind.domain.memory.vectors import cosine, embed, rank_documents


def test_retrieval_prefers_shared_words_and_misses_a_paraphrase() -> None:
    documents = [
        "analise o bitcoin",
        "analise a petrobras",
        "quero saber o resultado",
    ]
    ranked = rank_documents("preco do bitcoin", documents)
    assert ranked[0][1] == "analise o bitcoin"
    lexical = rank_documents("preco do bitcoin", ["analise o bitcoin"])[0][0]
    paraphrase = rank_documents("situacao daquela criptomoeda agora", ["analise o bitcoin"])[0][0]
    assert paraphrase < lexical
    target = hashlib.sha256(b"bitcoin").digest()[0] % 64
    collision = next(
        word
        for number in range(10000)
        if (word := f"zz{number}") and hashlib.sha256(word.encode()).digest()[0] % 64 == target
    )
    assert cosine(embed("bitcoin"), embed(collision)) != 0


def test_similar_questions_rank_above_unrelated_text() -> None:
    question = embed("analise o bitcoin")
    assert cosine(question, embed("preco do bitcoin")) > cosine(question, embed("petrobras vale itau"))


def test_recall_keeps_the_first_question_inside_the_token_budget() -> None:
    store = SessionVectorStore(":memory:", token_budget=30)
    store.remember("s1", "user", "analise o bitcoin", ["bitcoin"])
    store.remember("s1", "user", "x" * 400, ["bitcoin"])
    found = store.recall("s1", "qual foi minha primeira pergunta")
    assert found
    assert "analise o bitcoin" in found[0]["memoria"]
    assert int(found[0]["tokens_estimados"]) <= 30


def test_follow_up_reuses_the_catalog_or_the_previous_assets() -> None:
    everyone = [asset.symbol for asset in resolve_assets("analise todas do exemplo", [])]
    assert everyone == [entry.symbol for entry in CATALOG]
    again = [asset.symbol for asset in resolve_assets("desvalorizacao nos ultimos 5 anos", ["PETR4", "VALE3"])]
    assert again == ["PETR4", "VALE3"]
    listed = [asset.symbol for asset in resolve_assets("PETR4 e bitcoin", ["VALE3"])]
    assert listed == ["PETR4", "bitcoin"]


async def test_a_recall_question_does_not_run_another_analysis() -> None:
    class _Idle:
        async def run(self, **_kwargs: object) -> object:
            raise AssertionError("recall must not fetch the market")

    store = SessionVectorStore(":memory:")
    store.remember("s", "user", "analise o bitcoin", ["bitcoin"])
    text = await answer_message(
        _Idle(),  # type: ignore[arg-type]
        Settings(api_key="local"),
        "qual foi minha primeira pergunta?",
        memory=store,
        session_id="s",
    )
    assert text == "Sua primeira pergunta nesta sessao foi: analise o bitcoin"

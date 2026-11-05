"""Choose the session embedder and record a model call on the ledger."""

from assetmind.application.budget import BudgetLimits, BudgetManager, BudgetSnapshot, estimate_tokens
from assetmind.config.settings import Settings
from assetmind.domain.errors import BudgetExceededError
from assetmind.domain.memory.embedder import HashedEmbedder, TextEmbedder
from assetmind.persistence.repository import AnalysisRepository
from assetmind.providers.embeddings import GroqEmbedder


class LedgerEmbedder:
    """Reserve the allowance, call the model, and write the usage row."""

    def __init__(self, inner: TextEmbedder, repository: AnalysisRepository, settings: Settings) -> None:
        self._inner = inner
        self._repository = repository
        self._settings = settings
        self.name = inner.name
        self.prompt_tokens = 0

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        estimated = sum(estimate_tokens(text) for text in texts)
        balance = self._repository.token_balance(self._settings.token_allowance)
        if estimated > balance.remaining_tokens:
            raise BudgetExceededError("Token allowance exceeded.")
        vectors = self._inner.embed_many(texts)
        actual = int(getattr(self._inner, "prompt_tokens", 0) or 0)
        self.prompt_tokens = actual
        self._repository.record_usage(
            kind="embedding",
            usage=embedding_snapshot(self._settings.budget_limits(), estimated, actual),
        )
        return vectors


def build_session_embedder(settings: Settings, repository: AnalysisRepository | None) -> TextEmbedder:
    if settings.embedding_provider != "groq" or not settings.groq_api_key:
        return HashedEmbedder()
    model = GroqEmbedder(api_key=settings.groq_api_key, model=settings.embedding_model)
    if repository is None:
        return model
    return LedgerEmbedder(model, repository, settings)


def embedding_snapshot(limits: BudgetLimits, estimated_input: int, actual_input: int) -> BudgetSnapshot:
    manager = BudgetManager(limits)
    manager.authorize_llm_call(estimated_input, 0)
    if actual_input:
        manager.record_actual_usage(actual_input, 0)
    return manager.snapshot()

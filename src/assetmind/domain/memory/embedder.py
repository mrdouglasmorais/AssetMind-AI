"""Embedding port. The hashed implementation needs no model and no network."""

from typing import Protocol

from assetmind.domain.memory.vectors import embed

HASHED_EMBEDDER = "hashed-64"


class EmbeddingError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TextEmbedder(Protocol):
    """One vector per text, in the same order."""

    name: str
    prompt_tokens: int

    def embed_many(self, texts: list[str]) -> list[list[float]]: ...


class HashedEmbedder:
    name = HASHED_EMBEDDER
    prompt_tokens = 0

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [embed(text) for text in texts]

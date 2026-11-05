"""Groq embedding client.

The call is skipped unless an API key is configured. Tests pass a recorded
response through `parse_embeddings` and do not contact Groq.
"""

import httpx

from assetmind.domain.memory.embedder import EmbeddingError
from assetmind.providers.http import assert_allowed_url

GROQ_EMBEDDINGS_URL = "https://api.groq.com/openai/v1/embeddings"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text-v1.5"
_ALLOWED_HOSTS = {"api.groq.com"}


class GroqEmbedder:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_EMBEDDING_MODEL,
        timeout: float = 8,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key or not model:
            raise ValueError("Groq embeddings require an API key and a model id.")
        self.api_key = api_key
        self.model = model
        self.name = f"groq:{model}"
        self.timeout = timeout
        self.prompt_tokens = 0
        self._client = client

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        assert_allowed_url(GROQ_EMBEDDINGS_URL, _ALLOWED_HOSTS)
        payload = {"model": self.model, "input": texts, "encoding_format": "float"}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            if self._client is None:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(GROQ_EMBEDDINGS_URL, json=payload, headers=headers)
            else:
                response = self._client.post(GROQ_EMBEDDINGS_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise EmbeddingError("Groq embeddings timed out.") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingError("Groq embeddings request failed.") from exc
        if response.status_code >= 400:
            raise EmbeddingError(f"Groq embeddings returned HTTP {response.status_code}.")
        try:
            vectors, prompt_tokens = parse_embeddings(response.json(), expected=len(texts))
        except (ValueError, TypeError) as exc:
            raise EmbeddingError("Groq embeddings returned an unreadable body.") from exc
        self.prompt_tokens = prompt_tokens
        return vectors


def parse_embeddings(payload: object, *, expected: int) -> tuple[list[list[float]], int]:
    if not isinstance(payload, dict):
        raise ValueError("Embedding response must be an object.")
    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError("Embedding response must contain one vector per input.")
    ordered: list[tuple[int, list[float]]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Embedding row must be an object.")
        index = row.get("index")
        raw = row.get("embedding")
        if not isinstance(index, int) or not isinstance(raw, list) or not raw:
            raise ValueError("Embedding row must include an index and a float vector.")
        ordered.append((index, [float(value) for value in raw]))
    ordered.sort(key=lambda item: item[0])
    vectors = [vector for _index, vector in ordered]
    width = len(vectors[0])
    if any(len(vector) != width for vector in vectors):
        raise ValueError("Embedding vectors must share one width.")
    usage = payload.get("usage")
    prompt_tokens = 0
    if isinstance(usage, dict) and isinstance(usage.get("prompt_tokens"), int):
        prompt_tokens = int(usage["prompt_tokens"])
    return vectors, prompt_tokens

"""Deterministic hashed embeddings for session retrieval.

The vectors are a local index. They do not call a model and they do not rank
financial relevance. Each token is hashed into one of 64 buckets, so the score
follows shared words. A paraphrase with no shared token scores zero. Two
different tokens can land in the same bucket. Cosine similarity only finds
earlier turns with similar words.
"""

import hashlib
import math
import re

DIMENSIONS = 64
_TOKEN = re.compile(r"[a-z0-9]{2,}")


def embed(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for token in _TOKEN.findall(text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        bucket = digest[0] % DIMENSIONS
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[bucket] += sign
    return _normalize(vector)


def cosine(left: list[float], right: list[float]) -> float:
    return sum(one * other for one, other in zip(left, right, strict=True))


def rank_documents(query: str, documents: list[str]) -> list[tuple[float, str]]:
    """Highest cosine first. Ties keep the original document order."""

    query_vector = embed(query)
    scored = [(cosine(query_vector, embed(document)), index, document) for index, document in enumerate(documents)]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [(score, document) for score, _index, document in scored]


def estimate_tokens(text: str) -> int:
    """Rough budget count. Four characters stand in for one token."""

    return max(1, len(text) // 4)


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]

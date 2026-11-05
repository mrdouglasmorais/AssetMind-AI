"""SQLite vector index for one chat session.

Each turn is chunked. Retrieval embeds the question with the same embedder
that wrote the chunks and keeps the result inside a token budget. A model
failure falls back to the hashed index so the turn is still stored.
"""

import json
import sqlite3
import threading
from datetime import UTC, datetime

from assetmind.domain.errors import BudgetExceededError
from assetmind.domain.memory.chunks import chunk_text
from assetmind.domain.memory.embedder import HASHED_EMBEDDER, EmbeddingError, HashedEmbedder, TextEmbedder
from assetmind.domain.memory.vectors import cosine, embed, estimate_tokens


class SessionVectorStore:
    def __init__(
        self,
        path: str,
        *,
        token_budget: int = 600,
        embedder: TextEmbedder | None = None,
    ) -> None:
        self.path = path
        self.token_budget = token_budget
        self._embedder = embedder or HashedEmbedder()
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS session_vectors (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                symbols TEXT NOT NULL,
                vector TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {str(row[1]) for row in self._connection.execute("PRAGMA table_info(session_vectors)")}
        if "chunk_index" not in columns:
            self._connection.execute("ALTER TABLE session_vectors ADD COLUMN chunk_index INTEGER NOT NULL DEFAULT 0")
        if "embedder" not in columns:
            self._connection.execute(
                "ALTER TABLE session_vectors ADD COLUMN embedder TEXT NOT NULL DEFAULT 'hashed-64'"
            )
        self._connection.execute("CREATE INDEX IF NOT EXISTS session_vectors_session ON session_vectors(session_id)")
        self._connection.commit()

    def remember(self, session_id: str, role: str, text: str, symbols: list[str]) -> None:
        chunks = chunk_text(text)
        if not chunks:
            return
        embedder_name, vectors = self._vectors(chunks)
        created_at = datetime.now(UTC).isoformat()
        rows = [
            (session_id, role, chunk, json.dumps(symbols), json.dumps(vector), created_at, index, embedder_name)
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        with self._lock:
            self._connection.executemany(
                """
                INSERT INTO session_vectors
                    (session_id, role, text, symbols, vector, created_at, chunk_index, embedder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self._connection.commit()

    def first_user_text(self, session_id: str) -> str | None:
        row = self._connection.execute(
            """
            SELECT text FROM session_vectors
            WHERE session_id = ? AND role = 'user'
            ORDER BY id ASC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def latest_symbols(self, session_id: str) -> list[str]:
        row = self._connection.execute(
            """
            SELECT symbols FROM session_vectors
            WHERE session_id = ? AND symbols != '[]'
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return []
        loaded = json.loads(str(row[0]))
        if not isinstance(loaded, list):
            return []
        return [str(item) for item in loaded]

    def recall(self, session_id: str, query: str, *, limit: int = 4) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT role, text, vector, embedder FROM session_vectors
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
        if not rows:
            return []
        query_name, query_vectors = self._vectors([query])
        query_vector = query_vectors[0]
        comparable = [
            (str(role), str(text), json.loads(str(vector)))
            for role, text, vector, embedder_name in rows
            if str(embedder_name) == query_name
        ]
        ranked = sorted(
            (
                (cosine(query_vector, vector), role, text)
                for role, text, vector in comparable
                if len(vector) == len(query_vector)
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        first = next((str(text) for role, text, _vector, _name in rows if role == "user"), None)
        chosen: list[str] = []
        used = 0
        if first is not None:
            snippet = f"primeira pergunta: {first}"
            chosen.append(snippet)
            used += estimate_tokens(snippet)
        for _score, role, text in ranked[:limit]:
            line = f"{role}: {text}"
            if line in chosen or f"primeira pergunta: {text}" in chosen:
                continue
            cost = estimate_tokens(line)
            if used + cost > self.token_budget:
                break
            chosen.append(line)
            used += cost
        if not chosen:
            return []
        symbols = ", ".join(self.latest_symbols(session_id)) or "nenhum"
        body = "\n".join(chosen)
        return [
            {
                "memoria": body,
                "ativos_recentes": symbols,
                "tokens_estimados": str(used),
                "orcamento_tokens": str(self.token_budget),
            }
        ]

    def _vectors(self, texts: list[str]) -> tuple[str, list[list[float]]]:
        try:
            vectors = self._embedder.embed_many(texts)
        except (EmbeddingError, BudgetExceededError):
            vectors = []
        if len(vectors) == len(texts) and vectors and all(vector for vector in vectors):
            width = len(vectors[0])
            if all(len(vector) == width for vector in vectors):
                return self._embedder.name, vectors
        return HASHED_EMBEDDER, [embed(text) for text in texts]

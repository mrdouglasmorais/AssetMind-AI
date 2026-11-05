"""SQLite vector index for one chat session.

Brute-force cosine search is enough for a short conversation. The retrieved
text is capped by an estimated token budget so a later model call does not
replay full reports.
"""

import json
import sqlite3
import threading
from datetime import UTC, datetime

from assetmind.domain.memory.vectors import cosine, embed, estimate_tokens


class SessionVectorStore:
    def __init__(self, path: str, *, token_budget: int = 600) -> None:
        self.path = path
        self.token_budget = token_budget
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
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS session_vectors_session ON session_vectors(session_id)"
        )
        self._connection.commit()

    def remember(self, session_id: str, role: str, text: str, symbols: list[str]) -> None:
        compact = " ".join(text.split())
        if not compact:
            return
        payload = (
            session_id,
            role,
            compact[:500],
            json.dumps(symbols),
            json.dumps(embed(compact)),
            datetime.now(UTC).isoformat(),
        )
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO session_vectors (session_id, role, text, symbols, vector, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                payload,
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
            SELECT role, text, vector FROM session_vectors
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
        if not rows:
            return []
        query_vector = embed(query)
        ranked = sorted(
            ((cosine(query_vector, json.loads(str(vector))), str(role), str(text)) for role, text, vector in rows),
            key=lambda item: item[0],
            reverse=True,
        )
        first = next((text for role, text, _vector in rows if role == "user"), None)
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

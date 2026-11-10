"""PostgreSQL-backed job queue with lease fencing (ADR 0024)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from assetmind.persistence.tables import AnalysisJobRow


class StoredJob(BaseModel):
    analysis_id: str
    status: str
    attempt_count: int
    max_attempts: int
    lease_owner: str | None
    lease_token: str | None
    lease_expires_at: datetime | None
    available_at: datetime
    last_error: str | None


@dataclass(slots=True)
class ClaimedJob:
    analysis_id: str
    lease_token: str
    attempt_count: int
    max_attempts: int


def backoff_seconds(attempt_count: int) -> int:
    return min(300, 2 ** max(attempt_count, 1))


class JobRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def enqueue(
        self,
        *,
        analysis_id: str,
        now: datetime,
        max_attempts: int = 3,
    ) -> StoredJob:
        with self._session_factory() as session:
            row = AnalysisJobRow(
                analysis_id=analysis_id,
                status="queued",
                attempt_count=0,
                max_attempts=max_attempts,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                available_at=now,
                last_error=None,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            return _stored(row)

    def claim(
        self,
        *,
        worker_id: str,
        limit: int,
        lease_seconds: float,
        now: datetime | None = None,
    ) -> list[ClaimedJob]:
        moment = now or datetime.now(UTC)
        lease_until = moment + timedelta(seconds=lease_seconds)
        claimed: list[ClaimedJob] = []
        with self._session_factory() as session:
            dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
            if dialect == "postgresql":
                rows = self._claim_postgres(session, moment=moment, limit=limit)
            else:
                rows = self._claim_sqlite(session, moment=moment, limit=limit)
            for row in rows:
                token = uuid4().hex
                row.status = "leased"
                row.attempt_count += 1
                row.lease_owner = worker_id
                row.lease_token = token
                row.lease_expires_at = lease_until
                row.updated_at = moment
                claimed.append(
                    ClaimedJob(
                        analysis_id=row.analysis_id,
                        lease_token=token,
                        attempt_count=row.attempt_count,
                        max_attempts=row.max_attempts,
                    )
                )
            session.commit()
        return claimed

    def heartbeat(
        self,
        *,
        analysis_id: str,
        lease_token: str,
        lease_seconds: float,
        now: datetime | None = None,
    ) -> bool:
        moment = now or datetime.now(UTC)
        with self._session_factory() as session:
            result = session.execute(
                update(AnalysisJobRow)
                .where(
                    AnalysisJobRow.analysis_id == analysis_id,
                    AnalysisJobRow.lease_token == lease_token,
                    AnalysisJobRow.status == "leased",
                )
                .values(
                    lease_expires_at=moment + timedelta(seconds=lease_seconds),
                    updated_at=moment,
                )
            )
            session.commit()
            return int(getattr(result, "rowcount", 0) or 0) > 0

    def complete(
        self,
        *,
        analysis_id: str,
        lease_token: str,
        now: datetime | None = None,
    ) -> bool:
        moment = now or datetime.now(UTC)
        with self._session_factory() as session:
            result = session.execute(
                update(AnalysisJobRow)
                .where(
                    AnalysisJobRow.analysis_id == analysis_id,
                    AnalysisJobRow.lease_token == lease_token,
                    AnalysisJobRow.status == "leased",
                )
                .values(
                    status="completed",
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    last_error=None,
                    updated_at=moment,
                )
            )
            session.commit()
            return int(getattr(result, "rowcount", 0) or 0) > 0

    def fail(
        self,
        *,
        analysis_id: str,
        lease_token: str,
        error: str,
        now: datetime | None = None,
    ) -> str:
        """Return the resulting job status: queued, dead, or leased (if fencing lost)."""

        moment = now or datetime.now(UTC)
        with self._session_factory() as session:
            row = session.get(AnalysisJobRow, analysis_id)
            if row is None or row.lease_token != lease_token or row.status != "leased":
                return "fencing_lost"
            row.last_error = error[:2000]
            row.updated_at = moment
            if row.attempt_count >= row.max_attempts:
                row.status = "dead"
                row.lease_owner = None
                row.lease_token = None
                row.lease_expires_at = None
            else:
                row.status = "queued"
                row.lease_owner = None
                row.lease_token = None
                row.lease_expires_at = None
                row.available_at = moment + timedelta(seconds=backoff_seconds(row.attempt_count))
            status = row.status
            session.commit()
            return status

    def pending_counts(self) -> dict[str, int]:
        with self._session_factory() as session:
            rows = session.scalars(select(AnalysisJobRow)).all()
        counts = {"queued": 0, "leased": 0, "completed": 0, "dead": 0}
        for row in rows:
            if row.status in counts:
                counts[row.status] += 1
        return counts

    def _claim_postgres(
        self,
        session: Session,
        *,
        moment: datetime,
        limit: int,
    ) -> list[AnalysisJobRow]:
        statement = (
            select(AnalysisJobRow)
            .where(
                AnalysisJobRow.available_at <= moment,
                or_(
                    AnalysisJobRow.status == "queued",
                    and_(
                        AnalysisJobRow.status == "leased",
                        AnalysisJobRow.lease_expires_at.is_not(None),
                        AnalysisJobRow.lease_expires_at < moment,
                    ),
                ),
            )
            .order_by(AnalysisJobRow.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(session.scalars(statement))

    def _claim_sqlite(
        self,
        session: Session,
        *,
        moment: datetime,
        limit: int,
    ) -> list[AnalysisJobRow]:
        # SQLite lacks SKIP LOCKED; tests run single-threaded so a plain select is enough.
        statement = (
            select(AnalysisJobRow)
            .where(
                AnalysisJobRow.available_at <= moment,
                or_(
                    AnalysisJobRow.status == "queued",
                    and_(
                        AnalysisJobRow.status == "leased",
                        AnalysisJobRow.lease_expires_at.is_not(None),
                        AnalysisJobRow.lease_expires_at < moment,
                    ),
                ),
            )
            .order_by(AnalysisJobRow.created_at)
            .limit(limit)
        )
        return list(session.scalars(statement))


def _stored(row: AnalysisJobRow) -> StoredJob:
    return StoredJob(
        analysis_id=row.analysis_id,
        status=row.status,
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        lease_owner=row.lease_owner,
        lease_token=row.lease_token,
        lease_expires_at=row.lease_expires_at,
        available_at=row.available_at,
        last_error=row.last_error,
    )


def reclaim_expired_leases(session_factory: sessionmaker[Session], *, now: datetime | None = None) -> int:
    """Best-effort reclaim for operators; claim() already reclaims expired leases."""

    moment = now or datetime.now(UTC)
    with session_factory() as session:
        result = session.execute(
            text(
                """
                UPDATE analysis_jobs
                SET status = 'queued', lease_owner = NULL, lease_token = NULL,
                    lease_expires_at = NULL, updated_at = :now
                WHERE status = 'leased' AND lease_expires_at IS NOT NULL AND lease_expires_at < :now
                """
            ),
            {"now": moment},
        )
        session.commit()
        return int(getattr(result, "rowcount", 0) or 0)

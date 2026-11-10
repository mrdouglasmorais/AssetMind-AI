from datetime import UTC, datetime, timedelta
from pathlib import Path

from assetmind.persistence.db import create_db_engine, create_schema, create_session_factory
from assetmind.persistence.jobs import JobRepository, backoff_seconds
from assetmind.persistence.repository import AnalysisRepository


def _repos(tmp_path: Path) -> tuple[AnalysisRepository, JobRepository]:
    engine = create_db_engine(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    create_schema(engine)
    factory = create_session_factory(engine)
    return AnalysisRepository(factory), JobRepository(factory)


def test_backoff_grows_and_caps() -> None:
    assert backoff_seconds(1) == 2
    assert backoff_seconds(8) == 256
    assert backoff_seconds(20) == 300


def test_claim_complete_and_fencing(tmp_path: Path) -> None:
    analyses, jobs = _repos(tmp_path)
    now = datetime.now(UTC)
    analyses.create(analysis_id="a1", correlation_id="c1", request_json="{}", now=now)
    jobs.enqueue(analysis_id="a1", now=now, max_attempts=3)
    claimed = jobs.claim(worker_id="w1", limit=1, lease_seconds=30, now=now)
    assert len(claimed) == 1
    token = claimed[0].lease_token
    assert jobs.complete(analysis_id="a1", lease_token="wrong", now=now) is False
    assert jobs.complete(analysis_id="a1", lease_token=token, now=now) is True
    assert jobs.pending_counts()["completed"] == 1


def test_fail_retries_then_dead(tmp_path: Path) -> None:
    analyses, jobs = _repos(tmp_path)
    now = datetime.now(UTC)
    analyses.create(analysis_id="a2", correlation_id="c2", request_json="{}", now=now)
    jobs.enqueue(analysis_id="a2", now=now, max_attempts=2)
    first = jobs.claim(worker_id="w1", limit=1, lease_seconds=30, now=now)[0]
    assert jobs.fail(analysis_id="a2", lease_token=first.lease_token, error="boom", now=now) == "queued"
    later = now + timedelta(seconds=10)
    second = jobs.claim(worker_id="w1", limit=1, lease_seconds=30, now=later)[0]
    assert second.attempt_count == 2
    assert jobs.fail(analysis_id="a2", lease_token=second.lease_token, error="boom", now=later) == "dead"
    assert jobs.pending_counts()["dead"] == 1

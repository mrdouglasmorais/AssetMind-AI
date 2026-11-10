import asyncio
from pathlib import Path

import pytest

from assetmind.config.settings import Settings
from assetmind.worker import WorkerConfig, check_database, load_worker_config, run_worker


def test_load_worker_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSETMIND_WORKER_CONCURRENCY", raising=False)
    monkeypatch.delenv("ASSETMIND_JOB_QUEUE_ENABLED", raising=False)
    cfg = load_worker_config()
    assert cfg.concurrency == 1
    assert cfg.queue_enabled is False


def test_check_database_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "worker.db"
    monkeypatch.setenv("ASSETMIND_DATABASE_URL", f"sqlite+pysqlite:///{db}")
    check_database(Settings())


@pytest.mark.asyncio
async def test_run_worker_idle_then_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "worker.db"
    monkeypatch.setenv("ASSETMIND_DATABASE_URL", f"sqlite+pysqlite:///{db}")
    stop = asyncio.Event()
    cfg = WorkerConfig(
        worker_id="test-worker",
        poll_interval_seconds=0.05,
        concurrency=1,
        queue_enabled=False,
    )

    async def _stop_soon() -> None:
        await asyncio.sleep(0.02)
        stop.set()

    await asyncio.gather(
        run_worker(cfg, stop_event=stop, install_signals=False),
        _stop_soon(),
    )

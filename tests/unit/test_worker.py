import asyncio
from pathlib import Path

import pytest

from assetmind.config.settings import Settings
from assetmind.worker import WorkerConfig, check_database, load_worker_config, run_worker


def test_load_worker_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSETMIND_WORKER_CONCURRENCY", raising=False)
    monkeypatch.delenv("ASSETMIND_JOB_QUEUE_ENABLED", raising=False)
    cfg = load_worker_config(Settings(job_queue_enabled=False, worker_concurrency=1))
    assert cfg.concurrency == 1
    assert cfg.queue_enabled is False


def test_check_database_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "worker.db"
    monkeypatch.setenv("ASSETMIND_DATABASE_URL", f"sqlite+pysqlite:///{db}")
    check_database(Settings(database_url=f"sqlite+pysqlite:///{db}"))


@pytest.mark.asyncio
async def test_run_worker_idle_then_stop(tmp_path: Path) -> None:
    db = tmp_path / "worker.db"
    stop = asyncio.Event()
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{db}",
        job_queue_enabled=False,
        provider_mode="fixtures",
        api_key="test",
    )
    cfg = WorkerConfig(
        worker_id="test-worker",
        poll_interval_seconds=0.05,
        concurrency=1,
        queue_enabled=False,
        lease_seconds=30,
        deadline_seconds=5,
    )

    async def _stop_soon() -> None:
        await asyncio.sleep(0.02)
        stop.set()

    await asyncio.gather(
        run_worker(cfg, stop_event=stop, install_signals=False, settings=settings),
        _stop_soon(),
    )


@pytest.mark.asyncio
async def test_run_worker_processes_queued_job(tmp_path: Path) -> None:
    db = tmp_path / "queue.db"
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{db}",
        job_queue_enabled=True,
        provider_mode="fixtures",
        api_key="test",
        worker_concurrency=1,
        worker_poll_seconds=0.05,
        worker_lease_seconds=30,
        deadline_seconds=10,
        job_max_attempts=3,
    )
    from assetmind.api.app import create_app
    from assetmind.application.service import AnalysisService
    from assetmind.domain.assets.identity import AssetRequest

    app = create_app(settings)
    service: AnalysisService = app.state.service
    queued = service.enqueue(
        assets=[AssetRequest(symbol="PETR4")],
        scenarios=None,
        correlation_id="corr-worker",
        as_of=None,
    )
    assert queued.status == "queued"

    stop = asyncio.Event()

    async def _stop_after_work() -> None:
        for _ in range(40):
            stored = app.state.repository.get(queued.id)
            if stored and stored.status in {"completed", "partial", "failed"}:
                stop.set()
                return
            await asyncio.sleep(0.05)
        stop.set()

    await asyncio.gather(
        run_worker(
            WorkerConfig(
                worker_id="w-test",
                poll_interval_seconds=0.05,
                concurrency=1,
                queue_enabled=True,
                lease_seconds=30,
                deadline_seconds=10,
            ),
            stop_event=stop,
            install_signals=False,
            settings=settings,
        ),
        _stop_after_work(),
    )
    final = app.state.repository.get(queued.id)
    assert final is not None
    assert final.status in {"completed", "partial"}

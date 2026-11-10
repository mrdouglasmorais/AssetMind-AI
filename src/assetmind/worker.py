"""Background worker process for durable analysis jobs.

Phase 2 ships an idle-capable process that verifies database connectivity and
emits heartbeats. Phase 3 adds claim/lease/retry against PostgreSQL. Until then
HTTP requests still execute analyses in-process (ADR 0017).
"""

from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass

from assetmind.config.settings import Settings
from assetmind.observability.logging import configure_logging, log_event
from assetmind.persistence.db import create_db_engine, ping


@dataclass(slots=True)
class WorkerConfig:
    worker_id: str
    poll_interval_seconds: float
    concurrency: int
    queue_enabled: bool


def load_worker_config() -> WorkerConfig:
    return WorkerConfig(
        worker_id=os.environ.get("ASSETMIND_WORKER_ID", "worker-1"),
        poll_interval_seconds=float(os.environ.get("ASSETMIND_WORKER_POLL_SECONDS", "5")),
        concurrency=max(1, int(os.environ.get("ASSETMIND_WORKER_CONCURRENCY", "1"))),
        queue_enabled=os.environ.get("ASSETMIND_JOB_QUEUE_ENABLED", "false").lower() in {"1", "true", "yes"},
    )


def check_database(settings: Settings | None = None) -> None:
    runtime = settings or Settings()
    engine = create_db_engine(runtime.database_url)
    try:
        ping(engine)
    finally:
        engine.dispose()


async def run_worker(
    config: WorkerConfig | None = None,
    *,
    stop_event: asyncio.Event | None = None,
    install_signals: bool = True,
) -> None:
    logger = configure_logging()
    cfg = config or load_worker_config()
    stop = stop_event or asyncio.Event()

    def _stop(*_: object) -> None:
        stop.set()

    if install_signals:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _stop)
            except NotImplementedError:
                signal.signal(sig, lambda *_args: _stop())

    await asyncio.to_thread(check_database)
    log_event(
        logger,
        "worker_started",
        worker_id=cfg.worker_id,
        concurrency=cfg.concurrency,
        queue_enabled=cfg.queue_enabled,
        role="worker",
    )

    while not stop.is_set():
        if cfg.queue_enabled:
            log_event(
                logger,
                "worker_queue_not_implemented",
                worker_id=cfg.worker_id,
                hint="Phase 3 durable job claim is not enabled yet",
            )
        else:
            log_event(
                logger,
                "worker_idle",
                worker_id=cfg.worker_id,
                queue_enabled=False,
            )
        try:
            await asyncio.wait_for(stop.wait(), timeout=cfg.poll_interval_seconds)
        except TimeoutError:
            continue

    log_event(logger, "worker_stopped", worker_id=cfg.worker_id)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

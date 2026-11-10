"""Background worker process for durable analysis jobs (ADR 0024)."""

from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass

import httpx

from assetmind.application.budget import BudgetManager
from assetmind.application.service import AnalysisService
from assetmind.config.settings import Settings
from assetmind.domain.errors import DomainError
from assetmind.observability.logging import configure_logging, log_event
from assetmind.persistence.db import create_db_engine, create_schema, create_session_factory, ping
from assetmind.persistence.jobs import JobRepository
from assetmind.persistence.repository import AnalysisRepository
from assetmind.providers.bcb import BancoCentralProvider
from assetmind.providers.brapi import BrapiProvider
from assetmind.providers.coingecko import CoinGeckoProvider
from assetmind.providers.cvm import CvmProvider
from assetmind.providers.fixtures import FixtureMacroProvider, FixtureMarketProvider
from assetmind.providers.registry import ProviderRegistry


@dataclass(slots=True)
class WorkerConfig:
    worker_id: str
    poll_interval_seconds: float
    concurrency: int
    queue_enabled: bool
    lease_seconds: float
    deadline_seconds: float


def load_worker_config(settings: Settings | None = None) -> WorkerConfig:
    runtime = settings or Settings()
    return WorkerConfig(
        worker_id=os.environ.get("ASSETMIND_WORKER_ID", "worker-1"),
        poll_interval_seconds=runtime.worker_poll_seconds,
        concurrency=max(1, runtime.worker_concurrency),
        queue_enabled=runtime.job_queue_enabled,
        lease_seconds=runtime.worker_lease_seconds,
        deadline_seconds=runtime.deadline_seconds,
    )


def check_database(settings: Settings | None = None) -> None:
    runtime = settings or Settings()
    engine = create_db_engine(runtime.database_url)
    try:
        ping(engine)
    finally:
        engine.dispose()


def build_worker_service(
    settings: Settings,
    *,
    http_client: httpx.AsyncClient,
) -> tuple[AnalysisService, JobRepository, object]:
    engine = create_db_engine(settings.database_url)
    create_schema(engine)
    session_factory = create_session_factory(engine)
    repository = AnalysisRepository(session_factory)
    jobs = JobRepository(session_factory)
    logger = configure_logging()

    def registry_factory(budget: BudgetManager) -> ProviderRegistry:
        if settings.provider_mode == "fixtures":
            market = FixtureMarketProvider()
            return ProviderRegistry(
                brapi=market,
                coingecko=market,
                bcb=FixtureMacroProvider(),
                cvm=CvmProvider(use_fixtures=True),
                budget=budget,
            )
        return ProviderRegistry(
            brapi=BrapiProvider(
                http_client,
                base_url=settings.brapi_base_url,
                api_key=settings.brapi_api_key,
                timeout=settings.provider_timeout_seconds,
                max_retries=settings.max_provider_retries,
            ),
            coingecko=CoinGeckoProvider(
                http_client,
                base_url=settings.coingecko_base_url,
                api_key=settings.coingecko_api_key,
                timeout=settings.provider_timeout_seconds,
                max_retries=settings.max_provider_retries,
            ),
            bcb=BancoCentralProvider(
                http_client,
                base_url=settings.bcb_base_url,
                timeout=settings.provider_timeout_seconds,
                max_retries=settings.max_provider_retries,
            ),
            cvm=CvmProvider(use_fixtures=False),
            budget=budget,
        )

    def budget_factory(asset_count: int) -> BudgetManager:
        return BudgetManager(settings.budget_limits()).scaled_for_assets(asset_count)

    service = AnalysisService(
        repository,
        registry_factory,
        logger,
        budget_factory,
        jobs=jobs,
        job_queue_enabled=True,
        job_max_attempts=settings.job_max_attempts,
    )
    return service, jobs, engine


async def _heartbeat_loop(
    jobs: JobRepository,
    *,
    analysis_id: str,
    lease_token: str,
    lease_seconds: float,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=max(lease_seconds / 3, 5))
        except TimeoutError:
            if not jobs.heartbeat(
                analysis_id=analysis_id,
                lease_token=lease_token,
                lease_seconds=lease_seconds,
            ):
                return


async def process_one(
    service: AnalysisService,
    jobs: JobRepository,
    *,
    analysis_id: str,
    lease_token: str,
    worker_id: str,
    lease_seconds: float,
    deadline_seconds: float,
    logger: object,
) -> None:
    stop = asyncio.Event()
    beat = asyncio.create_task(
        _heartbeat_loop(
            jobs,
            analysis_id=analysis_id,
            lease_token=lease_token,
            lease_seconds=lease_seconds,
            stop=stop,
        )
    )
    try:
        await service.execute_claimed(
            analysis_id=analysis_id,
            lease_token=lease_token,
            deadline_seconds=deadline_seconds,
            worker_id=worker_id,
        )
    except Exception as exc:
        status = jobs.fail(
            analysis_id=analysis_id,
            lease_token=lease_token,
            error=str(exc),
        )
        log_event(
            logger,  # type: ignore[arg-type]
            "job_failed",
            analysis_id=analysis_id,
            job_id=analysis_id,
            worker_id=worker_id,
            error=str(exc),
            job_status=status,
        )
        if isinstance(exc, DomainError):
            return
        raise
    finally:
        stop.set()
        await beat


async def run_worker(
    config: WorkerConfig | None = None,
    *,
    stop_event: asyncio.Event | None = None,
    install_signals: bool = True,
    settings: Settings | None = None,
) -> None:
    logger = configure_logging()
    runtime = settings or Settings()
    cfg = config or load_worker_config(runtime)
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

    await asyncio.to_thread(check_database, runtime)
    log_event(
        logger,
        "worker_started",
        worker_id=cfg.worker_id,
        concurrency=cfg.concurrency,
        queue_enabled=cfg.queue_enabled,
        role="worker",
    )

    if not cfg.queue_enabled:
        while not stop.is_set():
            log_event(logger, "worker_idle", worker_id=cfg.worker_id, queue_enabled=False)
            try:
                await asyncio.wait_for(stop.wait(), timeout=cfg.poll_interval_seconds)
            except TimeoutError:
                continue
        log_event(logger, "worker_stopped", worker_id=cfg.worker_id)
        return

    async with httpx.AsyncClient() as http_client:
        service, jobs, engine = build_worker_service(runtime, http_client=http_client)
        try:
            while not stop.is_set():
                claimed = jobs.claim(
                    worker_id=cfg.worker_id,
                    limit=cfg.concurrency,
                    lease_seconds=cfg.lease_seconds,
                )
                if not claimed:
                    counts = jobs.pending_counts()
                    log_event(
                        logger,
                        "worker_idle",
                        worker_id=cfg.worker_id,
                        queue_enabled=True,
                        jobs_queued=counts["queued"],
                        jobs_leased=counts["leased"],
                    )
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=cfg.poll_interval_seconds)
                    except TimeoutError:
                        continue
                    continue
                for job in claimed:
                    log_event(
                        logger,
                        "job_claimed",
                        analysis_id=job.analysis_id,
                        job_id=job.analysis_id,
                        worker_id=cfg.worker_id,
                        attempt=job.attempt_count,
                    )
                    await process_one(
                        service,
                        jobs,
                        analysis_id=job.analysis_id,
                        lease_token=job.lease_token,
                        worker_id=cfg.worker_id,
                        lease_seconds=cfg.lease_seconds,
                        deadline_seconds=cfg.deadline_seconds,
                        logger=logger,
                    )
        finally:
            engine.dispose()  # type: ignore[attr-defined]

    log_event(logger, "worker_stopped", worker_id=cfg.worker_id)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

"""Use case that runs the Agno workflow and stores the result."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from assetmind.application.budget import BudgetManager
from assetmind.application.report import compose_report
from assetmind.application.state import RunState, StateMachine
from assetmind.domain.assets.identity import AssetRequest, resolve_asset
from assetmind.domain.errors import BudgetExceededError, DomainError
from assetmind.domain.scenarios.policy import ScenarioAssumptions, resolve_scenarios
from assetmind.observability.logging import log_event
from assetmind.persistence.jobs import JobRepository
from assetmind.persistence.repository import AnalysisRepository, StoredAnalysis
from assetmind.providers.registry import ProviderRegistry
from assetmind.workflows.analysis import build_analysis_workflow
from assetmind.workflows.context_store import RunContext, pop_run, register_run


class AnalysisService:
    def __init__(
        self,
        repository: AnalysisRepository,
        registry_factory: object,
        logger: object,
        budget_factory: object,
        jobs: JobRepository | None = None,
        *,
        job_queue_enabled: bool = False,
        job_max_attempts: int = 3,
    ) -> None:
        self.repository = repository
        self.registry_factory = registry_factory
        self.logger = logger
        self.budget_factory = budget_factory
        self.jobs = jobs
        self.job_queue_enabled = job_queue_enabled
        self.job_max_attempts = job_max_attempts
        self.workflow = build_analysis_workflow()

    async def run(
        self,
        *,
        assets: list[AssetRequest],
        scenarios: ScenarioAssumptions | None,
        correlation_id: str,
        as_of: datetime | None,
        deadline_seconds: float,
    ) -> StoredAnalysis:
        if self.job_queue_enabled:
            return self.enqueue(
                assets=assets,
                scenarios=scenarios,
                correlation_id=correlation_id,
                as_of=as_of,
            )
        return await self._run_inline(
            assets=assets,
            scenarios=scenarios,
            correlation_id=correlation_id,
            as_of=as_of,
            deadline_seconds=deadline_seconds,
        )

    def enqueue(
        self,
        *,
        assets: list[AssetRequest],
        scenarios: ScenarioAssumptions | None,
        correlation_id: str,
        as_of: datetime | None,
    ) -> StoredAnalysis:
        if self.jobs is None:
            raise DomainError("Job repository is not configured.")
        # Validate identity before accepting the job.
        for asset in assets:
            resolve_asset(asset)
        now = datetime.now(UTC)
        analysis_id = str(uuid4())
        request_json = _request_json(assets, scenarios, as_of=as_of)
        self.repository.create(
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            request_json=request_json,
            now=now,
            status="queued",
            message="Analysis queued for worker.",
        )
        self.jobs.enqueue(analysis_id=analysis_id, now=now, max_attempts=self.job_max_attempts)
        stored = self.repository.get(analysis_id)
        if stored is None:
            raise DomainError("Analysis was not stored.")
        log_event(
            self.logger,  # type: ignore[arg-type]
            "analysis_queued",
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            job_id=analysis_id,
        )
        return stored

    async def execute_claimed(
        self,
        *,
        analysis_id: str,
        lease_token: str,
        deadline_seconds: float,
        worker_id: str,
    ) -> StoredAnalysis:
        if self.jobs is None:
            raise DomainError("Job repository is not configured.")
        stored = self.repository.get(analysis_id)
        if stored is None:
            raise DomainError("Analysis was not stored.")
        if stored.status in {"completed", "partial", "failed", "cancelled"}:
            self.jobs.complete(analysis_id=analysis_id, lease_token=lease_token)
            return stored
        payload = json.loads(stored.request_json)
        assets = [AssetRequest.model_validate(item) for item in payload["assets"]]
        scenarios = None
        if payload.get("scenarios") is not None:
            scenarios = ScenarioAssumptions.model_validate(payload["scenarios"])
        as_of = None
        if payload.get("as_of") is not None:
            as_of = datetime.fromisoformat(payload["as_of"])
        result = await self._run_existing(
            analysis_id=analysis_id,
            correlation_id=stored.correlation_id,
            assets=assets,
            scenarios=scenarios,
            as_of=as_of,
            deadline_seconds=deadline_seconds,
            job_id=analysis_id,
            worker_id=worker_id,
        )
        outcome = self.jobs.complete(analysis_id=analysis_id, lease_token=lease_token)
        if not outcome:
            log_event(
                self.logger,  # type: ignore[arg-type]
                "job_fencing_lost_on_complete",
                analysis_id=analysis_id,
                job_id=analysis_id,
                worker_id=worker_id,
            )
        return result

    async def _run_inline(
        self,
        *,
        assets: list[AssetRequest],
        scenarios: ScenarioAssumptions | None,
        correlation_id: str,
        as_of: datetime | None,
        deadline_seconds: float,
    ) -> StoredAnalysis:
        now = datetime.now(UTC)
        analysis_id = str(uuid4())
        self.repository.create(
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            request_json=_request_json(assets, scenarios, as_of=as_of),
            now=now,
        )
        return await self._run_existing(
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            assets=assets,
            scenarios=scenarios,
            as_of=as_of,
            deadline_seconds=deadline_seconds,
            job_id=None,
            worker_id=None,
        )

    async def _run_existing(
        self,
        *,
        analysis_id: str,
        correlation_id: str,
        assets: list[AssetRequest],
        scenarios: ScenarioAssumptions | None,
        as_of: datetime | None,
        deadline_seconds: float,
        job_id: str | None,
        worker_id: str | None,
    ) -> StoredAnalysis:
        now = datetime.now(UTC)
        resolved = [resolve_asset(asset) for asset in assets]
        budget = self._budget(len(resolved))
        registry = self.registry_factory(budget)  # type: ignore[operator]
        if not isinstance(registry, ProviderRegistry):
            raise DomainError("Provider registry is not configured.")
        context = RunContext(
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            assets=resolved,
            scenarios=resolve_scenarios(scenarios),
            as_of=as_of,
            now=now,
            registry=registry,
            machine=StateMachine(),
            deadline=now + timedelta(seconds=deadline_seconds),
        )
        register_run(context)
        error_code = None
        if context.deadline is None:
            raise DomainError("Analysis deadline is not set.")
        registry.deadline = context.deadline
        try:
            remaining = max((context.deadline - datetime.now(UTC)).total_seconds(), 0)
            await asyncio.wait_for(self.workflow.arun(input=analysis_id), timeout=remaining)
        except TimeoutError:
            error_code = "deadline"
            context.partial_reasons.append("Deadline exceeded.")
        except (DomainError, BudgetExceededError) as exc:
            error_code = exc.code
            context.errors.append(exc.message)
        except Exception as exc:
            error_code = "internal"
            context.errors.append(exc.__class__.__name__)
        finally:
            self._close(context, error_code, budget)
            pop_run(analysis_id)
        stored = self.repository.get(analysis_id)
        if stored is None:
            raise DomainError("Analysis was not stored.")
        log_event(
            self.logger,  # type: ignore[arg-type]
            "analysis_finished",
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            job_id=job_id,
            worker_id=worker_id,
            workflow_name="assetmind-analysis",
            status=stored.status,
            provider_calls=budget.provider_calls,
            llm_calls=budget.llm_calls,
            estimated_cost_usd=budget.estimated_cost_usd,
        )
        return stored

    def _budget(self, asset_count: int) -> BudgetManager:
        budget = self.budget_factory(asset_count)  # type: ignore[operator]
        if not isinstance(budget, BudgetManager):
            raise DomainError("Budget manager is not configured.")
        return budget

    def _close(self, context: RunContext, error_code: str | None, budget: BudgetManager) -> None:
        if context.report is None:
            status = RunState.FAILED if not context.analyses else RunState.PARTIAL
            try:
                context.machine.finish(status)
            except Exception:
                status = RunState.FAILED
            context.report = compose_report(
                context.analyses,
                status=context.machine.state.value,
                composer="deterministic",
            )
        if context.report is not None:
            context.report = context.report.model_copy(update={"usage": budget.snapshot().model_dump()})
        self.repository.save_result(
            analysis_id=context.analysis_id,
            status=context.machine.state.value,
            report=context.report,
            analyses=context.analyses,
            usage=budget.snapshot(),
            error_code=error_code,
            now=datetime.now(UTC),
        )


def _request_json(
    assets: list[AssetRequest],
    scenarios: ScenarioAssumptions | None,
    *,
    as_of: datetime | None,
) -> str:
    payload = {
        "assets": [asset.model_dump(mode="json") for asset in assets],
        "scenarios": None if scenarios is None else scenarios.model_dump(mode="json"),
        "as_of": None if as_of is None else as_of.isoformat(),
    }
    return json.dumps(payload)

"""Use case that runs the Agno workflow and stores the result."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from assetmind.application.budget import BudgetManager
from assetmind.application.report import compose_report
from assetmind.application.state import RunState, StateMachine
from assetmind.domain.assets.identity import AssetRequest, resolve_asset
from assetmind.domain.errors import BudgetExceededError, DomainError
from assetmind.domain.scenarios.policy import ScenarioAssumptions, resolve_scenarios
from assetmind.observability.logging import log_event
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
    ) -> None:
        self.repository = repository
        self.registry_factory = registry_factory
        self.logger = logger
        self.budget_factory = budget_factory
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
        now = datetime.now(UTC)
        resolved = [resolve_asset(asset) for asset in assets]
        analysis_id = str(uuid4())
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
        self.repository.create(
            analysis_id=analysis_id,
            correlation_id=correlation_id,
            request_json=_request_json(assets, scenarios),
            now=now,
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


def _request_json(assets: list[AssetRequest], scenarios: ScenarioAssumptions | None) -> str:
    payload = {
        "assets": [asset.model_dump(mode="json") for asset in assets],
        "scenarios": None if scenarios is None else scenarios.model_dump(mode="json"),
    }
    import json

    return json.dumps(payload)

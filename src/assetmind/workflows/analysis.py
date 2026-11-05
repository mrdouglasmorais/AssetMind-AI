"""Agno workflow for a financial analysis.

Specialist stages are Python executors. The model is not asked to route, fetch,
or calculate. Agno 3.1.12 ``Workflow``, ``Step``, and ``Parallel`` are the
orchestration primitives actually used here.
"""

from datetime import UTC, datetime

from agno.workflow import Parallel, Step, StepInput, StepOutput, Workflow

from assetmind.application.report import compose_report
from assetmind.application.state import RunState
from assetmind.domain.analysis.engine import analyze_snapshot
from assetmind.domain.assets.identity import AssetClass
from assetmind.domain.errors import BudgetExceededError, DeadlineExceeded, DomainError
from assetmind.providers.errors import ProviderError
from assetmind.workflows.context_store import RunContext, get_run


def build_analysis_workflow() -> Workflow:
    # Agno 3.1.12 accepts these executors at runtime. Its published type aliases
    # are narrower than the constructors used by the official examples.
    specialists = Parallel(
        Step(name="specialist-equity", executor=fetch_equity),  # pyright: ignore[reportArgumentType]
        Step(name="specialist-crypto", executor=fetch_crypto),  # pyright: ignore[reportArgumentType]
        Step(name="specialist-real-estate", executor=fetch_real_estate),  # pyright: ignore[reportArgumentType]
        name="specialists",
    )
    return Workflow(  # pyright: ignore[reportArgumentType]
        name="assetmind-analysis",
        description="An orchestrator routes each asset to one specialist. Specialists calculate in Python.",
        telemetry=False,
        steps=[
            Step(name="validate", executor=validate_step),
            Step(name="orchestrate", executor=orchestrate_step),
            specialists,
            Step(name="analyze", executor=analyze_step),
            Step(name="verify", executor=verify_step),
            Step(name="report", executor=report_step),
        ],
    )


async def validate_step(step_input: StepInput) -> StepOutput:
    context = get_run(_analysis_id(step_input))
    _ensure_active(context)
    context.machine.move(RunState.VALIDATING)
    if not context.assets:
        context.errors.append("No assets resolved.")
        raise DomainError("No assets resolved.")
    return StepOutput(content={"assets": len(context.assets)})


async def orchestrate_step(step_input: StepInput) -> StepOutput:
    """Assign each asset to one specialist. Routing does not call a model."""

    context = get_run(_analysis_id(step_input))
    _ensure_active(context)
    context.machine.move(RunState.PLANNING)
    grouped: dict[str, list[str]] = {}
    for asset in context.assets:
        grouped.setdefault(asset.asset_class.value, []).append(asset.symbol)
    context.route = [f"{name}: {', '.join(symbols)}" for name, symbols in sorted(grouped.items())]
    context.route.append("narrator: optional single call over the metric card")
    context.machine.move(RunState.FETCHING)
    return StepOutput(content={"route": context.route})


async def fetch_equity(step_input: StepInput) -> StepOutput:
    return await _fetch_class(step_input, AssetClass.EQUITY)


async def fetch_crypto(step_input: StepInput) -> StepOutput:
    return await _fetch_class(step_input, AssetClass.CRYPTO)


async def fetch_real_estate(step_input: StepInput) -> StepOutput:
    return await _fetch_class(step_input, AssetClass.REAL_ESTATE)


async def analyze_step(step_input: StepInput) -> StepOutput:
    context = get_run(_analysis_id(step_input))
    _ensure_active(context)
    context.machine.move(RunState.ANALYZING)
    return StepOutput(content={"analyzed": len(context.analyses)})


async def verify_step(step_input: StepInput) -> StepOutput:
    context = get_run(_analysis_id(step_input))
    _ensure_active(context)
    context.machine.move(RunState.VERIFYING)
    approved = all(analysis.status != "failed" for analysis in context.analyses)
    return StepOutput(content={"approved": approved and not context.errors})


async def report_step(step_input: StepInput) -> StepOutput:
    context = get_run(_analysis_id(step_input))
    _ensure_active(context)
    status = _terminal_status(context)
    context.machine.move(status)
    context.report = compose_report(
        context.analyses,
        status=status.value,
        composer="deterministic",
        orchestration=context.route,
    )
    return StepOutput(content={"status": status.value})


async def _fetch_class(step_input: StepInput, asset_class: AssetClass) -> StepOutput:
    context = get_run(_analysis_id(step_input))
    selected = [asset for asset in context.assets if asset.asset_class is asset_class]
    if not selected:
        return StepOutput(content={"skipped": asset_class.value})
    produced = 0
    for asset in selected:
        _ensure_active(context)
        try:
            snapshot = await context.registry.fetch_asset(asset, as_of=context.as_of, now=context.now)
            analysis = analyze_snapshot(
                snapshot,
                scenarios=context.scenarios,
                now=context.now,
                as_of=context.as_of,
            )
        except (BudgetExceededError, DeadlineExceeded) as exc:
            context.partial_reasons.append(exc.message)
            break
        except ProviderError as exc:
            context.errors.append(f"{asset.symbol}: {exc.code}")
            from assetmind.domain.analysis.engine import AssetAnalysis

            analysis = AssetAnalysis(asset=asset, status="failed", uncertainties=[exc.message])
        with context.lock:
            context.analyses.append(analysis)
        produced += 1
    return StepOutput(content={"asset_class": asset_class.value, "produced": produced})


def _analysis_id(step_input: StepInput) -> str:
    if isinstance(step_input.input, str):
        return step_input.input
    raise DomainError("Workflow input must be the analysis id.")


def _ensure_active(context: RunContext) -> None:
    if context.deadline is not None and datetime.now(UTC) > context.deadline:
        context.partial_reasons.append("Deadline exceeded.")
        raise DeadlineExceeded("Deadline exceeded.")
    if context.cancelled:
        if context.machine.state is not RunState.CANCELLED:
            context.machine.move(RunState.CANCELLED)
        raise DomainError("Analysis cancelled.")


def _terminal_status(context: RunContext) -> RunState:
    if context.cancelled:
        return RunState.CANCELLED
    if not context.analyses:
        return RunState.FAILED
    if context.partial_reasons or context.errors or any(item.status != "completed" for item in context.analyses):
        if any(item.status in {"completed", "partial"} and item.metrics for item in context.analyses):
            return RunState.PARTIAL
        if any(item.metrics for item in context.analyses):
            return RunState.PARTIAL
        return RunState.FAILED
    return RunState.COMPLETED

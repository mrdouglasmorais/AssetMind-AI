"""In-process run context shared by workflow steps."""

import threading
from dataclasses import dataclass, field
from datetime import datetime

from assetmind.application.report import ReportDocument
from assetmind.application.state import StateMachine
from assetmind.domain.analysis.engine import AssetAnalysis
from assetmind.domain.assets.identity import ResolvedAsset
from assetmind.domain.scenarios.policy import ResolvedScenario
from assetmind.providers.registry import ProviderRegistry


@dataclass
class RunContext:
    analysis_id: str
    correlation_id: str
    assets: list[ResolvedAsset]
    scenarios: list[ResolvedScenario]
    as_of: datetime | None
    now: datetime
    registry: ProviderRegistry
    machine: StateMachine
    analyses: list[AssetAnalysis] = field(default_factory=list)
    partial_reasons: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    cancelled: bool = False
    deadline: datetime | None = None
    report: ReportDocument | None = None
    route: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


_RUNS: dict[str, RunContext] = {}


def register_run(context: RunContext) -> None:
    _RUNS[context.analysis_id] = context


def get_run(analysis_id: str) -> RunContext:
    try:
        return _RUNS[analysis_id]
    except KeyError as exc:
        raise KeyError(f"Unknown analysis run {analysis_id}.") from exc


def pop_run(analysis_id: str) -> RunContext | None:
    return _RUNS.pop(analysis_id, None)

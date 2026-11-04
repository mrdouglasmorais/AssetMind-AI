"""Deterministic evidence checks. Source text is data, never an instruction."""

import re
from collections import defaultdict

from pydantic import BaseModel, Field

from assetmind.domain.evidence.models import Evidence, QualityStatus

_INJECTION = re.compile(
    r"(ignore (all |any |previous )?instructions|system override|you are now|reveal the prompt)",
    re.IGNORECASE,
)
_RELATIVE_TOLERANCE = 0.01


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: str


class EvidenceValidation(BaseModel):
    evidence: list[Evidence]
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def approved(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def reconcile_evidence(evidence: list[Evidence]) -> EvidenceValidation:
    issues: list[ValidationIssue] = []
    updated = [item.model_copy() for item in evidence]
    for item in updated:
        if not item.provider:
            issues.append(
                ValidationIssue(
                    code="missing_provenance",
                    message=f"Metric {item.metric} has no provider.",
                    severity="error",
                )
            )
        if item.quality_status is QualityStatus.MISSING or item.value is None:
            if item.quality_status is not QualityStatus.NOT_APPLICABLE:
                issues.append(
                    ValidationIssue(
                        code="missing_value",
                        message=f"{item.metric} is missing and was not replaced with zero.",
                        severity="warning",
                    )
                )
        if _contains_injection(item.text_value):
            issues.append(
                ValidationIssue(
                    code="prompt_injection_excluded",
                    message=(
                        f"Instruction-like text in {item.metric} from {item.provider} "
                        "was kept as data and excluded from the narrative."
                    ),
                    severity="warning",
                )
            )

    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, item in enumerate(updated):
        if item.value is None or item.quality_status is QualityStatus.NOT_APPLICABLE:
            continue
        grouped[(item.asset_id, item.metric)].append(index)

    for (asset_id, metric), indexes in grouped.items():
        values = [updated[index].value for index in indexes if updated[index].value is not None]
        if len(values) < 2 or values[0] is None:
            continue
        baseline = values[0]
        if any(_conflicts(baseline, value) for value in values[1:] if value is not None):
            for index in indexes:
                updated[index] = updated[index].model_copy(update={"quality_status": QualityStatus.CONFLICTING})
            issues.append(
                ValidationIssue(
                    code="conflicting_sources",
                    message=f"{metric} for {asset_id} disagrees across sources and was not averaged.",
                    severity="error",
                )
            )

    return EvidenceValidation(evidence=updated, issues=issues)


def _conflicts(left: float, right: float) -> bool:
    scale = max(abs(left), abs(right), 1e-9)
    return abs(left - right) / scale > _RELATIVE_TOLERANCE


def _contains_injection(text: str | None) -> bool:
    return bool(text and _INJECTION.search(text))

"""Persistence for analysis requests, states, reports, evidence, and usage."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from assetmind.application.budget import BudgetSnapshot, TokenBalance
from assetmind.application.report import ReportDocument
from assetmind.domain.analysis.engine import AssetAnalysis
from assetmind.persistence.tables import AnalysisEventRow, AnalysisRow, EvidenceRow, UsageRow


class StoredAnalysis(BaseModel):
    id: str
    correlation_id: str
    status: str
    request_json: str
    report_json: str | None
    error_code: str | None


class StoredEvent(BaseModel):
    state: str
    message: str
    created_at: datetime


class AnalysisRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, *, analysis_id: str, correlation_id: str, request_json: str, now: datetime) -> None:
        with self._session_factory() as session:
            session.add(
                AnalysisRow(
                    id=analysis_id,
                    correlation_id=correlation_id,
                    status="created",
                    request_json=request_json,
                    report_json=None,
                    error_code=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                AnalysisEventRow(
                    analysis_id=analysis_id,
                    state="created",
                    message="Analysis created.",
                    created_at=now,
                )
            )
            session.commit()

    def add_event(self, analysis_id: str, state: str, message: str, now: datetime | None = None) -> None:
        with self._session_factory() as session:
            session.add(
                AnalysisEventRow(
                    analysis_id=analysis_id,
                    state=state,
                    message=message,
                    created_at=now or datetime.now(UTC),
                )
            )
            session.commit()

    def save_result(
        self,
        *,
        analysis_id: str,
        status: str,
        report: ReportDocument | None,
        analyses: list[AssetAnalysis],
        usage: BudgetSnapshot,
        error_code: str | None,
        now: datetime,
    ) -> None:
        with self._session_factory() as session:
            row = session.get(AnalysisRow, analysis_id)
            if row is None:
                raise KeyError(analysis_id)
            row.status = status
            row.report_json = report.model_dump_json() if report else None
            row.error_code = error_code
            row.updated_at = now
            session.add(
                AnalysisEventRow(
                    analysis_id=analysis_id,
                    state=status,
                    message=error_code or "Analysis finished.",
                    created_at=now,
                )
            )
            session.add(
                UsageRow(
                    analysis_id=analysis_id,
                    provider_calls=usage.provider_calls,
                    llm_calls=usage.llm_calls,
                    estimated_input_tokens=usage.estimated_input_tokens,
                    estimated_output_tokens=usage.estimated_output_tokens,
                    actual_input_tokens=usage.actual_input_tokens,
                    actual_output_tokens=usage.actual_output_tokens,
                    estimated_cost_usd=f"{usage.estimated_cost_usd:.8f}",
                    actual_cost_usd=None if usage.actual_cost_usd is None else f"{usage.actual_cost_usd:.8f}",
                )
            )
            for analysis in analyses:
                for evidence in analysis.evidence:
                    session.add(
                        EvidenceRow(
                            analysis_id=analysis_id,
                            provider=evidence.provider,
                            source_url=evidence.source_url,
                            asset_id=evidence.asset_id,
                            observed_at=evidence.observed_at,
                            retrieved_at=evidence.retrieved_at,
                            metric=evidence.metric,
                            value_text=None if evidence.value is None else str(evidence.value),
                            unit=evidence.unit,
                            currency=evidence.currency,
                            period=evidence.period,
                            quality_status=evidence.quality_status.value,
                        )
                    )
            session.commit()

    def record_usage(self, *, kind: str, usage: BudgetSnapshot) -> str:
        """Append one ledger row for a chat narration or an external lookup."""

        analysis_id = str(uuid4())
        now = datetime.now(UTC)
        self.create(
            analysis_id=analysis_id,
            correlation_id=kind[:64],
            request_json=json.dumps({"kind": kind}),
            now=now,
        )
        self.save_result(
            analysis_id=analysis_id,
            status="completed",
            report=None,
            analyses=[],
            usage=usage,
            error_code=None,
            now=now,
        )
        return analysis_id

    def token_balance(self, allowance_tokens: int) -> TokenBalance:
        with self._session_factory() as session:
            rows = session.scalars(select(UsageRow)).all()
        estimated_input = sum(row.estimated_input_tokens for row in rows)
        estimated_output = sum(row.estimated_output_tokens for row in rows)
        actual_input = sum(row.actual_input_tokens or 0 for row in rows)
        actual_output = sum(row.actual_output_tokens or 0 for row in rows)
        estimated_tokens = estimated_input + estimated_output
        estimated_cost = sum(float(row.estimated_cost_usd) for row in rows)
        return TokenBalance(
            analyses=len(rows),
            estimated_input_tokens=estimated_input,
            estimated_output_tokens=estimated_output,
            estimated_tokens=estimated_tokens,
            actual_input_tokens=actual_input,
            actual_output_tokens=actual_output,
            llm_calls=sum(row.llm_calls for row in rows),
            provider_calls=sum(row.provider_calls for row in rows),
            estimated_cost_usd=estimated_cost,
            allowance_tokens=allowance_tokens,
            remaining_tokens=max(0, allowance_tokens - estimated_tokens),
        )

    def get(self, analysis_id: str) -> StoredAnalysis | None:
        with self._session_factory() as session:
            row = session.get(AnalysisRow, analysis_id)
            if row is None:
                return None
            return StoredAnalysis(
                id=row.id,
                correlation_id=row.correlation_id,
                status=row.status,
                request_json=row.request_json,
                report_json=row.report_json,
                error_code=row.error_code,
            )

    def events(self, analysis_id: str) -> list[StoredEvent]:
        with self._session_factory() as session:
            statement = (
                select(AnalysisEventRow)
                .where(AnalysisEventRow.analysis_id == analysis_id)
                .order_by(AnalysisEventRow.id)
            )
            return [
                StoredEvent(state=row.state, message=row.message, created_at=row.created_at)
                for row in session.scalars(statement)
            ]

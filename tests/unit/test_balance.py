from assetmind.application.report import compose_report
from assetmind.domain.analysis.engine import AssetAnalysis
from assetmind.domain.assets.identity import AssetRequest, resolve_asset
from assetmind.persistence.db import create_db_engine, create_schema, create_session_factory
from assetmind.persistence.repository import AnalysisRepository
from assetmind.persistence.tables import UsageRow


def test_orchestration_groups_specialists_without_a_model() -> None:
    equity = AssetAnalysis(asset=resolve_asset(AssetRequest(symbol="PETR4")), status="completed")
    crypto = AssetAnalysis(asset=resolve_asset(AssetRequest(symbol="bitcoin")), status="completed")
    report = compose_report([equity, crypto], status="completed", composer="deterministic")
    assert report.orchestration == ["crypto: bitcoin", "equity: PETR4"]


def test_token_balance_keeps_estimated_spend_separate_from_actual(tmp_path: object) -> None:
    database = tmp_path / "usage.db"  # type: ignore[operator]
    engine = create_db_engine(f"sqlite+pysqlite:///{database}")
    create_schema(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        from datetime import UTC, datetime

        from assetmind.persistence.tables import AnalysisRow

        now = datetime.now(UTC)
        session.add(
            AnalysisRow(
                id="a1",
                correlation_id="c1",
                status="completed",
                request_json="{}",
                report_json=None,
                error_code=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UsageRow(
                analysis_id="a1",
                provider_calls=2,
                llm_calls=0,
                estimated_input_tokens=800,
                estimated_output_tokens=200,
                actual_input_tokens=None,
                actual_output_tokens=None,
                estimated_cost_usd="0.00024000",
                actual_cost_usd=None,
            )
        )
        session.commit()
    balance = AnalysisRepository(factory).token_balance(100_000)
    assert balance.estimated_tokens == 1000
    assert balance.actual_input_tokens == 0
    assert balance.remaining_tokens == 99_000
    assert balance.llm_calls == 0
    engine.dispose()

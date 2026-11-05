from types import SimpleNamespace

import pytest
from agno.exceptions import InputCheckError

from assetmind.agents.chat import _guard_narration, _record_narration
from assetmind.application.budget import BudgetManager, TokenBalance
from assetmind.config.settings import Settings
from assetmind.persistence.db import create_db_engine, create_schema, create_session_factory
from assetmind.persistence.repository import AnalysisRepository


def _balance(remaining: int) -> TokenBalance:
    return TokenBalance(
        analyses=0,
        estimated_input_tokens=0,
        estimated_output_tokens=0,
        estimated_tokens=0,
        actual_input_tokens=0,
        actual_output_tokens=0,
        llm_calls=0,
        provider_calls=0,
        estimated_cost_usd=0.0,
        allowance_tokens=100,
        remaining_tokens=remaining,
    )


def test_narration_is_refused_when_the_allowance_cannot_hold_it() -> None:
    class _Repository:
        def token_balance(self, allowance_tokens: int) -> TokenBalance:
            return _balance(10)

    settings = Settings(api_key="local", token_allowance=100, max_output_tokens=50, max_total_tokens=4000)
    guard = _guard_narration(SimpleNamespace(repository=_Repository()), settings)  # type: ignore[arg-type]
    with pytest.raises(InputCheckError, match="Token allowance exceeded"):
        guard(SimpleNamespace(input_content="analise PETR4"))


def test_narration_is_refused_when_the_call_cap_is_too_small() -> None:
    class _Repository:
        def token_balance(self, allowance_tokens: int) -> TokenBalance:
            return _balance(100_000)

    settings = Settings(api_key="local", max_output_tokens=50, max_total_tokens=20)
    guard = _guard_narration(SimpleNamespace(repository=_Repository()), settings)  # type: ignore[arg-type]
    with pytest.raises(InputCheckError, match="Total token budget exceeded"):
        guard(SimpleNamespace(input_content="analise PETR4"))


def test_a_finished_narration_is_written_to_the_ledger(tmp_path: object) -> None:
    database = tmp_path / "chat.db"  # type: ignore[operator]
    engine = create_db_engine(f"sqlite+pysqlite:///{database}")
    create_schema(engine)
    repository = AnalysisRepository(create_session_factory(engine))
    settings = Settings(api_key="local", max_output_tokens=20, max_total_tokens=4000)
    service = SimpleNamespace(repository=repository)
    record = _record_narration(service, settings)  # type: ignore[arg-type]
    record(
        SimpleNamespace(
            input=SimpleNamespace(input_content="analise PETR4"),
            metrics=SimpleNamespace(input_tokens=11, output_tokens=4),
        )
    )
    balance = repository.token_balance(100_000)
    assert balance.analyses == 1
    assert balance.llm_calls == 1
    assert balance.estimated_output_tokens == 20
    assert balance.actual_input_tokens == 11
    assert balance.actual_output_tokens == 4
    assert balance.remaining_tokens == 100_000 - balance.estimated_tokens
    engine.dispose()


def test_provider_probe_counts_one_call_and_no_model_tokens() -> None:
    manager = BudgetManager()
    manager.consume_provider_call()
    assert manager.snapshot().provider_calls == 1
    assert manager.snapshot().llm_calls == 0

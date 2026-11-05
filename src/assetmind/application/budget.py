"""Token, call, and estimated-cost budgets.

Defaults are engineering guardrails, not measured production targets.
Estimated usage and actual usage are stored separately.
"""

import threading

from pydantic import BaseModel, Field

from assetmind.domain.errors import BudgetExceededError


class BudgetLimits(BaseModel):
    max_total_tokens: int = 4000
    max_output_tokens: int = 1200
    max_llm_calls: int = 8
    max_provider_calls: int = 12
    max_estimated_cost_usd: float = 0.03
    max_tool_calls: int = 24
    input_cost_per_million: float = 0.15
    output_cost_per_million: float = 0.60


class BudgetSnapshot(BaseModel):
    provider_calls: int
    llm_calls: int
    tool_calls: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    actual_input_tokens: int | None = None
    actual_output_tokens: int | None = None
    estimated_cost_usd: float
    actual_cost_usd: float | None = None


class BudgetManager:
    def __init__(self, limits: BudgetLimits | None = None) -> None:
        self.limits = limits or BudgetLimits()
        self.provider_calls = 0
        self.llm_calls = 0
        self.tool_calls = 0
        self.estimated_input_tokens = 0
        self.estimated_output_tokens = 0
        self.actual_input_tokens: int | None = None
        self.actual_output_tokens: int | None = None
        self.estimated_cost_usd = 0.0
        self.actual_cost_usd: float | None = None
        self._lock = threading.Lock()

    def scaled_for_assets(self, asset_count: int) -> "BudgetManager":
        count = max(asset_count, 1)
        limits = self.limits.model_copy(
            update={
                "max_total_tokens": self.limits.max_total_tokens * count,
                "max_provider_calls": self.limits.max_provider_calls * count,
                "max_estimated_cost_usd": self.limits.max_estimated_cost_usd * count,
                "max_llm_calls": self.limits.max_llm_calls,
                "max_output_tokens": self.limits.max_output_tokens,
            }
        )
        return BudgetManager(limits)

    def consume_provider_call(self) -> None:
        with self._lock:
            if self.provider_calls >= self.limits.max_provider_calls:
                raise BudgetExceededError("Provider call budget exceeded.")
            self.provider_calls += 1

    def consume_tool_call(self) -> None:
        with self._lock:
            if self.tool_calls >= self.limits.max_tool_calls:
                raise BudgetExceededError("Tool call budget exceeded.")
            self.tool_calls += 1

    def authorize_llm_call(self, estimated_input_tokens: int, estimated_output_tokens: int) -> None:
        with self._lock:
            if estimated_output_tokens > self.limits.max_output_tokens:
                raise BudgetExceededError("Requested output exceeds the narrative token budget.")
            if self.llm_calls >= self.limits.max_llm_calls:
                raise BudgetExceededError("LLM call budget exceeded.")
            next_input = self.estimated_input_tokens + estimated_input_tokens
            next_output = self.estimated_output_tokens + estimated_output_tokens
            if next_input + next_output > self.limits.max_total_tokens:
                raise BudgetExceededError("Total token budget exceeded.")
            next_cost = _cost(
                next_input,
                next_output,
                self.limits.input_cost_per_million,
                self.limits.output_cost_per_million,
            )
            if next_cost > self.limits.max_estimated_cost_usd:
                raise BudgetExceededError("Estimated USD budget exceeded.")
            self.llm_calls += 1
            self.estimated_input_tokens = next_input
            self.estimated_output_tokens = next_output
            self.estimated_cost_usd = next_cost

    def record_actual_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.actual_input_tokens = (self.actual_input_tokens or 0) + input_tokens
        self.actual_output_tokens = (self.actual_output_tokens or 0) + output_tokens
        self.actual_cost_usd = _cost(
            self.actual_input_tokens,
            self.actual_output_tokens,
            self.limits.input_cost_per_million,
            self.limits.output_cost_per_million,
        )

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            provider_calls=self.provider_calls,
            llm_calls=self.llm_calls,
            tool_calls=self.tool_calls,
            estimated_input_tokens=self.estimated_input_tokens,
            estimated_output_tokens=self.estimated_output_tokens,
            actual_input_tokens=self.actual_input_tokens,
            actual_output_tokens=self.actual_output_tokens,
            estimated_cost_usd=self.estimated_cost_usd,
            actual_cost_usd=self.actual_cost_usd,
        )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def narration_snapshot(
    limits: BudgetLimits,
    text: str,
    output_tokens: int,
    *,
    actual_input_tokens: int = 0,
    actual_output_tokens: int = 0,
) -> BudgetSnapshot:
    """Reserve one narration. Actual tokens are recorded only when the run reports them."""

    manager = BudgetManager(limits)
    manager.authorize_llm_call(estimate_tokens(text), output_tokens)
    if actual_input_tokens or actual_output_tokens:
        manager.record_actual_usage(actual_input_tokens, actual_output_tokens)
    return manager.snapshot()


def provider_probe_snapshot() -> BudgetSnapshot:
    manager = BudgetManager()
    manager.consume_provider_call()
    return manager.snapshot()


def _cost(input_tokens: int, output_tokens: int, input_rate: float, output_rate: float) -> float:
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate


class UsageView(BaseModel):
    estimated: BudgetSnapshot
    note: str = Field(default="Estimated cost uses configured rates and is not an invoice from the model gateway.")


class TokenBalance(BaseModel):
    """Running ledger. Estimated and actual figures stay on separate fields."""

    analyses: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_tokens: int
    actual_input_tokens: int
    actual_output_tokens: int
    llm_calls: int
    provider_calls: int
    estimated_cost_usd: float
    allowance_tokens: int
    remaining_tokens: int
    note: str = "Remaining tokens use the estimated ledger. Actual tokens appear only after a provider reports them."


def assert_narration_allowed(
    limits: BudgetLimits,
    balance: TokenBalance,
    text: str,
    output_tokens: int,
) -> BudgetSnapshot:
    snapshot = narration_snapshot(limits, text, output_tokens)
    reserved = snapshot.estimated_input_tokens + snapshot.estimated_output_tokens
    if reserved > balance.remaining_tokens:
        raise BudgetExceededError("Token allowance exceeded.")
    return snapshot


def format_token_balance(balance: TokenBalance) -> str:
    return (
        f"Saldo de tokens: {balance.estimated_tokens} estimados em {balance.analyses} analises. "
        f"Restam {balance.remaining_tokens} de {balance.allowance_tokens}. "
        f"Modelo: {balance.llm_calls} chamadas. Provedores: {balance.provider_calls} chamadas. "
        f"Custo estimado: {balance.estimated_cost_usd:.6f} USD. {balance.note}"
    )

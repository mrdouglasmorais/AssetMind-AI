"""Runtime settings. Secrets come from the environment and are never logged."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from assetmind.application.budget import BudgetLimits


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    env: str = Field(default="development", validation_alias=AliasChoices("ASSETMIND_ENV"))
    database_url: str = Field(
        default="sqlite+pysqlite:///./assetmind.db",
        validation_alias=AliasChoices("ASSETMIND_DATABASE_URL", "DATABASE_URL"),
    )
    api_key: str | None = Field(default=None, validation_alias=AliasChoices("ASSETMIND_API_KEY"))
    cors_origins: str = Field(default="", validation_alias=AliasChoices("ASSETMIND_CORS_ORIGINS"))
    agentos_enabled: bool = Field(default=False, validation_alias=AliasChoices("ASSETMIND_AGENTOS_ENABLED"))
    agentos_jwt_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ASSETMIND_AGENTOS_JWT_SECRET"),
    )
    os_security_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ASSETMIND_OS_SECURITY_KEY", "OS_SECURITY_KEY"),
    )
    agent_ui_url: str = Field(
        default="http://127.0.0.1:3000",
        validation_alias=AliasChoices("ASSETMIND_AGENT_UI_URL"),
    )
    provider_mode: str = Field(default="live", validation_alias=AliasChoices("ASSETMIND_PROVIDER_MODE"))
    llm_provider: str = Field(default="groq", validation_alias=AliasChoices("ASSETMIND_LLM_PROVIDER"))
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "ASSETMIND_GROQ_API_KEY"),
    )
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        validation_alias=AliasChoices("ASSETMIND_GROQ_MODEL"),
    )
    embedding_provider: str = Field(
        default="hashed",
        validation_alias=AliasChoices("ASSETMIND_EMBEDDING_PROVIDER"),
    )
    embedding_model: str = Field(
        default="nomic-embed-text-v1.5",
        validation_alias=AliasChoices("ASSETMIND_EMBEDDING_MODEL"),
    )
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "ASSETMIND_OPENROUTER_API_KEY"),
    )
    openrouter_model: str = Field(
        default="",
        validation_alias=AliasChoices("ASSETMIND_OPENROUTER_MODEL"),
    )
    brapi_api_key: str | None = Field(default=None, validation_alias=AliasChoices("BRAPI_API_KEY"))
    brapi_base_url: str = Field(
        default="https://brapi.dev",
        validation_alias=AliasChoices("ASSETMIND_BRAPI_BASE_URL"),
    )
    coingecko_base_url: str = Field(
        default="https://api.coingecko.com/api/v3",
        validation_alias=AliasChoices("ASSETMIND_COINGECKO_BASE_URL"),
    )
    coingecko_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("COINGECKO_API_KEY"),
    )
    bcb_base_url: str = Field(
        default="https://api.bcb.gov.br",
        validation_alias=AliasChoices("ASSETMIND_BCB_BASE_URL"),
    )
    skills_dir: str = Field(default="skills", validation_alias=AliasChoices("ASSETMIND_SKILLS_DIR"))
    token_allowance: int = Field(default=100_000, validation_alias="ASSETMIND_TOKEN_ALLOWANCE")
    max_total_tokens: int = Field(default=4000, validation_alias="ASSETMIND_MAX_TOTAL_TOKENS")
    max_output_tokens: int = Field(default=1200, validation_alias="ASSETMIND_MAX_OUTPUT_TOKENS")
    max_llm_calls: int = Field(default=8, validation_alias="ASSETMIND_MAX_LLM_CALLS")
    max_provider_calls: int = Field(default=12, validation_alias="ASSETMIND_MAX_PROVIDER_CALLS")
    max_estimated_cost_usd: float = Field(default=0.03, validation_alias="ASSETMIND_MAX_ESTIMATED_COST_USD")
    max_tool_calls: int = Field(default=24, validation_alias="ASSETMIND_MAX_TOOL_CALLS")
    deadline_seconds: float = Field(default=25, validation_alias="ASSETMIND_DEADLINE_SECONDS")
    provider_timeout_seconds: float = Field(default=8, validation_alias="ASSETMIND_PROVIDER_TIMEOUT_SECONDS")
    max_provider_retries: int = Field(default=2, validation_alias="ASSETMIND_MAX_PROVIDER_RETRIES")
    rate_limit_per_minute: int = Field(default=30, validation_alias="ASSETMIND_RATE_LIMIT_PER_MINUTE")
    max_assets: int = Field(default=5, validation_alias="ASSETMIND_MAX_ASSETS")
    input_cost_per_million: float = Field(default=0.15, validation_alias="ASSETMIND_INPUT_COST_PER_MILLION")
    output_cost_per_million: float = Field(
        default=0.60,
        validation_alias="ASSETMIND_OUTPUT_COST_PER_MILLION",
    )

    @field_validator("provider_mode")
    @classmethod
    def _provider_mode(cls, value: str) -> str:
        if value not in {"live", "fixtures"}:
            raise ValueError("ASSETMIND_PROVIDER_MODE must be live or fixtures.")
        return value

    @field_validator("llm_provider")
    @classmethod
    def _llm_provider(cls, value: str) -> str:
        if value not in {"groq", "openrouter"}:
            raise ValueError("ASSETMIND_LLM_PROVIDER must be groq or openrouter.")
        return value

    @field_validator("embedding_provider")
    @classmethod
    def _embedding_provider(cls, value: str) -> str:
        if value not in {"hashed", "groq"}:
            raise ValueError("ASSETMIND_EMBEDDING_PROVIDER must be hashed or groq.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def budget_limits(self) -> BudgetLimits:
        return BudgetLimits(
            max_total_tokens=self.max_total_tokens,
            max_output_tokens=self.max_output_tokens,
            max_llm_calls=self.max_llm_calls,
            max_provider_calls=self.max_provider_calls,
            max_estimated_cost_usd=self.max_estimated_cost_usd,
            max_tool_calls=self.max_tool_calls,
            input_cost_per_million=self.input_cost_per_million,
            output_cost_per_million=self.output_cost_per_million,
        )

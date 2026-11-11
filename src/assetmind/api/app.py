"""FastAPI application. AgentOS is mounted only when explicitly enabled."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from scalar_fastapi import add_scalar_reference

from assetmind import __version__
from assetmind.api.routes import router
from assetmind.application.budget import BudgetManager
from assetmind.application.service import AnalysisService
from assetmind.config.settings import Settings
from assetmind.observability.logging import configure_logging
from assetmind.persistence.db import create_db_engine, create_schema, create_session_factory, ping
from assetmind.persistence.jobs import JobRepository
from assetmind.persistence.repository import AnalysisRepository
from assetmind.providers.bcb import BancoCentralProvider
from assetmind.providers.brapi import BrapiProvider
from assetmind.providers.coingecko import CoinGeckoProvider
from assetmind.providers.cvm import CvmProvider
from assetmind.providers.fixtures import FixtureMacroProvider, FixtureMarketProvider
from assetmind.providers.registry import ProviderRegistry
from assetmind.security.rate_limit import RateLimiter
from assetmind.workflows.analysis import build_analysis_workflow


def create_app(
    settings: Settings | None = None,
    *,
    http_client: httpx.AsyncClient | None = None,
    database_url: str | None = None,
) -> FastAPI:
    runtime = settings or Settings()
    if database_url is not None:
        runtime = runtime.model_copy(update={"database_url": database_url})
    logger = configure_logging()
    engine = create_db_engine(runtime.database_url)
    create_schema(engine)
    session_factory = create_session_factory(engine)
    repository = AnalysisRepository(session_factory)
    jobs = JobRepository(session_factory)
    client = http_client or httpx.AsyncClient()

    def registry_factory(budget: BudgetManager) -> ProviderRegistry:
        if runtime.provider_mode == "fixtures":
            market = FixtureMarketProvider()
            return ProviderRegistry(
                brapi=market,
                coingecko=market,
                bcb=FixtureMacroProvider(),
                cvm=CvmProvider(use_fixtures=True),
                budget=budget,
            )
        return ProviderRegistry(
            brapi=BrapiProvider(
                client,
                base_url=runtime.brapi_base_url,
                api_key=runtime.brapi_api_key,
                timeout=runtime.provider_timeout_seconds,
                max_retries=runtime.max_provider_retries,
            ),
            coingecko=CoinGeckoProvider(
                client,
                base_url=runtime.coingecko_base_url,
                api_key=runtime.coingecko_api_key,
                timeout=runtime.provider_timeout_seconds,
                max_retries=runtime.max_provider_retries,
            ),
            bcb=BancoCentralProvider(
                client,
                base_url=runtime.bcb_base_url,
                timeout=runtime.provider_timeout_seconds,
                max_retries=runtime.max_provider_retries,
            ),
            cvm=CvmProvider(use_fixtures=False),
            budget=budget,
        )

    def budget_factory(asset_count: int) -> BudgetManager:
        return BudgetManager(runtime.budget_limits()).scaled_for_assets(asset_count)

    service = AnalysisService(
        repository,
        registry_factory,
        logger,
        budget_factory,
        jobs=jobs,
        job_queue_enabled=runtime.job_queue_enabled,
        job_max_attempts=runtime.job_max_attempts,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if http_client is None:
            await client.aclose()
        engine.dispose()

    app = FastAPI(
        title="AssetMind AI",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = runtime
    app.state.http_client = client
    app.state.service = service
    app.state.repository = repository
    app.state.ping = lambda: ping(engine)
    app.state.rate_limiter = RateLimiter(runtime.rate_limit_per_minute)
    _mount_agent_ui(app, runtime)
    _mount_api_docs(app)
    app.include_router(router)
    if runtime.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=runtime.cors_origin_list,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Correlation-ID"],
        )
    if runtime.agentos_enabled:
        _mount_agent_os(app, runtime)
    _limit_openapi_to_product_api(app)
    return app


def _limit_openapi_to_product_api(app: FastAPI) -> None:
    """Keep Scalar/OpenAPI on AssetMind routes. AgentOS control paths stay live but hidden."""

    def openapi() -> dict[str, object]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = FastAPI.openapi(app)
        paths = schema.get("paths")
        if isinstance(paths, dict):
            schema["paths"] = {
                path: item for path, item in paths.items() if path in {"/health", "/ready"} or path.startswith("/api/")
            }
        schema["info"] = {
            **(schema.get("info") or {}),
            "description": (
                "AssetMind product HTTP API. AgentOS chat control routes exist for the Agent UI but are omitted here."
            ),
        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]


def _mount_agent_ui(app: FastAPI, settings: Settings) -> None:
    """Send `/` to the Agno Agent UI. API docs live on `/scalar`."""

    target = settings.agent_ui_url.strip()

    def agent_ui() -> RedirectResponse | JSONResponse:
        if not target:
            return JSONResponse(
                {
                    "name": "AssetMind AI",
                    "health": "/health",
                    "ui": "not configured",
                    "docs": "/scalar",
                }
            )
        return RedirectResponse(target, status_code=307)

    app.add_api_route("/", agent_ui, methods=["GET"], include_in_schema=False, response_model=None)


def _mount_api_docs(app: FastAPI) -> None:
    """Mount Scalar and send legacy Swagger/ReDoc paths there."""

    add_scalar_reference(app, route="/scalar", include_in_schema=False)

    def docs_to_scalar() -> RedirectResponse:
        return RedirectResponse("/scalar", status_code=307)

    for path in ("/docs", "/redoc"):
        app.add_api_route(path, docs_to_scalar, methods=["GET"], include_in_schema=False, response_model=None)


def _mount_agent_os(app: FastAPI, settings: Settings) -> None:
    from agno.db.sqlite import SqliteDb
    from agno.os import AgentOS
    from agno.os.config import AuthorizationConfig
    from agno.os.settings import AgnoAPISettings

    from assetmind.agents.chat import build_chat_agent

    security_key = settings.os_security_key or settings.api_key
    os_settings = AgnoAPISettings(
        docs_enabled=False,
        os_security_key=None if settings.agentos_jwt_secret else security_key,
    )
    database = SqliteDb(db_file=_agentos_database(settings), id="assetmind-os")
    common = {
        "name": "AssetMind",
        "agents": [build_chat_agent(app.state.service, settings, http_client=app.state.http_client)],
        "workflows": [build_analysis_workflow()],
        "db": database,
        "base_app": app,
        "on_route_conflict": "preserve_base_app",
        "settings": os_settings,
        "telemetry": False,
        "tracing": False,
        "scheduler": False,
        "auto_provision_dbs": True,
        "cors_allowed_origins": _ui_origins(settings),
    }
    public_routes = [
        "/health",
        "/ready",
        "/api/*",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/scalar",
    ]
    if settings.agentos_jwt_secret:
        from agno.os.authz import Authorization

        AgentOS(
            authorization=Authorization(
                verification_keys=[settings.agentos_jwt_secret],
                algorithm="HS256",
                excluded_route_paths=public_routes,
            ),
            **common,
        ).get_app()
        return
    if not security_key:
        raise RuntimeError("ASSETMIND_API_KEY or ASSETMIND_OS_SECURITY_KEY is required when AgentOS is enabled.")
    AgentOS(
        authorization_config=AuthorizationConfig(excluded_route_paths=public_routes),
        **common,
    ).get_app()


def _agentos_database(settings: Settings) -> str:
    from pathlib import Path

    url = settings.database_url
    if url.startswith("sqlite"):
        location = url.split("///", 1)[-1]
        return str(Path(location).with_name("assetmind-os.db"))
    return "assetmind-os.db"


def _ui_origins(settings: Settings) -> list[str]:
    origins = ["http://127.0.0.1:3000", "http://localhost:3000"]
    for origin in settings.cors_origin_list:
        if origin not in origins:
            origins.append(origin)
    return origins


def agent_factory_placeholder() -> Callable[[], None]:
    """Keeps the optional model gateway import out of the default request path."""

    return lambda: None

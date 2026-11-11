"""Versioned HTTP routes. AgentOS control routes are not mounted here."""

import json
import re
from collections.abc import Iterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from assetmind.api.schemas import AnalysisAccepted, AnalysisCreate, ErrorBody, MoversResponse
from assetmind.application.budget import provider_probe_snapshot
from assetmind.application.service import AnalysisService
from assetmind.domain.assets.catalog import (
    LIVE_LISTING_LIMITATION,
    catalog_payload,
    search_catalog,
    search_entries,
)
from assetmind.domain.assets.identity import AssetRequest
from assetmind.domain.assets.movers import MoverAssetType, MoverDirection, MoverSort
from assetmind.domain.errors import DomainError
from assetmind.domain.scenarios.policy import ScenarioAssumptions
from assetmind.persistence.repository import AnalysisRepository, StoredAnalysis
from assetmind.providers.errors import ProviderError
from assetmind.providers.listings import cached_listings
from assetmind.providers.movers import cached_movers, fixture_movers
from assetmind.providers.news import fetch_headlines
from assetmind.security.auth import AuthenticationError, require_api_key

router = APIRouter()
_CORRELATION = re.compile(r"^[A-Za-z0-9_.:-]{8,64}$")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    try:
        request.app.state.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ready"}


@router.get("/api/v1/assets/search")
async def search_assets(
    request: Request,
    q: str = "",
    x_api_key: str | None = Header(default=None),
) -> dict[str, object]:
    _authorize(request, x_api_key)
    _limit(request, x_api_key or "anonymous")
    settings = request.app.state.settings
    if settings.provider_mode == "live":
        try:
            listed = await cached_listings(
                request.app.state.http_client,
                brapi_base_url=settings.brapi_base_url,
                brapi_api_key=settings.brapi_api_key,
                coingecko_base_url=settings.coingecko_base_url,
                coingecko_api_key=settings.coingecko_api_key,
            )
        except ProviderError:
            return catalog_payload(search_catalog(q, limit=50))
        return catalog_payload(search_entries(listed, q, limit=50), limitation=LIVE_LISTING_LIMITATION)
    return catalog_payload(search_catalog(q, limit=50))


@router.get("/api/v1/assets/movers", response_model=MoversResponse)
async def list_movers(
    request: Request,
    direction: Annotated[MoverDirection, Query()] = MoverDirection.BOTH,
    asset_type: Annotated[MoverAssetType, Query(alias="type")] = MoverAssetType.ALL,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
    min_volume: Annotated[float, Query(ge=0)] = 0,
    sort_by: Annotated[MoverSort, Query()] = MoverSort.CHANGE,
    x_api_key: str | None = Header(default=None),
) -> MoversResponse:
    """List assets rising and falling. Quantity, volume filter, type, and pagination are query params."""

    _authorize(request, x_api_key)
    _limit(request, x_api_key or "anonymous")
    settings = request.app.state.settings
    if settings.provider_mode == "fixtures":
        result = fixture_movers(
            direction=direction,
            asset_type=asset_type,
            limit=limit,
            page=page,
            min_volume=min_volume,
            sort_by=sort_by,
        )
    else:
        try:
            result = await cached_movers(
                request.app.state.http_client,
                brapi_base_url=settings.brapi_base_url,
                brapi_api_key=settings.brapi_api_key,
                coingecko_base_url=settings.coingecko_base_url,
                coingecko_api_key=settings.coingecko_api_key,
                direction=direction,
                asset_type=asset_type,
                limit=limit,
                page=page,
                min_volume=min_volume,
                sort_by=sort_by,
            )
        except ProviderError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc
    return MoversResponse.model_validate(result.model_dump())


@router.get("/api/v1/assets/{symbol}/news")
async def asset_news(
    symbol: str,
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> dict[str, object]:
    _authorize(request, x_api_key)
    _limit(request, x_api_key or "anonymous")
    repository: AnalysisRepository = request.app.state.repository
    try:
        payload = await fetch_headlines(request.app.state.http_client, symbol.strip().upper())
    except ProviderError as exc:
        repository.record_usage(kind="news", usage=provider_probe_snapshot())
        raise HTTPException(status_code=503, detail=exc.message) from exc
    repository.record_usage(kind="news", usage=provider_probe_snapshot())
    return payload


@router.post("/api/v1/analyses", response_model=AnalysisAccepted)
async def create_analysis(
    request: Request,
    body: AnalysisCreate,
    x_api_key: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> AnalysisAccepted:
    correlation_id = _correlation(x_correlation_id)
    _authorize(request, x_api_key)
    _limit(request, x_api_key or "anonymous")
    service: AnalysisService = request.app.state.service
    settings = request.app.state.settings
    if len(body.assets) > settings.max_assets:
        raise _http(422, "too_many_assets", "Too many assets for one analysis.", correlation_id)
    scenarios = None if body.scenarios is None else ScenarioAssumptions.model_validate(body.scenarios.model_dump())
    try:
        stored = await service.run(
            assets=[AssetRequest.model_validate(asset.model_dump()) for asset in body.assets],
            scenarios=scenarios,
            correlation_id=correlation_id,
            as_of=body.as_of,
            deadline_seconds=settings.deadline_seconds,
        )
    except DomainError as exc:
        raise _http(422, exc.code, exc.message, correlation_id) from exc
    report = json.loads(stored.report_json) if stored.report_json else None
    return AnalysisAccepted(
        analysis_id=stored.id,
        correlation_id=stored.correlation_id,
        status=stored.status,
        report=report,
        error_code=stored.error_code,
    )


@router.get("/api/v1/usage/balance")
def usage_balance(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> dict[str, object]:
    _authorize(request, x_api_key)
    repository: AnalysisRepository = request.app.state.repository
    allowance = request.app.state.settings.token_allowance
    return repository.token_balance(allowance).model_dump()


@router.get("/api/v1/analyses/{analysis_id}")
def get_analysis(
    request: Request,
    analysis_id: str,
    x_api_key: str | None = Header(default=None),
) -> dict[str, object]:
    _authorize(request, x_api_key)
    stored = _stored(request, analysis_id)
    return {
        "analysis_id": stored.id,
        "correlation_id": stored.correlation_id,
        "status": stored.status,
        "error_code": stored.error_code,
    }


@router.get("/api/v1/analyses/{analysis_id}/report")
def get_report(
    request: Request,
    analysis_id: str,
    x_api_key: str | None = Header(default=None),
) -> dict[str, object]:
    _authorize(request, x_api_key)
    stored = _stored(request, analysis_id)
    if not stored.report_json:
        raise HTTPException(status_code=404, detail="report_not_ready")
    return json.loads(stored.report_json)


@router.get("/api/v1/analyses/{analysis_id}/events")
def get_events(
    request: Request,
    analysis_id: str,
    x_api_key: str | None = Header(default=None),
) -> StreamingResponse:
    _authorize(request, x_api_key)
    _stored(request, analysis_id)
    repository: AnalysisRepository = request.app.state.repository

    def stream() -> Iterator[str]:
        for event in repository.events(analysis_id):
            payload = {
                "state": event.state,
                "message": event.message,
                "created_at": event.created_at.isoformat(),
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


def _authorize(request: Request, api_key: str | None) -> None:
    try:
        require_api_key(request.app.state.settings, api_key)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _limit(request: Request, key: str) -> None:
    if not request.app.state.rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="rate_limited", headers={"Retry-After": "60"})


def _stored(request: Request, analysis_id: str) -> StoredAnalysis:
    repository: AnalysisRepository = request.app.state.repository
    stored = repository.get(analysis_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="analysis_not_found")
    return stored


def _correlation(value: str | None) -> str:
    if value is None:
        return uuid4().hex
    if not _CORRELATION.match(value):
        raise HTTPException(status_code=400, detail="invalid_correlation_id")
    return value


def _http(status: int, code: str, message: str, correlation_id: str) -> HTTPException:
    body = ErrorBody(code=code, message=message, correlation_id=correlation_id)
    return HTTPException(status_code=status, detail=body.model_dump())

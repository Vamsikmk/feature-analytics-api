from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app import core
from app.database import get_db
from app.schemas import TopFeatureItem, UniqueUsersResponse, UsageResponse
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/usage", response_model=UsageResponse)
@limiter.limit("30/minute")
async def get_usage(
    request: Request,
    feature: str = Query(..., description="Feature name to query"),
    start: datetime | None = Query(None, description="Start of time window (ISO 8601)"),
    end: datetime | None = Query(None, description="End of time window (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = {"endpoint": "usage", "feature": feature, "start": str(start), "end": str(end)}
    cached = core.cache.get(cache_key)
    if cached is not None:
        return cached

    count = await analytics_service.get_usage_count(db, feature, start, end)
    result = UsageResponse(feature=feature, count=count, start=start, end=end)
    core.cache.set(cache_key, result)
    return result


@router.get("/unique-users", response_model=UniqueUsersResponse)
@limiter.limit("30/minute")
async def get_unique_users(
    request: Request,
    feature: str = Query(..., description="Feature name to query"),
    start: datetime | None = Query(None, description="Start of time window (ISO 8601)"),
    end: datetime | None = Query(None, description="End of time window (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = {"endpoint": "unique-users", "feature": feature, "start": str(start), "end": str(end)}
    cached = core.cache.get(cache_key)
    if cached is not None:
        return cached

    unique = await analytics_service.get_unique_users(db, feature, start, end)
    result = UniqueUsersResponse(feature=feature, unique_users=unique, start=start, end=end)
    core.cache.set(cache_key, result)
    return result


@router.get("/top-features", response_model=list[TopFeatureItem])
@limiter.limit("30/minute")
async def get_top_features(
    request: Request,
    n: int = Query(10, ge=1, le=100, description="Number of top features to return"),
    start: datetime | None = Query(None, description="Start of time window (ISO 8601)"),
    end: datetime | None = Query(None, description="End of time window (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = {"endpoint": "top-features", "n": n, "start": str(start), "end": str(end)}
    cached = core.cache.get(cache_key)
    if cached is not None:
        return cached

    results = await analytics_service.get_top_features(db, n, start, end)
    core.cache.set(cache_key, results)
    return results


@router.get("/breakdown", response_model=list[dict])
@limiter.limit("30/minute")
async def get_breakdown(
    request: Request,
    feature: str = Query(..., description="Feature name to query"),
    by: Annotated[list[str], Query(description="One or more metadata keys to group by. Can be repeated: &by=plan&by=device")] = [],
    start: datetime | None = Query(None, description="Start of time window (ISO 8601)"),
    end: datetime | None = Query(None, description="End of time window (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
):
    if not by:
        return []

    cache_key = {
        "endpoint": "breakdown",
        "feature": feature,
        "by": sorted(by),
        "start": str(start),
        "end": str(end),
    }
    cached = core.cache.get(cache_key)
    if cached is not None:
        return cached

    results = await analytics_service.get_breakdown(db, feature, by, start, end)
    core.cache.set(cache_key, results)
    return results

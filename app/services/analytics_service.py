import json
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event


def _apply_time_filters(stmt, start: datetime | None, end: datetime | None):
    if start:
        stmt = stmt.where(Event.timestamp >= start)
    if end:
        stmt = stmt.where(Event.timestamp <= end)
    return stmt


async def get_usage_count(
    db: AsyncSession,
    feature: str,
    start: datetime | None,
    end: datetime | None,
) -> int:
    stmt = select(func.count()).where(Event.feature == feature)
    stmt = _apply_time_filters(stmt, start, end)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_unique_users(
    db: AsyncSession,
    feature: str,
    start: datetime | None,
    end: datetime | None,
) -> int:
    stmt = select(func.count(func.distinct(Event.user_id))).where(Event.feature == feature)
    stmt = _apply_time_filters(stmt, start, end)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_top_features(
    db: AsyncSession,
    n: int,
    start: datetime | None,
    end: datetime | None,
) -> list[dict]:
    stmt = (
        select(Event.feature, func.count().label("count"))
        .group_by(Event.feature)
        .order_by(func.count().desc())
        .limit(n)
    )
    stmt = _apply_time_filters(stmt, start, end)
    result = await db.execute(stmt)
    return [{"feature": row.feature, "count": row.count} for row in result.all()]


async def get_breakdown(
    db: AsyncSession,
    feature: str,
    dimensions: list[str],
    start: datetime | None,
    end: datetime | None,
) -> list[dict]:
    stmt = select(Event.metadata_json).where(
        Event.feature == feature,
        Event.metadata_json.isnot(None),
    )
    stmt = _apply_time_filters(stmt, start, end)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    counts: dict[tuple, int] = {}
    for raw in rows:
        try:
            meta = json.loads(raw)
            key = tuple(str(meta[d]) if d in meta else None for d in dimensions)
        except (json.JSONDecodeError, TypeError):
            continue
        if any(v is not None for v in key):
            counts[key] = counts.get(key, 0) + 1

    results = []
    for key_tuple, count in sorted(counts.items(), key=lambda x: -x[1]):
        row = {dim: val for dim, val in zip(dimensions, key_tuple)}
        row["count"] = count
        results.append(row)

    return results

import json

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import core
from app.models import Event
from app.schemas import EventIn


async def ingest_events(db: AsyncSession, events: list[EventIn]) -> int:
    rows = [
        {
            "timestamp": e.timestamp,
            "user_id": e.user_id,
            "feature": e.feature,
            "metadata_json": json.dumps(e.metadata) if e.metadata is not None else None,
        }
        for e in events
    ]
    await db.execute(insert(Event), rows)
    await db.commit()
    core.cache.invalidate_all()
    return len(rows)

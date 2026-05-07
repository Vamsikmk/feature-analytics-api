from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app import core
from app.core.config import settings
from app.database import get_db
from app.schemas import EventBatch, EventIn, IngestResponse
from app.services import event_service

router = APIRouter(prefix="/events", tags=["Events"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def ingest_events(
    request: Request,
    payload: EventIn | EventBatch,
    db: AsyncSession = Depends(get_db),
):
    if isinstance(payload, EventIn):
        events = [payload]
    else:
        events = payload.events

    if len(events) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size {len(events)} exceeds maximum of {settings.MAX_BATCH_SIZE}",
        )

    count = await event_service.ingest_events(db, events)
    return IngestResponse(ingested=count, message=f"Successfully ingested {count} event(s)")

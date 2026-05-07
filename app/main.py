from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware
from app.database import init_db
from app.routers import analytics, events
from app.schemas import HealthResponse

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="REST API for ingesting and analyzing feature usage events.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(analytics.router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@limiter.limit("60/minute")
async def health_check(request: Request):
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@app.post("/seed", tags=["Seed"])
@limiter.limit("5/minute")
async def seed_data(request: Request):
    from app.database import AsyncSessionLocal
    from app.services.event_service import ingest_events
    from scripts.seed import generate_events

    events_data = generate_events(10_000)
    async with AsyncSessionLocal() as db:
        count = await ingest_events(db, events_data)
    return {"seeded": count, "message": f"Successfully seeded {count} events"}

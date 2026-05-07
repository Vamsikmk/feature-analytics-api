import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_client(client):
    known_events = [
        {
            "timestamp": "2025-01-10T10:00:00Z",
            "user_id": "user-001",
            "feature": "sidebar_search",
            "metadata": {"plan": "pro", "device": "mobile"},
        },
        {
            "timestamp": "2025-01-11T11:00:00Z",
            "user_id": "user-002",
            "feature": "sidebar_search",
            "metadata": {"plan": "free", "device": "desktop"},
        },
        {
            "timestamp": "2025-01-12T12:00:00Z",
            "user_id": "user-001",
            "feature": "sidebar_search",
            "metadata": {"plan": "pro", "device": "mobile"},
        },
        {
            "timestamp": "2025-01-15T09:00:00Z",
            "user_id": "user-003",
            "feature": "dashboard_view",
            "metadata": {"plan": "enterprise", "device": "desktop"},
        },
        {
            "timestamp": "2025-01-20T14:00:00Z",
            "user_id": "user-004",
            "feature": "bill_payment",
            "metadata": {"plan": "free", "device": "tablet"},
        },
    ]
    await client.post("/events", json={"events": known_events})
    yield client

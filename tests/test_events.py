import pytest


@pytest.mark.asyncio
async def test_ingest_single_event(client):
    payload = {
        "timestamp": "2025-03-01T08:00:00Z",
        "user_id": "user-single",
        "feature": "hotspot_toggle",
        "metadata": {"plan": "pro", "device": "mobile"},
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["ingested"] == 1


@pytest.mark.asyncio
async def test_ingest_batch_events(client):
    payload = {
        "events": [
            {
                "timestamp": "2025-03-02T09:00:00Z",
                "user_id": f"user-batch-{i}",
                "feature": "dashboard_view",
                "metadata": {"plan": "free"},
            }
            for i in range(5)
        ]
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["ingested"] == 5


@pytest.mark.asyncio
async def test_batch_exceeding_limit_returns_400(client):
    payload = {
        "events": [
            {
                "timestamp": "2025-03-03T10:00:00Z",
                "user_id": f"user-{i}",
                "feature": "test_feature",
            }
            for i in range(1001)
        ]
    }
    response = await client.post("/events", json=payload)
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_missing_required_field_returns_422(client):
    payload = {
        "user_id": "user-no-timestamp",
        "feature": "sidebar_search",
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_feature_returns_422(client):
    payload = {
        "timestamp": "2025-03-01T08:00:00Z",
        "user_id": "user-no-feature",
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_timestamp_format_returns_422(client):
    payload = {
        "timestamp": "not-a-valid-datetime",
        "user_id": "user-bad-ts",
        "feature": "sidebar_search",
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_metadata_as_list_returns_422(client):
    payload = {
        "timestamp": "2025-03-01T08:00:00Z",
        "user_id": "user-bad-meta",
        "feature": "sidebar_search",
        "metadata": ["plan", "pro"],
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_metadata_exceeding_2kb_returns_422(client):
    payload = {
        "timestamp": "2025-03-01T08:00:00Z",
        "user_id": "user-big-meta",
        "feature": "sidebar_search",
        "metadata": {"key": "x" * 3000},
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 422
    assert "2KB" in response.text or "2048" in response.text or "metadata" in response.text


@pytest.mark.asyncio
async def test_metadata_deeply_nested_returns_422(client):
    payload = {
        "timestamp": "2025-03-01T08:00:00Z",
        "user_id": "user-deep-meta",
        "feature": "sidebar_search",
        "metadata": {"level1": {"level2": {"level3": "too deep"}}},
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 422
    assert "depth" in response.text or "nesting" in response.text or "metadata" in response.text


@pytest.mark.asyncio
async def test_ingest_without_metadata(client):
    payload = {
        "timestamp": "2025-03-01T08:30:00Z",
        "user_id": "user-no-meta",
        "feature": "plan_upgrade",
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 201
    assert response.json()["ingested"] == 1


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data

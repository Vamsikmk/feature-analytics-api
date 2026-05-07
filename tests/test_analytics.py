import pytest


@pytest.mark.asyncio
async def test_usage_count_returns_correct_number(seeded_client):
    response = await seeded_client.get("/analytics/usage?feature=sidebar_search")
    assert response.status_code == 200
    data = response.json()
    assert data["feature"] == "sidebar_search"
    assert data["count"] >= 3


@pytest.mark.asyncio
async def test_unique_user_count_returns_distinct_count(seeded_client):
    response = await seeded_client.get("/analytics/unique-users?feature=sidebar_search")
    assert response.status_code == 200
    data = response.json()
    assert data["feature"] == "sidebar_search"
    assert data["unique_users"] >= 2


@pytest.mark.asyncio
async def test_top_features_returns_correct_ranking(seeded_client):
    response = await seeded_client.get("/analytics/top-features?n=3")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) <= 3
    counts = [item["count"] for item in items]
    assert counts == sorted(counts, reverse=True)


@pytest.mark.asyncio
async def test_top_features_respects_n_param(seeded_client):
    response = await seeded_client.get("/analytics/top-features?n=1")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1


@pytest.mark.asyncio
async def test_breakdown_by_plan(seeded_client):
    response = await seeded_client.get(
        "/analytics/breakdown?feature=sidebar_search&by=plan"
    )
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    plan_values = [item["plan"] for item in items]
    assert "pro" in plan_values or "free" in plan_values


@pytest.mark.asyncio
async def test_breakdown_by_device(seeded_client):
    response = await seeded_client.get(
        "/analytics/breakdown?feature=sidebar_search&by=device"
    )
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert all("device" in item for item in items)


@pytest.mark.asyncio
async def test_breakdown_multi_dimension(seeded_client):
    response = await seeded_client.get(
        "/analytics/breakdown?feature=sidebar_search&by=plan&by=device"
    )
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert all("plan" in item and "device" in item and "count" in item for item in items)


@pytest.mark.asyncio
async def test_time_window_filtering(seeded_client):
    response = await seeded_client.get(
        "/analytics/usage"
        "?feature=sidebar_search"
        "&start=2025-01-10T00:00:00Z"
        "&end=2025-01-11T23:59:59Z"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 2


@pytest.mark.asyncio
async def test_time_window_excludes_out_of_range(seeded_client):
    response = await seeded_client.get(
        "/analytics/usage"
        "?feature=sidebar_search"
        "&start=2020-01-01T00:00:00Z"
        "&end=2020-12-31T23:59:59Z"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_unknown_dimension_returns_empty_list(seeded_client):
    response = await seeded_client.get(
        "/analytics/breakdown?feature=sidebar_search&by=nonexistent_key_xyz"
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_usage_unknown_feature_returns_zero(seeded_client):
    response = await seeded_client.get("/analytics/usage?feature=feature_does_not_exist")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.asyncio
async def test_unique_users_unknown_feature_returns_zero(seeded_client):
    response = await seeded_client.get(
        "/analytics/unique-users?feature=feature_does_not_exist"
    )
    assert response.status_code == 200
    assert response.json()["unique_users"] == 0

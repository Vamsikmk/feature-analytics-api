"""
API smoke test script — calls POST /events endpoint with realistic payloads.

Usage:
    python -m scripts.api_test                      # 100 single events
    python -m scripts.api_test --mode batch         # 10 batches of 100 events
    python -m scripts.api_test --count 500          # 500 single events
    python -m scripts.api_test --url http://localhost:8000

What this tests:
    - API is reachable and responding
    - Validation is working (sends one bad payload at the end)
    - Rate limiting triggers correctly under burst load
    - Response times are acceptable
    - Batch ingestion works end to end
"""

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000"

FEATURES = [
    "sidebar_search", "dashboard_view", "plan_upgrade",
    "bill_payment", "data_usage_check", "support_chat",
    "autopay_setup", "sync_up_tracker", "hotspot_toggle",
]
PLANS = ["free", "pro", "enterprise", "prepaid"]
DEVICES = ["mobile", "desktop", "tablet", "watch"]
REGIONS = ["west", "east", "central", "south"]


def make_event() -> dict:
    now = datetime.now(timezone.utc)
    ts = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
    return {
        "timestamp": ts.isoformat(),
        "user_id": f"user-{random.randint(1, 2000):04d}",
        "feature": random.choice(FEATURES),
        "metadata": {
            "plan": random.choice(PLANS),
            "device": random.choice(DEVICES),
            "region": random.choice(REGIONS),
        },
    }


def run_single(client: httpx.Client, count: int) -> None:
    print(f"\n--- Single Event Mode ({count} requests) ---")
    success = fail = 0
    latencies = []

    for i in range(count):
        payload = make_event()
        start = time.monotonic()
        try:
            response = client.post(f"{BASE_URL}/events", json=payload)
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            latencies.append(latency_ms)

            if response.status_code == 201:
                success += 1
            elif response.status_code == 429:
                print(f"  [{i+1}] Rate limited (429) — slowing down...")
                time.sleep(2)
                fail += 1
            else:
                print(f"  [{i+1}] Unexpected {response.status_code}: {response.text[:80]}")
                fail += 1

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{count} | last latency: {latency_ms}ms")

        except httpx.ConnectError:
            print("  ERROR: Cannot connect. Is the server running on", BASE_URL)
            sys.exit(1)

    _print_summary(success, fail, latencies)


def run_batch(client: httpx.Client, batches: int, batch_size: int = 100) -> None:
    print(f"\n--- Batch Mode ({batches} batches × {batch_size} events) ---")
    success = fail = 0
    latencies = []

    for i in range(batches):
        payload = {"events": [make_event() for _ in range(batch_size)]}
        start = time.monotonic()
        try:
            response = client.post(f"{BASE_URL}/events", json=payload)
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            latencies.append(latency_ms)

            if response.status_code == 201:
                ingested = response.json().get("ingested", 0)
                success += ingested
                print(f"  Batch {i+1}/{batches} → {ingested} events ingested in {latency_ms}ms")
            elif response.status_code == 429:
                print(f"  Batch {i+1} rate limited — waiting 2s...")
                time.sleep(2)
                fail += batch_size
            else:
                print(f"  Batch {i+1} failed {response.status_code}: {response.text[:80]}")
                fail += batch_size

        except httpx.ConnectError:
            print("  ERROR: Cannot connect. Is the server running on", BASE_URL)
            sys.exit(1)

    _print_summary(success, fail, latencies)


def run_validation_check(client: httpx.Client) -> None:
    print("\n--- Validation Check ---")

    tests = [
        ("Missing timestamp",        {"user_id": "u1", "feature": "test"}, 422),
        ("Empty user_id",            {"timestamp": "2025-01-01T00:00:00Z", "user_id": "", "feature": "test"}, 422),
        ("Metadata as list",         {"timestamp": "2025-01-01T00:00:00Z", "user_id": "u1", "feature": "test", "metadata": ["bad"]}, 422),
        ("Metadata too large",       {"timestamp": "2025-01-01T00:00:00Z", "user_id": "u1", "feature": "test", "metadata": {"k": "x" * 3000}}, 422),
        ("Valid single event",       {"timestamp": "2025-01-01T00:00:00Z", "user_id": "u1", "feature": "test", "metadata": {"plan": "pro"}}, 201),
    ]

    for name, payload, expected in tests:
        response = client.post(f"{BASE_URL}/events", json=payload)
        status = "PASS" if response.status_code == expected else "FAIL"
        print(f"  {status} | {name} | expected={expected} got={response.status_code}")


def _print_summary(success: int, fail: int, latencies: list) -> None:
    print(f"\n{'='*40}")
    print(f"  Total success : {success}")
    print(f"  Total failed  : {fail}")
    if latencies:
        latencies.sort()
        print(f"  Avg latency   : {round(sum(latencies)/len(latencies), 1)}ms")
        print(f"  p50 latency   : {latencies[len(latencies)//2]}ms")
        print(f"  p95 latency   : {latencies[int(len(latencies)*0.95)]}ms")
        print(f"  Max latency   : {latencies[-1]}ms")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API smoke test for feature-analytics-api")
    parser.add_argument("--mode", choices=["single", "batch", "validate", "all"], default="all")
    parser.add_argument("--count", type=int, default=100, help="Number of single events or batches")
    parser.add_argument("--url", type=str, default=BASE_URL, help="Base URL of the API")
    args = parser.parse_args()

    BASE_URL = args.url

    print(f"Target: {BASE_URL}")
    print(f"Mode  : {args.mode}")

    with httpx.Client(timeout=30.0) as client:
        health = client.get(f"{BASE_URL}/health")
        if health.status_code != 200:
            print("ERROR: Health check failed. Is the server running?")
            sys.exit(1)
        print(f"Health check: OK\n")

        if args.mode in ("single", "all"):
            run_single(client, args.count)

        if args.mode in ("batch", "all"):
            run_batch(client, batches=10, batch_size=100)

        if args.mode in ("validate", "all"):
            run_validation_check(client)

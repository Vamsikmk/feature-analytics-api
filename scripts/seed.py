"""
Seed script — generates realistic feature usage events.

Usage:
    python -m scripts.seed              # seeds 10,000 events via API
    python -m scripts.seed --count 50000
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone

from app.schemas import EventIn

FEATURES = [
    "sidebar_search",
    "dashboard_view",
    "plan_upgrade",
    "bill_payment",
    "data_usage_check",
    "international_roaming",
    "device_trade_in",
    "support_chat",
    "autopay_setup",
    "account_settings",
    "family_plan_add_line",
    "sync_up_tracker",
    "hotspot_toggle",
    "app_store_browse",
    "notification_preferences",
]

PLANS = ["free", "pro", "enterprise", "prepaid"]
DEVICES = ["mobile", "desktop", "tablet", "watch"]
REGIONS = ["west", "east", "central", "south"]


def generate_events(count: int = 10_000) -> list[EventIn]:
    now = datetime.now(timezone.utc)
    events = []
    for _ in range(count):
        days_ago = random.randint(0, 90)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        ts = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        user_num = random.randint(1, 2_000)
        feature = random.choices(
            FEATURES,
            weights=[20, 15, 12, 11, 10, 8, 7, 6, 5, 4, 3, 3, 2, 2, 2],
        )[0]

        metadata = {
            "plan": random.choice(PLANS),
            "device": random.choice(DEVICES),
            "region": random.choice(REGIONS),
        }

        events.append(
            EventIn(
                timestamp=ts,
                user_id=f"user-{user_num:04d}",
                feature=feature,
                metadata=metadata,
            )
        )
    return events


async def seed_via_db(count: int) -> None:
    from app.database import AsyncSessionLocal, init_db
    from app.services.event_service import ingest_events

    await init_db()

    BATCH = 1000
    total = 0
    async with AsyncSessionLocal() as db:
        for i in range(0, count, BATCH):
            batch_count = min(BATCH, count - i)
            batch = generate_events(batch_count)
            inserted = await ingest_events(db, batch)
            total += inserted
            print(f"  Seeded {total}/{count} events...")

    print(f"Done. Total seeded: {total}")


if __name__ == "__main__":
    count = 10_000
    for arg in sys.argv[1:]:
        if arg.startswith("--count="):
            count = int(arg.split("=")[1])
        elif arg == "--count" and sys.argv.index(arg) + 1 < len(sys.argv):
            count = int(sys.argv[sys.argv.index(arg) + 1])

    print(f"Seeding {count} events...")
    asyncio.run(seed_via_db(count))

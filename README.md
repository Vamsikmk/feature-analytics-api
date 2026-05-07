# Feature Analytics API

A REST API for ingesting and analyzing feature usage events. Built with **FastAPI**, **SQLAlchemy (async)**, and **SQLite** as a working MVP.

---

## Section 1 — What Was Built & How to Run It

### What Is Implemented

| Area | What Was Done |
|---|---|
| **Ingestion** | `POST /events` — accepts a single event or a batch of up to 1,000 events |
| **Analytics** | 4 query endpoints: usage count, unique users, top-N features, metadata breakdown |
| **Caching** | In-memory TTL cache (60s) — invalidated on every write |
| **Rate limiting** | Per-IP limits via `slowapi` — 60/min on ingestion, 30/min on analytics |
| **Request logging** | Structured logs for every request (method, path, status, latency) |
| **Response headers** | `X-Response-Time-Ms` on every response |
| **CORS** | Open CORS for development (`allow_origins=["*"]`) |
| **Tests** | Pytest suite with in-memory SQLite — deterministic seeded data, no flakiness |
| **Seed data** | Script + API endpoint to seed 10,000 realistic events |
| **Docker** | Single `Dockerfile`, runs with one command |

---

### Project Structure

```
feature-analytics-api/
├── app/
│   ├── main.py              # FastAPI app, lifespan, CORS, rate limiter, health + seed
│   ├── database.py          # SQLAlchemy async engine and session
│   ├── models.py            # Event ORM model with composite indexes
│   ├── schemas.py           # Pydantic v2 request/response schemas
│   ├── routers/
│   │   ├── events.py        # POST /events
│   │   └── analytics.py     # GET /analytics/*
│   ├── services/
│   │   ├── event_service.py     # Ingest logic
│   │   └── analytics_service.py # Query logic
│   └── core/
│       ├── config.py        # Settings loaded from env vars
│       ├── cache.py         # In-memory TTL cache
│       └── middleware.py    # Request logging + X-Response-Time-Ms header
├── tests/
│   ├── conftest.py          # Test DB, client fixtures, seeded data
│   ├── test_events.py       # Ingestion tests
│   └── test_analytics.py   # Analytics endpoint tests
├── scripts/
│   └── seed.py              # Data seeding script
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

### Environment Setup

```bash
# 1. Clone and enter the project
cd feature-analytics-api

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
cp .env.example .env
```

#### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./analytics.db` | Database connection string |
| `CACHE_TTL_SECONDS` | `60` | Analytics cache TTL in seconds |
| `MAX_BATCH_SIZE` | `1000` | Max events per batch request |
| `APP_TITLE` | `Feature Analytics API` | API title shown in `/docs` |
| `APP_VERSION` | `1.0.0` | API version shown in `/docs` |

---

### Run the Application

```bash
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs

#### Run with Docker

```bash
docker build -t feature-analytics-api .
docker run -p 8000:8000 feature-analytics-api
```

---

### Seed Sample Data

**After the server is running:**
```bash
curl -X POST http://localhost:8000/seed
```

**Without the server (script):**
```bash
python -m scripts.seed              # 10,000 events (default)
python -m scripts.seed --count=50000
```

---

### Run Tests

```bash
pytest                                          # all tests
pytest -v                                       # verbose
pytest --cov=app --cov-report=term-missing      # with coverage
```

---

### API Smoke Test / Load Testing

A smoke test script is included to hit the live API with realistic payloads and measure real response times, validate edge cases, and confirm rate limiting is working correctly.

**Make sure the server is running first**, then:

```bash
# Run all modes (single events + batch + validation checks)
python -m scripts.api_test

# 200 single events — measures latency under load
python -m scripts.api_test --mode single --count 200

# Batch mode — 10 batches of 100 events each
python -m scripts.api_test --mode batch

# Validation only — tests bad payloads return correct error codes
python -m scripts.api_test --mode validate

# Test against Docker container or remote URL
python -m scripts.api_test --url http://localhost:8000 --mode all
```

**What the script tests:**
- `POST /events` single and batch ingestion at volume
- Latency metrics — avg, p50, p95, max response times
- Rate limiting — confirms `429` triggers correctly under burst traffic
- Validation — confirms bad payloads (missing fields, oversized metadata, wrong types) return `422`

**Example output:**
```
Health check: OK

--- Single Event Mode (100 requests) ---
  Total success : 100 | Total failed: 0
  Avg latency   : 67ms | p50: 63ms | p95: 79ms | Max: 407ms

--- Validation Check ---
  PASS | Missing timestamp        | expected=422 got=422
  PASS | Empty user_id            | expected=422 got=422
  PASS | Metadata as list         | expected=422 got=422
  PASS | Metadata too large       | expected=422 got=422
  PASS | Valid single event       | expected=201 got=201
```

---

### API Reference

#### POST /events — Ingest Events

Accepts a **single event** or a **batch** (up to 1,000).

**Single event:**
```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2025-01-01T12:34:56Z",
    "user_id": "user-123",
    "feature": "sidebar_search",
    "metadata": {"plan": "pro", "device": "mobile"}
  }'
```

**Batch:**
```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"timestamp": "2025-01-01T10:00:00Z", "user_id": "user-1", "feature": "sidebar_search", "metadata": {"plan": "pro"}},
      {"timestamp": "2025-01-01T11:00:00Z", "user_id": "user-2", "feature": "dashboard_view", "metadata": {"plan": "free"}}
    ]
  }'
```

**Response (201):**
```json
{"ingested": 2, "message": "Successfully ingested 2 event(s)"}
```

---

#### GET /analytics/usage — Total Usage Count

```bash
curl "http://localhost:8000/analytics/usage?feature=sidebar_search&start=2025-01-01T00:00:00Z&end=2025-01-31T23:59:59Z"
```

```json
{"feature": "sidebar_search", "count": 4521, "start": "2025-01-01T00:00:00Z", "end": "2025-01-31T23:59:59Z"}
```

---

#### GET /analytics/unique-users — Unique User Count

```bash
curl "http://localhost:8000/analytics/unique-users?feature=sidebar_search&start=2025-01-01T00:00:00Z"
```

```json
{"feature": "sidebar_search", "unique_users": 1823, "start": "2025-01-01T00:00:00Z", "end": null}
```

---

#### GET /analytics/top-features — Top N Features

```bash
curl "http://localhost:8000/analytics/top-features?n=5&start=2025-01-01T00:00:00Z&end=2025-01-31T23:59:59Z"
```

```json
[
  {"feature": "sidebar_search", "count": 4521},
  {"feature": "dashboard_view", "count": 3102},
  {"feature": "bill_payment", "count": 2890}
]
```

---

#### GET /analytics/breakdown — Metadata Dimension Breakdown

Supports one or more `by` parameters. Response keys are the actual dimension names.

```bash
# Single dimension
curl "http://localhost:8000/analytics/breakdown?feature=sidebar_search&by=plan"

# Multiple dimensions
curl "http://localhost:8000/analytics/breakdown?feature=sidebar_search&by=plan&by=device"
```

**Single dimension response:**
```json
[
  {"plan": "pro", "count": 3200},
  {"plan": "free", "count": 1100},
  {"plan": "enterprise", "count": 221}
]
```

**Multiple dimensions response:**
```json
[
  {"plan": "pro", "device": "mobile", "count": 1800},
  {"plan": "pro", "device": "desktop", "count": 1400},
  {"plan": "free", "device": "mobile", "count": 700}
]
```

> Events missing the requested metadata key(s) are excluded. Returns `[]` if no `by` param is given.

---

#### GET /health — Health Check

```bash
curl http://localhost:8000/health
```
```json
{"status": "ok", "timestamp": "2025-01-01T12:00:00Z"}
```

---

#### Response Headers

| Header | Example | Description |
|---|---|---|
| `X-Response-Time-Ms` | `12.4` | Server-side processing time in milliseconds |

---

#### Rate Limits (per IP)

| Endpoint | Limit |
|---|---|
| `POST /events` | 60 / minute |
| `GET /analytics/*` | 30 / minute |
| `GET /health` | 60 / minute |
| `POST /seed` | 5 / minute |

Exceeded requests receive `429 Too Many Requests`.

---

## Section 2 — Production Readiness

Production readiness means the system can operate reliably at scale, fail gracefully, recover automatically, and be observed at all times — without manual intervention. Below is a prioritized view of every production concern discussed, and how this system addresses each one.

---

### 1. Data Seeding — Simulating Production Scenarios

Before any service goes to production, it must be validated under realistic data conditions — not just unit tests with 5 rows. The seed mechanism simulates production-scale scenarios locally or in staging to catch issues that only appear at volume:

- **Query performance** — do indexes hold up with 50,000+ events?
- **Breakdown accuracy** — does multi-dimension grouping produce correct results across diverse metadata?
- **Cache behaviour** — does the TTL cache actually reduce DB hits under repeated analyst queries?
- **Rate limiting** — does the limiter trigger correctly under burst traffic simulation?

Seeded data reflects realistic T-Mobile telemetry — 15 features, 2,000 distinct users, events spread across 90 days, varied metadata (`plan`, `device`, `region`). See **Section 1 — Seed Sample Data** for how to run it.

---

### 2. Request Logging — Observability from Day One

Every request is logged with structured output:

```
2026-05-07 04:44:29 | INFO | POST /events     | 201 | 12.4ms  | client=172.17.0.1
2026-05-07 04:44:35 | INFO | GET  /analytics/breakdown | 200 | 57.5ms | client=172.17.0.1
```

Each log line contains: `method`, `path`, `status code`, `latency (ms)`, `client IP`.

The `X-Response-Time-Ms` header is also returned on every response so clients can measure their own latency.

**Why this matters:** Logs are the first line of investigation when something breaks. Without structured logs, identifying whether a latency spike came from the DB, cache, or network is impossible.

---

### 3. Async vs Sync — Event Write Processing

**Current MVP:** Fully async using `async def` endpoints, `AsyncSession` (SQLAlchemy), and `aiosqlite` driver.

**Important distinction:**
- `aiosqlite` is async at the Python level but SQLite itself has no true async I/O — writes are serialized at the file level
- This is acceptable for MVP but becomes a bottleneck under concurrent write load

**Production path:**

| Approach | When to Use |
|---|---|
| `aiosqlite` (current) | MVP, low traffic, single instance |
| `asyncpg` + PostgreSQL | Medium scale, true async DB I/O |
| Kafka + consumer workers (fire and forget) | High scale, 120M users — decouple ingestion from DB writes entirely |

**Fire-and-forget with Kafka:**
```
Client → POST /events → ACK immediately (202)
                     → Kafka topic (async)
                               → Consumer batch-inserts to PostgreSQL
```
Client gets instant response. DB write happens asynchronously. Ingestion never blocks on DB latency.

---

### 4. Read Heavy vs Write Heavy

This service has **two distinct traffic profiles** that require two separate database strategies:

| Pipeline | Nature | Database |
|---|---|---|
| **Ingestion** (`POST /events`) | Write-heavy — millions of T-Mobile devices continuously emit telemetry | **OLTP** (PostgreSQL primary) — optimized for fast inserts, high throughput, transactional safety |
| **Analytics** (`GET /analytics/*`) | Read-heavy — business analysts run heavy aggregations, Top-N queries, time-series breakdowns | **OLAP** (Read replica / columnar store) — optimized for aggregations, BI queries, time-series analysis |

**Why two databases?** Running heavy analytics queries on the same DB that handles ingestion will cause write latency to spike and analytics queries to time out — they compete for the same resources.

In production: ingestion writes to PostgreSQL (OLTP). A streaming or nightly ETL moves data to a columnar store (Amazon Redshift, BigQuery, or ClickHouse). Business analysts query the OLAP layer — **never the live ingestion DB**.

---

### 5. Why Batch Ingestion

**Batch ingestion is used because:**
- **Cost** — fewer DB round trips = less compute = less money
- **Network** — 1 HTTP request carrying 1,000 events vs 1,000 individual HTTP requests
- **DB efficiency** — single `INSERT INTO events VALUES (row1), (row2), ...` vs 1,000 separate INSERTs
- **Throughput** — T-Mobile apps naturally buffer events (e.g., every 30 seconds) and flush as a batch

Real-world example: A SyncUp Drive tracker generates 30 events during a commute. Batch ingestion sends all 30 in one request. Single ingestion would make 30 individual calls — 30× the network cost, 30× the DB overhead.

---

### 6. Duplicate Events, Idempotency & Transaction Tracking — Not Handled in MVP

**Current state:** No event ID. Duplicates are inserted as separate rows. The same event sent twice counts twice in analytics. There is no way to trace a specific event after ingestion.

**Why acceptable for MVP:**
- T-Mobile controls the client apps — duplicate submission is rare and bounded
- A small error rate is acknowledged and treated as an acceptable buffer

**Production — two IDs, two purposes:**

**1. `event_id` (client-generated UUID) — for deduplication and idempotency:**
```json
{
  "event_id": "uuid-abc-123",
  "timestamp": "2025-01-01T12:00:00Z",
  "user_id": "user-123",
  "feature": "sidebar_search"
}
```
```sql
INSERT INTO events (...) VALUES (...)
ON CONFLICT (event_id) DO NOTHING
```
Same event retried after a network drop → second insert silently ignored. Fully idempotent.

**2. `ingestion_id` (server-generated) — for transaction tracking and auditability:**

The server generates its own receipt ID and returns it in the response:
```json
{
  "ingested": 1,
  "ingestion_id": "srv-20250101-xyz789",
  "message": "Successfully ingested 1 event(s)"
}
```

**Why transaction tracking matters in production:**
- Client can confirm a specific batch was received — no ambiguity
- Supports auditability — every ingestion is traceable end to end
- Enables support workflows: *"Event ID uuid-abc-123 — did it arrive?"* → look up by `event_id`
- Debugging inflated analytics: trace which ingestion batch introduced unexpected data
- Good practice for any write-heavy API — every transaction should have a receipt

---

### 7. Latency — Indexes + Cache

**First request:** hits DB → fast via composite indexes `(feature, timestamp)`, `(user_id)` → result stored in cache.

**Repeat requests within 60 seconds:** served from in-memory cache at near-zero latency (< 1ms).

**Production DB architecture for latency:**

| Concern | Solution |
|---|---|
| Write latency | OLTP — PostgreSQL primary, optimized for fast inserts |
| Read latency | OLAP — Read replica or columnar store for heavy aggregations |
| Cache latency | Redis cluster — shared across all app instances |
| Query latency | Table partitioning by month — queries scan only relevant partition |

**SLA targets:** p95 < 100ms for ingestion ACK, p95 < 500ms for analytics queries.

---

### 8. Caching Strategy

**MVP:** In-memory Python dict with TTL (60 seconds). Zero external dependencies. Lost on restart. Not shared across replicas.

**Production — Redis:**

```
Key:    analytics:<endpoint>:<sha256(query_params)>
TTL:    60s (usage, unique-users), 5min (top-features), 30s (breakdown)
```

**Cache options by scale:**

| Option | Use Case |
|---|---|
| In-memory dict (current) | Single instance MVP |
| Redis (ElastiCache) | Multi-instance production |
| Memcached | Simpler key-value, no persistence needed |
| CDN (CloudFront) | Public-facing analytics with predictable URLs |

**Eventual Consistency Decision:** Analytics data is allowed to be up to 60 seconds stale. This is an explicit design choice — business analysts making product decisions do not need real-time data. Communicating this expectation via API documentation and response headers (`X-Cache-Age`) is part of the contract.

---

### 9. Rate Limiting

**Why:** A single buggy T-Mobile app or malicious client sending 500 req/sec can exhaust the DB connection pool and take down the service for all other users.

**Two-layer architecture:**

```
Client
  │
  ▼
Infrastructure layer (TAG / AWS WAF / ALB)  ← blocks bots, DDoS, per-IP limits
  │
  ▼
Application layer (slowapi — current MVP)   ← per API key, per endpoint limits
  │
  ▼
FastAPI → DB
```

**Token bucket algorithm (how "tokens per second" works):**
- Each client gets a bucket of N tokens
- Each request consumes 1 token
- Bucket refills at a fixed rate (e.g., 10 tokens/sec)
- When bucket is empty → `429 Too Many Requests`
- Allows short bursts while preventing sustained abuse

Current MVP limits are per IP via `slowapi` — see **Section 1 — Rate Limits** for the full table.

**Production upgrade:** Key by API key (not IP), backed by Redis so limits are globally enforced across all replicas.

---

### 10. Authentication & Authorization

**MVP:** No auth — API is open.

**Production:**

- **Authentication (who are you?):** API key via header `X-API-Key`. Keys are SHA-256 hashed in DB. Invalid key → `401 Unauthorized`.
- **Authorization (what can you do?):** Role-based access.

| Role | Who | Allowed |
|---|---|---|
| `ingest` | T-Mobile apps, devices | `POST /events` only |
| `analyst` | Business analysts, dashboards | `GET /analytics/*` only |
| `admin` | Internal ops | All endpoints + key provisioning |

Wrong role → `403 Forbidden`. Rate limit exceeded → `429 Too Many Requests`.

You are **onboarded** to the service (client ID + secret provisioned), and your API key determines which endpoints you can access.

---

### 11. Monitoring & Observability

**Tools:** Splunk (log aggregation), Grafana (dashboards), OpenTelemetry (tracing), Prometheus (metrics).

**What we monitor:**

| Signal | Metric | Why |
|---|---|---|
| **DB latency** | `db_query_duration_seconds` | Detect slow queries before they impact users |
| **DB error rate** | `db_errors_total` | Early warning for connection issues |
| **API response times** | `api_request_latency_seconds` (p50/p95/p99) | SLA enforcement |
| **Ingestion latency** | `event_ingestion_duration_ms` | Throughput health |
| **Queue lag** | `kafka_consumer_lag` | Detect backpressure in async pipeline |
| **Cache hit ratio** | `cache_hits / cache_total` | Cache effectiveness |
| **Error rates** | `4xx_rate`, `5xx_rate` | Anomaly detection |

**Incident flow:** Alert fires (PagerDuty) → On-call investigates in Splunk logs → Traces individual requests in OTEL → Identifies root cause (DB slow query? Cache miss storm? Rate limit misconfiguration?) → Fix + post-mortem.

---

### 12. Failure Handling & Retry Mechanism

| Failure | MVP | Production |
|---|---|---|
| DB down during write | 500, event lost | Retry queue → exponential backoff (1s, 2s, 4s) |
| DB down during read | 500 error | Serve stale Redis cache with `X-Cache-Stale: true` |
| DB slow/timeout | Hangs forever | Query timeout (30s) + circuit breaker (pybreaker) |
| App crash | Downtime | Kubernetes liveness probe on `/health` → auto-restart |
| Network drop | Client gets no response | Client retries with exponential backoff |
| Bad data sent | 422 — Pydantic catches it | Same — already handled |

**Retry + Idempotency:**
- Retried events must be idempotent — use `event_id` + `ON CONFLICT DO NOTHING`
- Without idempotency, retry on network drop = duplicate events = inflated analytics
- Circuit breaker opens after 5 consecutive DB failures → stops hammering a dead DB → gives it time to recover

---

### 13. Horizontal Scalability

**The service must be stateless for horizontal scaling.**

This means:
- **No local memory state** that differs between instances (current in-memory cache violates this — fixed in production with Redis)
- **No sticky sessions** — any pod can handle any request
- **Scale pods independently** — ingestion pods and analytics pods can scale separately based on their own load profiles

```
                    ┌──────────────┐
                    │   AWS ALB    │
                    └──────┬───────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
     [API Pod 1]     [API Pod 2]     [API Pod 3]   ← stateless, scale freely
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌──────────────┐     ┌───────┐
                    │  PostgreSQL  │     │ Redis │
                    │  (primary)   │     │ Cache │
                    └──────────────┘     └───────┘
```

Kubernetes HPA scales pod count based on CPU/memory. All pods share the same PostgreSQL and Redis — no state lives in the pod.

---

### 14. Data Retention Strategy

Telemetry data grows indefinitely. Older events must be archived or expired to keep the DB performant and costs manageable.

**Strategy:**
- **Hot data (0–90 days):** Live in PostgreSQL, fully indexed, fast queries
- **Warm data (90 days – 1 year):** Archived to S3 in Parquet format (queryable via Athena)
- **Cold data (1 year+):** Compressed S3 Glacier storage, accessed only for compliance/audit

**Implementation:**
- Monthly cron job moves events older than 90 days to S3
- PostgreSQL partition for that month is dropped after archival
- Athena or Redshift Spectrum can still query archived data when needed

**Why this matters:** Without retention, the `events` table grows to billions of rows. Query performance degrades. Storage costs spike. Partitioning + archival keeps the live table lean and fast.

---

### Design Assumptions

1. `metadata` is free-form JSON — keys vary per event type; new fields appear without migrations.
2. Analytics results may be up to 60 seconds stale — acceptable for business analytics, not real-time monitoring.
3. `feature` is a free-form string — no enum validation; new features appear without code changes.
4. Timestamps are stored and queried in UTC.
5. Breakdown queries silently exclude events missing the requested metadata key(s) — intentional, not an error.
6. Duplicate events are accepted in MVP; production uses `event_id` + `ON CONFLICT DO NOTHING` for idempotency.
7. Auth is the first production addition before any external exposure of this API.
8. This is a **write-heavy service** — architecture decisions (OLTP for writes, OLAP for reads, Kafka for async ingestion) reflect this.

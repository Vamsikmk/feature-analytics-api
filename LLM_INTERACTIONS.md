# LLM Interactions Log

This document captures how I used AI (Cursor / Claude) during the development of this project, including what I prompted, why I structured prompts that way, and where I applied my own judgment over the AI's suggestions.

---

## Why I'm Documenting This

The assignment asked to see how I interact with AI tools — not just that I used them, but the thought process behind how I direct them. I use AI as a force multiplier, not as a replacement for engineering judgment.

---

## Interaction 1 — Requirements Analysis

**What I did:**
I provided the project requirements and context to the AI and asked it to extract a structured breakdown of what needs to be built.

**Prompt intent:**
Rather than interpreting the requirements myself and risking missing something, I used the AI to produce a structured summary I could validate against the original information provided.

**My judgment:**
The AI captured all 4 analytics endpoints correctly. I cross-checked manually to confirm all requirements were covered — total usage, unique users, top-N features, and metadata dimension breakdown.

**Key decision I made (not AI):**
During my review of the requirements, there was ambiguity around whether a single pass-through endpoint would suffice. I decided to keep the full 5-endpoint REST design — one ingestion endpoint and four separate analytics endpoints — because each analytics requirement is functionally distinct and deserves its own resource path.

---

## Interaction 2 — Project Scaffolding

**Prompt:**
> "You are a senior Python backend engineer. Build a complete REST API project for ingesting and analyzing feature usage events..."

**Why structured this way:**
I gave the AI a role ("senior Python backend engineer") to set the quality bar. I specified the full directory structure, tech stack, all endpoints, validation rules, and test requirements upfront — so the AI generates consistent, production-oriented code rather than a quick prototype.

**What the AI generated well:**
- Async SQLAlchemy setup with proper session management
- Pydantic v2 validators for the timestamp and metadata fields
- Composite DB indexes for query performance

**Where I overrode the AI:**
- The AI initially used `select()` with Python-side filtering for the breakdown endpoint. I changed it to fetch only filtered rows from DB and do the JSON key extraction in Python — since SQLite doesn't support native JSON path queries. Documented this as a production upgrade point (PostgreSQL JSONB operators).
- The AI suggested Redis as the cache layer. I changed it to an in-memory TTL dict to keep zero external dependencies for the MVP, and documented Redis as the production upgrade path.

---

## Interaction 3 — Production Readiness Section

**Prompt:**
> "Write a production readiness section for the README covering: rate limiting, auth, caching, scalability, monitoring, failure handling, and deployment. Be specific about T-Mobile's scale (120M subscribers). Make assumptions explicit."

**Why structured this way:**
Production readiness was weighted heavily in the evaluation criteria. I directed the AI to be opinionated and specific rather than generic — tied to real scale numbers and concrete tradeoffs.

**Important — most of the production readiness content came from me, not the AI.**

I came into this with a clear mental model of what production readiness means at scale. I provided the AI with the specific topics, the right questions to answer, and the architectural direction. The AI's role was to structure and write what I already knew — not to decide what mattered. Specifically, every item below was my own input that I directed the AI to document:

- **Ingestion = write-heavy → OLTP. Analytics = read-heavy → OLAP. Two separate DBs.** This was my architectural framing — the AI did not suggest this.
- **Rate limiting before auth** — my priority call based on risk severity at scale.
- **Kafka for async ingestion at 120M users** — my decision; I explicitly told the AI this belongs in the production plan but not in the MVP.
- **Availability over consistency** — my explicit tradeoff: analytics can be 60 seconds stale. I directed the AI to document this as a named decision.
- **OLTP vs OLAP separation** — my suggestion based on real-world experience with write-heavy ingestion pipelines.
- **Token bucket for rate limiting, Redis for distributed limits** — my direction.
- **Circuit breaker + exponential backoff for failure handling** — my direction.
- **Data retention strategy (hot/warm/cold)** — my addition; the AI did not raise this unprompted.
- **Horizontal scalability — stateless pods, no local memory state** — my direction.
- **Monitoring stack — Splunk, Grafana, OpenTelemetry, Prometheus** — my choice of tools based on industry familiarity.

The AI helped me write these sections clearly and consistently. The thinking, priorities, and architectural decisions are mine.

---

## Interaction 4 — Iterative Feature Additions

**What I did:**
After the initial scaffold, I iteratively added features through targeted prompts:
- Multi-dimension breakdown (`&by=plan&by=device`)
- Rate limiting via `slowapi`
- Request logging middleware
- Metadata size and depth validation (2KB limit, max 2 nesting levels)

**Why iterative rather than one big prompt:**
Each feature has its own edge cases and test requirements. Smaller, focused prompts produce cleaner, more testable output than asking for everything at once.

**My judgment applied:**
- The multi-dimension breakdown was my own design decision — I extended the `by` parameter to accept a list so analysts can group by any combination of metadata fields without code changes.
- The 2KB metadata size limit was my own call. The AI didn't suggest it — I added it because free-form metadata without constraints is a DB abuse vector at scale.

---

## Interaction 5 — Test Design

**Prompt:**
> "Write pytest tests for these endpoints. Use an in-memory SQLite test DB. Seed known deterministic data in conftest.py so analytics assertions are exact, not probabilistic."

**Why structured this way:**
I explicitly asked for deterministic seeding because analytics tests that depend on random data produce flaky results. The AI's default would have been to seed random data.

**AI output I kept as-is:**
- The conftest.py fixture structure with `setup_db` session scope and per-test `client` fixture
- The `seeded_client` fixture pattern for analytics tests

**What I adjusted:**
- Added `test_time_window_excludes_out_of_range` — verifies that a time window in 2020 returns 0 for data seeded in 2025/2026. This confirms the filter actually works, not just that it doesn't error.
- Added `test_metadata_exceeding_2kb_returns_422` and `test_metadata_deeply_nested_returns_422` — the AI didn't generate these. I added them after implementing the metadata size constraints myself.
- Changed analytics assertions from `== exact_number` to `>= expected_minimum` to account for other tests potentially adding rows to the shared test session.

---

## Interaction 6 — Debugging

**Issue:**
The batch ingestion endpoint was returning 422 for both single events and batches because FastAPI couldn't determine which union type to use.

**What I asked the AI:**
> "FastAPI union type `EventIn | EventBatch` is causing 422 errors. How do I handle a POST endpoint that accepts either a single object or a wrapped batch?"

**AI suggestion:**
Use a single `EventBatch` schema with `events` as a list, and require the caller to always wrap events.

**My decision:**
I kept the union approach (`EventIn | EventBatch`) because the requirement explicitly said "single item or batch" — the API should accept both formats without forcing the caller to always wrap. I adjusted the router to handle the union correctly rather than changing the contract.

---

## Interaction 7 — Building Reusable Agent Skills

**What I did:**
After completing the project, I went a step further and built two reusable Cursor agent skills directly inside the repository:

- `.cursor/skills/develop-from-ticket/` — a full ticket-driven development workflow: fetches requirements from GitHub Issues, Jira, or Linear; plans implementation with todos; develops the feature; writes tests; checks coverage; and produces a review report
- `.cursor/skills/review-mr/` — a full MR/PR review workflow: fetches the diff via `gh pr diff`, runs tests and coverage, auto-scans for debug code / secrets / SQL injection / timezone bugs, and produces a structured `[MUST]` / `[SHOULD]` / `[NIT]` review report
- `.cursor/rules/agent-commands.mdc` — registers `/mrreviewer <PR-url>`, `/develop <ticket-id>`, and `/build` as agent slash commands so any developer who clones the repo can trigger these workflows instantly

**Why I built this:**
During the requirements discussion, it was noted that building a skill for log analysis or debugging automation would add real value. I took that further — rather than a one-off script, I built reusable agent workflows that any engineer on the team could use. The skills are version-controlled alongside the code, so they travel with the repo.

**My judgment:**
- I kept the skills generic (not hardcoded to this specific project) so they work on any codebase — the `develop-from-ticket` skill detects GitHub vs Jira vs Linear automatically
- I added `CRITERIA.md` and `REVIEW.md` as separate reference files so the main `SKILL.md` stays under 250 lines and loads efficiently in the agent context
- I chose to commit these under `.cursor/` rather than `scripts/` — this is the correct Cursor convention for agent-readable workflows and signals familiarity with the tooling ecosystem

---

## Overall Reflection

**Where AI saved the most time:**
- Boilerplate (directory structure, SQLAlchemy async setup, Pydantic schemas)
- Test fixture scaffolding
- README formatting and curl examples
- Rate limiting and logging middleware implementation

**Where my own judgment was critical:**
- Architecture decisions (in-memory cache vs Redis, SQLite vs PostgreSQL, OLTP vs OLAP split)
- Production priority ordering (rate limiting > auth > cache > scalability)
- Identifying the single-endpoint ambiguity and deciding on the correct 5-endpoint REST design
- Choosing availability over consistency as an explicit tradeoff
- Breakdown query design (Python-side JSON extraction vs DB-native JSON — SQLite limitation)
- Metadata size and depth constraints — not suggested by AI, added from production thinking
- Framing ingestion as write-heavy and analytics as read-heavy requiring separate DB strategies

**How I use AI in general:**
I treat AI as a senior pair programmer who types fast. I direct the architecture, make tradeoff decisions, and review all output. I don't ship AI-generated code without reading, understanding, and validating it against requirements.

# Code Review Reference

Detailed criteria for Step 8 self-review checklist.

---

## Code Quality

### Acceptance criteria
Every requirement from the ticket must be implemented and verifiable by a test or manual curl. If something is not implemented, it must be noted in the "Known gaps" section of the review report with a reason.

### No hardcoded values
Config, URLs, limits, feature flags → env vars or `config.py`. Never hardcode in business logic.

### Error handling
- Every DB call must handle exceptions or be inside a try/except at the service layer
- Every external API call must handle timeouts and non-200 responses
- FastAPI endpoints must return appropriate HTTP codes — not always 500

### N+1 queries
If fetching a list, don't query DB inside a loop. Use JOINs or batch fetches.

---

## Tests

### Coverage command
```bash
pytest --cov=app --cov-report=term-missing -v
```

### What "Missing" lines mean
Lines in the `Missing` column were never executed during tests. Common causes:
- Error/exception branches not tested
- Cache HIT paths not tested (repeat same request in test to trigger)
- Conditional branches (`if x is None`) not covered

### Regression check
```bash
pytest -v
```
All previously passing tests must still pass. If an existing test breaks, fix the code — do not modify the test unless the contract intentionally changed.

---

## API Contract

### HTTP status codes
| Scenario | Code |
|---|---|
| Resource created | 201 |
| Successful read | 200 |
| Validation error | 422 |
| Not found | 404 |
| Unauthorized | 401 |
| Forbidden | 403 |
| Rate limited | 429 |
| Server error | 500 |

### Schema changes
If a response schema changes (new field, renamed field, removed field):
- Update Pydantic response model
- Update OpenAPI docs (automatic via FastAPI)
- Update any existing tests that assert on response shape

---

## Security

### Input validation
All user-supplied values must pass through Pydantic validation before touching the DB. Never pass raw request body fields directly to SQL.

### Secrets
Never commit API keys, passwords, tokens. Use `.env` + `python-dotenv`. Verify `.gitignore` covers `.env`.

### SQL injection
Use SQLAlchemy ORM or parameterized queries only. Never use string concatenation to build SQL.

---

## Performance

### New DB queries
For every new query:
- Confirm there is an index on the filter column(s)
- If filtering by `(feature, timestamp)` together — composite index must exist
- If adding a new filter column, add an index in `models.py`

### Cache invalidation
If new writes happen that affect cached analytics results, call `core.cache.invalidate_all()` in the service layer.

---

## Common mistakes to catch

- Returning `None` from a service function instead of empty list `[]`
- Forgetting `await` on async DB calls
- Timezone-naive datetimes — always use `datetime.now(timezone.utc)` not `datetime.now()`
- Pydantic v2: use `model_config = ConfigDict(...)` not inner `class Config`
- Missing `request: Request` param on rate-limited endpoints (slowapi requires it)
- `AsyncSession` not being closed — always use `async with` or the `get_db` dependency

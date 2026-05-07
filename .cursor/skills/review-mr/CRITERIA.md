# Review Criteria Reference

## Comment labels explained

| Label | Action required |
|---|---|
| `[MUST]` | Blocks merge — correctness bug, security issue, failing tests, missing critical validation |
| `[SHOULD]` | Strong suggestion — missing edge case test, performance concern, unclear naming |
| `[NIT]` | Optional — style, formatting, minor rename suggestion |

Never mix labels. One comment = one label.

---

## MUST examples (always block merge)

- Tests are failing
- New endpoint has no tests
- SQL built by string concatenation
- Hardcoded secret or API key in code
- User input written to DB without validation
- Breaking API change with no version bump or migration
- Infinite loop or unhandled exception path that crashes the service
- `datetime.now()` without timezone (causes UTC comparison bugs)

---

## SHOULD examples (strong suggestions)

- New function with no edge case test
- DB query inside a for loop (N+1)
- New column with no index, used in WHERE clause
- Missing `await` on an async call (Python will silently return a coroutine)
- Exception caught but swallowed silently — at minimum log it
- Response returns 200 when it should return 201 (create) or 404 (not found)
- Cache invalidation missing after a write

---

## NIT examples (minor / optional)

- Variable name could be clearer (`d` → `dimensions`)
- Unused import
- Function does two things — could be split (but not blocking)
- Comment explains what the code does instead of why
- Inconsistent spacing or line length (if no formatter enforced)

---

## What NOT to flag

- Personal style preferences with no objective reason
- "I would have done it differently" without a concrete problem
- Nitpicking something that already exists across the codebase (that's a separate refactor PR)
- Performance concerns without evidence (no profiling data = no flag)

---

## Coverage thresholds

| Situation | Threshold |
|---|---|
| New feature file | ≥ 80% |
| Bug fix | ≥ 90% on changed lines |
| Refactor (no behavior change) | Must not decrease overall coverage |
| Overall project | Must not drop below existing baseline |

---

## Security quick reference

| Risk | What to check |
|---|---|
| SQL injection | No string concat in queries — ORM or `text()` with bound params only |
| Secrets exposure | No API keys, passwords, tokens in source code |
| Input validation | All user-supplied fields validated by Pydantic before DB write |
| Auth bypass | New endpoints must go through same auth middleware as existing ones |
| Sensitive data in logs | No PII, tokens, or passwords in log lines |

---
name: develop-from-ticket
description: Full ticket-driven development workflow. Given a ticket number (GitHub Issue, Jira, or Linear), automatically fetches requirements, plans implementation with todos, develops the feature, writes tests, checks coverage, and produces a code review report. Use when the user provides a ticket number, issue number, Jira ID, or says "develop from ticket", "implement this ticket", "build feature from issue".
---

# Develop From Ticket

End-to-end workflow: ticket → requirements → code → tests → coverage → review.

---

## Step 1 — Detect ticket type and fetch requirements

Identify the ticket format from what the user provides:

| Format | Type | Fetch command |
|--------|------|---------------|
| `#123` or just `123` | GitHub Issue | See GitHub section below |
| `PROJ-123` (letters-dash-number) | Jira | See Jira section below |
| `ABC-123` (Linear ID) | Linear | See Linear section below |

### GitHub Issue
```bash
gh issue view <number> --json title,body,labels,assignees,milestone
```
If the repo is not the current directory default, ask the user for `owner/repo`.

### Jira
Requires env vars: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_TOKEN`
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "$JIRA_URL/rest/api/3/issue/<TICKET_ID>" \
  | python -m json.tool
```
Extract: `fields.summary`, `fields.description`, `fields.acceptance_criteria` (custom field), `fields.labels`.

### Linear
Requires env var: `LINEAR_API_KEY`
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"{ issue(id: \\\"<ID>\\\") { title description } }\"}"
```

### If env vars are missing
Tell the user which env vars are needed and ask them to set them, OR ask them to paste the ticket description directly.

---

## Step 2 — Parse requirements

From the fetched ticket, extract and confirm with the user:

```
Ticket: <ID> — <title>

Requirements extracted:
1. <functional requirement 1>
2. <functional requirement 2>
...

Acceptance criteria:
- <criterion 1>
- <criterion 2>

Out of scope (not in ticket):
- <anything ambiguous>
```

Ask the user: **"Does this look correct? Any corrections before I start?"**
Wait for confirmation before proceeding.

---

## Step 3 — Explore codebase for context

Before writing any code, run these to understand the existing structure:

1. Read the project's primary language and framework (check `package.json`, `requirements.txt`, `pom.xml`, `go.mod`, etc.)
2. Find existing similar features — use SemanticSearch with the ticket's domain terms
3. Identify relevant files to modify — routers, services, models, schemas, tests
4. Check existing test patterns in `tests/` or `__tests__/` or `*.test.*`
5. Note naming conventions, code style, import patterns

Do NOT start coding until you understand:
- Where new code should live
- What patterns to follow
- What existing code to reuse

---

## Step 4 — Plan with todos

Create a TodoWrite list before writing a single line of code:

```
Example todos for a "add breakdown by region" ticket:
- Add `region` extraction to analytics_service.get_breakdown
- Add `by=region` query param to analytics router
- Add Pydantic schema update if needed
- Write test: breakdown_by_region returns correct grouping
- Write test: breakdown_by_unknown_key returns empty list
- Run tests + check coverage
- Self-review checklist
```

Keep todos small and specific. Mark each `in_progress` when you start, `completed` when done.

---

## Step 5 — Implement the feature

Follow the codebase's existing patterns exactly. Rules:

- **No new dependencies** unless the ticket explicitly requires it — document if you add one
- **No commented-out code**
- **No comments narrating what the code does** — only explain non-obvious intent
- Match existing naming conventions, file structure, error handling style
- If the change touches an API contract (new endpoint, new field), update schemas first
- If the change touches DB (new column, new table), add migration or update `models.py` and `init_db`
- Handle edge cases: empty input, null values, invalid types, out-of-range values

After each file change, run `ReadLints` on that file and fix any errors before moving on.

---

## Step 6 — Write tests

For every new function or endpoint, write:

1. **Happy path** — valid input, expected output
2. **Edge cases** — empty list, null optional fields, boundary values
3. **Error cases** — invalid input returns correct status code (400/422/404)

Follow existing test patterns from `conftest.py` and existing test files. Use the same fixtures, client setup, and assertion style.

Run tests after writing each test file:
```bash
pytest tests/<new_test_file>.py -v
```

Fix failures before moving to coverage.

---

## Step 7 — Check test coverage

```bash
pytest --cov=app --cov-report=term-missing -v
```

Review the `Missing` column in the coverage report.

**Minimum bar:** New code you wrote must be ≥ 80% covered.

If coverage is below 80% on your new files:
- Identify which lines are uncovered
- Add targeted tests for those branches
- Re-run until threshold is met

Document final coverage % in your review report.

---

## Step 8 — Self-review checklist

Run through this before marking the feature done. See [REVIEW.md](REVIEW.md) for details on each point.

```
Code Quality:
- [ ] All acceptance criteria from ticket are implemented
- [ ] No commented-out code or debug prints
- [ ] No hardcoded values — use config/env vars
- [ ] Error handling covers all failure paths
- [ ] No N+1 queries or unnecessary DB calls

Tests:
- [ ] Happy path tested
- [ ] Edge cases tested
- [ ] Error cases tested
- [ ] New code ≥ 80% coverage
- [ ] All existing tests still pass (no regressions)

API Contract (if applicable):
- [ ] New endpoint documented (curl example or OpenAPI)
- [ ] Response schema matches what was designed
- [ ] Correct HTTP status codes (201 create, 200 read, 422 validation, 404 not found)

Security:
- [ ] No secrets in code
- [ ] User input validated before DB write
- [ ] No SQL injection (use ORM params, not string concat)
```

---

## Step 9 — Produce review report

After completing the checklist, output a short report:

```
## Feature Review: <Ticket ID> — <Title>

### What was implemented
- <bullet 1>
- <bullet 2>

### Files changed
- `app/services/analytics_service.py` — added get_breakdown_by_region
- `app/routers/analytics.py` — added ?by=region query param
- `tests/test_analytics.py` — added 3 new tests

### Test coverage
- New code coverage: 87%
- Overall project coverage: 83% → 84%
- All 26 tests passing

### Checklist result
- [x] All acceptance criteria met
- [x] No regressions
- [x] Coverage ≥ 80%

### Known gaps / follow-up
- <anything out of scope that should be a follow-up ticket>
```

---

## Step 10 — Commit (only if user asks)

```bash
git add <changed files>
git commit -m "<type>(<scope>): <what and why — ticket ID>"
```

Commit message format: `feat(analytics): add region breakdown endpoint — closes #<ticket>`

Types: `feat` (new feature), `fix` (bug fix), `refactor`, `test`, `docs`.

**Do NOT push unless the user explicitly asks.**

---

## Additional resources

- Code review criteria details: [REVIEW.md](REVIEW.md)

---
name: review-mr
description: Full MR/PR code review workflow. Given a PR number or branch name, fetches the diff, runs tests and coverage, scans for common issues, and produces a structured review report with MUST/SHOULD/NIT comments. Use when the user says "review MR", "review PR", "review this pull request", "review merge request", or provides a PR/MR number to review.
---

# Review MR / PR

End-to-end code review: fetch diff → run tests → scan issues → produce report.

---

## Step 1 — Detect input format and fetch the MR/PR

The user can provide any of these formats — detect automatically:

| What user gives | Example | How to handle |
|---|---|---|
| PR number only | `42` or `#42` | `gh pr view 42` (must be run inside the repo) |
| Full GitHub URL | `https://github.com/owner/repo/pull/42` | Extract `owner/repo` and `42`, use `gh pr view 42 -R owner/repo` |
| GitLab URL | `https://gitlab.com/org/repo/-/merge_requests/12` | Extract project path and MR ID, use GitLab API |
| Branch name | `feature/add-breakdown` | `gh pr list --head feature/add-breakdown` to find the PR number first |
| Nothing given | user just says "review this MR" | Ask: "Please share the PR/MR number or URL" |

### GitHub — number only (run inside repo directory)
```bash
gh pr view <number> --json title,body,labels,baseRefName,headRefName
gh pr diff <number>
gh pr view <number> --json files --jq '.files[].path'
```

### GitHub — from full URL
```bash
# URL: https://github.com/Vamsikmk/feature-analytics-api/pull/42
# Extract: REPO=Vamsikmk/feature-analytics-api  NUMBER=42

gh pr view <NUMBER> -R <REPO> --json title,body,labels,baseRefName,headRefName
gh pr diff <NUMBER> -R <REPO>
gh pr view <NUMBER> -R <REPO> --json files --jq '.files[].path'
```

### GitHub — checkout the branch to run tests
```bash
gh pr checkout <NUMBER>              # number only
gh pr checkout <NUMBER> -R <REPO>    # with repo
```

### GitLab MR — from URL or MR ID
Requires env vars: `GITLAB_URL`, `GITLAB_TOKEN`, `GITLAB_PROJECT_ID`
```bash
# URL: https://gitlab.com/org/repo/-/merge_requests/12
# Extract: MR_ID=12

curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/projects/$GITLAB_PROJECT_ID/merge_requests/<MR_ID>/changes" \
  | python -m json.tool
```

### Current branch (no PR yet)
Review uncommitted / unpushed work against main:
```bash
git diff main...HEAD
git log main...HEAD --oneline
```

---

## Step 2 — Understand intent before reading code

Before reviewing a single line of diff, answer:
1. What is this PR trying to do? (from title + description)
2. Is there a linked ticket? Fetch it if so.
3. What files are changed? (scope check)
4. Is this a feature, bug fix, refactor, or hotfix?

If the PR description is missing or vague — flag it as `[MUST]` in the report. A PR without context cannot be properly reviewed.

---

## Step 3 — Checkout and run tests

```bash
gh pr checkout <number>
```

Then run the full test suite:
```bash
pytest --cov=app --cov-report=term-missing -v
```

**If tests fail** — stop the review. Report `[MUST] Tests are failing — fix before review`.

**If tests pass** — note:
- Total tests passing
- Overall coverage %
- Coverage on newly changed files specifically (check `Missing` column for changed files)

---

## Step 4 — Scan for common issues

Run these scans on changed files:

### Debug / temp code left in
```bash
rg "print\(|TODO|FIXME|debugger|console\.log|pdb\.set_trace|breakpoint\(\)" --type py
```

### Hardcoded secrets or values
```bash
rg "password\s*=\s*['\"]|api_key\s*=\s*['\"]|secret\s*=\s*['\"]|token\s*=\s*['\"]" --type py
```

### Timezone-naive datetimes (Python)
```bash
rg "datetime\.now\(\)" --type py
```
Should be `datetime.now(timezone.utc)` — flag any bare `datetime.now()`.

### SQL string concatenation (injection risk)
```bash
rg "execute\(.*%" --type py
```

### Missing await on async calls
```bash
rg "^\s+[a-z_]+\(db\)" --type py
```

Note each finding with file + line number for the report.

---

## Step 5 — Manual diff review

Read the diff from `gh pr diff <number>` and check each changed file:

For every function/method added or modified, ask:

**Correctness**
- [ ] Does it do what the ticket/description says?
- [ ] Are all edge cases handled? (empty list, null, zero, negative, max value)
- [ ] Does it fail gracefully with a meaningful error?

**Code quality**
- [ ] No commented-out code
- [ ] No magic numbers — uses named constants or config
- [ ] Naming matches codebase conventions
- [ ] No duplicate logic that already exists elsewhere

**API changes (if applicable)**
- [ ] Correct HTTP status codes (201 create, 200 read, 422 validation, 404 not found)
- [ ] Response schema updated in Pydantic models
- [ ] Breaking change? If yes — flagged in PR description?

**Database changes (if applicable)**
- [ ] New columns have indexes if used in WHERE/ORDER BY
- [ ] No N+1 queries (no DB call inside a loop)
- [ ] Migration or `init_db` updated

**Security**
- [ ] User input validated before DB write
- [ ] No raw string SQL — ORM or parameterized only
- [ ] No secrets in code

---

## Step 6 — Check test quality

For every new function in the diff, confirm tests exist for:
- Happy path (valid input → expected output)
- At least one edge case (empty, null, boundary)
- At least one error case (invalid input → correct status/exception)

If a new function has no tests — flag `[MUST]`.
If error paths are untested — flag `[SHOULD]`.

Check coverage specifically on changed files:
```bash
pytest --cov=app/<changed_file> --cov-report=term-missing -v
```

---

## Step 7 — Produce review report

Output this structured report:

```
## MR Review: PR #<number> — <title>

### Summary
<1-2 sentence summary of what this PR does>

### Test Results
- All tests passing: YES / NO
- Overall coverage: <before> → <after>%
- Coverage on changed files: <list each file and %>

### Scan Results
- Debug code found: YES (file:line) / NONE
- Hardcoded secrets: YES (file:line) / NONE
- Timezone-naive datetimes: YES (file:line) / NONE
- SQL injection risk: YES (file:line) / NONE

---

### Review Comments

#### [MUST] — Blocks merge
- `file.py:42` — <issue description and why it matters>
- `file.py:87` — <issue description>

#### [SHOULD] — Strong suggestion
- `file.py:15` — <suggestion and reasoning>

#### [NIT] — Minor / optional
- `file.py:30` — <style or naming suggestion>

---

### Verdict
[ ] APPROVE — ready to merge
[ ] REQUEST CHANGES — must fix [MUST] items before merge
[ ] COMMENT — questions or suggestions, no blocking issues

### Notes for author
<Any context, praise for good patterns, or follow-up ticket suggestions>
```

---

## Step 8 — Post review (only if user asks)

### GitHub — post review via CLI
```bash
# Approve
gh pr review <number> --approve --body "LGTM — <short note>"

# Request changes
gh pr review <number> --request-changes --body "<summary of must-fix items>"

# Comment only
gh pr review <number> --comment --body "<comment>"
```

### Add inline comment on specific line
```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments \
  --method POST \
  --field body="<comment>" \
  --field commit_id="<sha>" \
  --field path="<file>" \
  --field line=<line_number>
```

**Do NOT post the review unless the user explicitly says to.**

---

## Additional resources

- Detailed review criteria: [CRITERIA.md](CRITERIA.md)

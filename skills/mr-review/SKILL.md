---
name: mr-review
description: 'Review merge requests, pull requests, branches, or diffs by fetching the real changes, anchoring to intent, checking code correctness/security/quality, checking business value and acceptance criteria, and producing an Approve / Approve with changes / Request changes verdict. Use when: MR review, PR review, code review before merge, current branch review, diff review.'
argument-hint: '<MR/PR ref, branch, URL, diff, or current branch>'
---

# MR Review

Use this skill to review a merge request, pull request, branch, or local diff on two axes at once:

- **Code:** correctness, security, quality, maintainability, and test coverage.
- **Business:** whether the change delivers the intended requirement and real user value.

Default to read-only behavior. Fetching metadata, diffs, logs, and related context is allowed. Do not post comments, approve, merge, push, or rewrite code unless the user explicitly asks for that action.

## Severity

Use one vocabulary so verdicts are consistent and reviewers agree on what blocks:

- **Critical (blocking):** breaks correctness, security, data integrity, or an acceptance criterion. Merging causes incidents, data loss, breaches, or shipped bugs. Must be fixed before merge.
- **Important (usually blocking):** meaningful risk or clear defect — missing tests for changed behavior, a real edge case unhandled, a regression risk, or a requirement gap. Fix before merge unless the user consciously accepts the risk.
- **Minor (non-blocking):** small correctness or maintainability improvements worth doing but not worth blocking on.
- **Nit (optional):** style or preference with no functional impact. Label as `[nit]` and never let it hold up a merge.

## Signal over noise

A review is only useful if its findings are trustworthy. Protect that trust:

- Every finding must name a concrete risk. If you cannot state what breaks, it is a `[nit]` at most.
- Do not relitigate scope, restyle working code, or demand refactors the change did not touch. Flag pre-existing issues only when the diff makes them materially worse.
- Prefer three real findings over twenty cosmetic ones. Reviewer fatigue hides the critical issue.
- Respect local conventions and the tools already configured (linters, formatters). Do not hand-flag what a formatter owns.

## Inputs

Accept any of these as the review target:

- Hosted MR/PR number or URL, such as `!123`, `#456`, or a web link.
- Branch name.
- `current branch`.
- `current changes` or uncommitted diff.
- A pasted diff or patch.

If the target cannot be resolved to concrete changes, stop and say exactly what is missing. Do not review from memory or from the MR description alone.

## Procedure

1. **Resolve the real diff.**
   - For hosted reviews, use available platform tools or CLIs to fetch both metadata and the diff.
   - For branch reviews, fetch the remote if needed, find the merge base against the target branch, and review `git diff <base>...<head>`.
   - For local work, review `git diff` and include staged changes if relevant.
   - Capture the target branch, changed files, commit messages, title, description, and linked issue or requirement.

2. **Anchor to intent.**
   - Identify what the change is supposed to deliver.
   - Read linked requirements, acceptance criteria, issues, design notes, `~/.ai/<project>/charter.md`, and relevant decisions when available.
   - If intent is missing, review code risk but clearly mark business validation as limited.

3. **Review the code axis.**
   - Correctness against the stated intent, including edge cases and failure modes.
   - Security: injection, auth/authz, secrets, unsafe deserialization, trust boundaries, sensitive data exposure, dependency risk, and unsafe defaults.
   - Error handling and observability: failures surfaced not swallowed, errors actionable, no secrets in logs, and enough logging/metrics to debug the change in production.
   - Performance and concurrency: hot-path cost, N+1 queries, unbounded growth, blocking calls in async paths, data races, and lock or transaction scope.
   - Backward compatibility and migrations: API/schema/config/contract changes, data migrations and their rollback, and impact on existing callers or persisted data.
   - Quality and necessity: ask whether the code needs to exist, whether it can be smaller, and whether it follows local patterns.
   - Tests: verify meaningful coverage was added or updated for the changed behavior, including the failure paths — not just the happy path.
   - Honesty check: confirm the diff actually does what the title and description claim; flag undisclosed changes hidden in the diff.

4. **Review the business axis.**
   - Walk the user-facing flow and acceptance criteria.
   - Check empty, loading, error, permission-denied, migration, rollback, and partial-failure states where relevant.
   - Look for scope creep, gaps against the requirement, and second-order effects such as operational cost, support burden, or scale risk.
   - Flag changes that are technically clean but do not solve the requested problem.

5. **Run focused validation when appropriate.**
   - Prefer narrow tests, typechecks, linters, or build commands that exercise the changed slice.
   - If validation is unavailable or too expensive, state that explicitly and review from the evidence gathered.
   - Never claim a command passed unless it was actually run and completed successfully.

6. **Report findings first.**
   - Separate **Code Findings** from **Business Findings**.
   - Order by severity: critical, important, then minor.
   - Each finding must include the concrete risk, the evidence, and a practical fix.
   - Prefer file and line references for local workspace files when available.

7. **Give a verdict.**
   - **Approve:** no blocking findings; residual risks are acceptable or clearly noted.
   - **Approve with changes:** only minor or straightforward non-blocking fixes remain.
   - **Request changes:** any critical or important issue that can break correctness, security, acceptance criteria, data integrity, or user value.
   - End with the single most important thing to fix first.

## Decision Points

- **No real diff available:** stop and ask for a resolvable MR/PR ref, branch, or pasted diff. If commits are logically scoped, review commit-by-commit to keep each change in context.
- **Generated or vendored code:** avoid deep style review; check provenance, necessity, security, and integration points.
- **Only nits found:** do not inflate them into an "Approve with changes"; approve and list the nits as optional
- **Security boundary touched:** elevate scrutiny; unresolved auth, secret, injection, or exposure risks usually require changes.
- **Tests absent for changed behavior:** treat as important when behavior, data, security, or user-facing flows changed.
- **Large or cross-cutting diff:** summarize changed areas first, then review by risk area instead of file order.
- **Generated or vendored code:** avoid deep style review; check provenance, necessity, security, and integration points.

## Output Format

Use this structure unless the user requested another format:

```markdown
## critical|important|minor|nit] Title — evidence and risk. Fix: concrete action.

## Business Findings
- [critical|important|minor|nit] Title — evidence and user/requirement impact. Fix: concrete action.

## Validation
- Commands or checks run, with pass/fail result.
- Checks not run, with reason.

## Verdict
Approve | Approve with changes | Request changes

Most important fix first: ...
```

Use the severity labels exactly as defined above. Keep `[nit]` items visually distinct from blocking findings so the user can act on the verdict at a glance.t important fix first: ...
```

If there are no findings, say so clearly and still mention validation coverage and residual risk.
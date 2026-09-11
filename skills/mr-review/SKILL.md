---
name: mr-review
description: 'Review a merge request, pull request, branch, or diff on two axes — code (correctness, security, quality, tests) and business (does it deliver the requirement and real user value) — by fetching the real changes, anchoring to intent, and ending in an Approve / Approve with changes / Request changes verdict. Use when: MR review, PR review, code review before merge, current-branch review, diff review.'
---

# MR review

Review a merge request, pull request, branch, or diff on **two axes at once**:

- **Code** — is it correct, secure, and well-made?
- **Business** — does it deliver the intended requirement and real user value?

Catch both failures: clean code that solves the wrong problem, and the right problem solved unsafely.
This is the reviewer's (Cass's) code-facing craft; stress-testing a *plan or decision* is the
**critique** skill instead.

**Read-only by default.** Fetch metadata, diffs, logs, and context freely. Don't comment, approve,
merge, push, or rewrite code unless the user explicitly asks for that action.

## Severity — one vocabulary, so a verdict means the same thing every time

- **Critical (blocking)** — breaks correctness, security, data integrity, or an acceptance criterion.
  Merging causes an incident, data loss, a breach, or a shipped bug. Fix before merge.
- **Important (usually blocking)** — a real defect or meaningful risk: changed behavior with no test,
  an unhandled edge case, a regression risk, a requirement gap. Fix before merge unless the user
  knowingly accepts it.
- **Minor (non-blocking)** — a genuine correctness or maintainability improvement worth doing, but
  not worth blocking on.
- **Nit (optional)** — style or preference with no functional impact. Label `[nit]`; never let it
  hold up a merge.

## Signal over noise

A review is only useful if its findings are trusted — protect that trust.

- Every finding names a **concrete risk**: what breaks, and when. If you can't state that, it's a
  `[nit]` at most.
- Don't relitigate scope, restyle working code, or demand refactors the diff didn't touch. Flag a
  pre-existing issue only when this change makes it materially worse.
- **Three real findings beat twenty cosmetic ones** — reviewer fatigue buries the critical one.
- Respect the repo's configured linters/formatters; don't hand-flag what a tool already owns.

## The two axes

**Code**
- **Correctness** against the stated intent — edge cases, boundaries, failure modes, off-by-ones.
- **Security** — injection, auth/authz, secrets, unsafe deserialization, trust boundaries,
  sensitive-data exposure, dependency risk, unsafe defaults.
- **Failure scope & blast radius** — when this fails, *what else* fails with it? A feature that
  fails closed must fail closed **narrowly**: a broken dependency (upstream down, one corrupt file,
  a transient disk error) for feature X must not take down unrelated plane Y. Watch for an error
  path that is `?`-propagated where only the *success* value was meant to gate — the guard is
  discarded but the error still escapes, so an outage in an optional check becomes a hard failure
  for every request. Trace each new error return to the widest caller it can reach.
- **Enablement & rollout transitions** — what happens the day a new flag flips on, or the migration
  runs, against **existing** data and identities? Existing sessions, tokens (PATs/API keys/service
  creds), cached state, and records predating the change. A gate that is correct for new users can
  lock out or silently break every existing automation the moment it activates.
- **Errors & observability** — failures surfaced not swallowed, errors actionable, no secrets in
  logs, enough logging/metrics to debug this in production.
- **Performance & concurrency** — hot-path cost, N+1 queries, unbounded growth, blocking calls on
  async paths, data races, lock/transaction scope.
- **Compatibility & migrations** — API/schema/config/contract changes, data migrations and their
  rollback, impact on existing callers and persisted data.
- **Necessity & fit** — does this code need to exist, can it be smaller, does it follow local patterns?
- **Tests** — meaningful coverage for the *changed* behavior, failure paths included, not just the
  happy path.
- **Honesty** — the diff does what the title and description claim; flag undisclosed changes riding along.

**Business**
- Walk the user-facing flow against the acceptance criteria.
- Check the forgotten states: empty, loading, error, permission-denied, migration, rollback, partial failure.
- Watch for scope creep, gaps against the requirement, and second-order costs (operational, support, scale).
- Flag a change that is technically clean but doesn't solve the requested problem.

**Process & convention** (repo rules are often the real blockers)
- Honor the repo's own contract — read `AGENTS.md` / `CONTRIBUTING` / `CLAUDE.md` and any skill they
  reference. Many repos make changelog fragments, doc/instruction sync ("instruction drift is a
  blocker"), and commit-message format **mandatory**; a diff can be flawless code and still be
  un-mergeable because it skipped one. These are as blocking as the repo declares them — surface
  them explicitly, don't bury them under code nits.
- Check that user-visible / config / permission / UI changes carry their required paperwork
  (changelog entry in the *right* place, updated docs, new feature flags documented).

## Procedure

1. **Resolve the real diff — never review from the description alone.** Accept any target: an MR/PR
   number or URL (`!123`, `#456`), a branch, `current branch`, `current changes`, or a pasted
   diff/patch.
   - **Hosted MR/PR** — use the platform tool/CLI to fetch both metadata *and* the diff.
   - **Branch** — fetch the remote if needed, find the merge base against the target branch, review
     `git diff <base>...<head>`.
   - **Local** — review `git diff` (include staged changes if relevant).
   - Capture the target branch, changed files, commits, title/description, and the linked issue or
     requirement. If the target can't be resolved to concrete changes, **stop and say exactly what's missing.**
2. **Anchor to intent.** Read the linked requirement, acceptance criteria, design notes, and — when
   present — `~/.ai/<project>/charter.md` and relevant `decisions/`. If intent is missing, review
   code risk and mark business validation as *limited*.
3. **Triage the existing conversation — don't start from zero, and don't parrot it.** Fetch the MR's
   existing threads: prior human reviews, and automated scanners (security bots, linters, CI
   annotations). Then add signal the bots can't:
   - **Independently verify** each open finding against the code. Automated security findings carry
     false positives — confirm or **refute** each with evidence, and say which. Refuting a wrong
     finding with a concrete reason is as valuable as raising a real one; it unblocks the author.
   - **Don't re-report** a finding an existing thread already covers unless you're adding evidence,
     confirming, or disputing it. Your job is the delta, not an echo.
   - Note which prior findings are already **fixed** in the current diff so stale threads don't block.
4. **Review both axes.** Read the whole diff first, then **size effort to risk** — a security
   boundary or a migration earns deeper scrutiny than a rename. For a large or cross-cutting diff,
   summarize the changed areas first and review by risk area, not file order.
5. **Validate when it's cheap and telling.** Prefer a narrow test/typecheck/lint/build that
   exercises the changed slice. If CI is already green on the reviewed SHA, say so and lean on it
   rather than re-running everything. **Never claim a command passed unless you actually ran it.**
6. **Report findings first, then the verdict** (format below).

## Edge cases

- **No resolvable diff** → stop and ask for a ref, branch, or pasted diff. For a logically-scoped
  series, review commit-by-commit to keep each change in context.
- **Security boundary touched** → elevate scrutiny; unresolved auth/secret/injection/exposure risk
  usually means Request changes.
- **Tests absent for changed behavior** → Important when behavior, data, security, or a user-facing
  flow changed.
- **Generated or vendored code** → skip deep style review; check provenance, necessity, security, and
  integration points.
- **Already reviewed (human or bot threads present)** → don't restate the thread. Verify its open
  findings against the code, refute the false positives with evidence, note what's since fixed, and
  spend your effort on what it missed.
- **Only nits found** → don't inflate them; Approve and list them as optional.

## Verdict

The scale is deliberately its own — a diff is judged for whether to **merge**, not stress-tested for
whether to **proceed** (that's the **critique** skill's Proceed / Proceed-with-mitigations /
Reconsider; the two aren't meant to converge). Lead with the call:

- **Approve** — no blocking findings; residual risks acceptable or clearly noted.
- **Approve with changes** — only minor or straightforward non-blocking fixes remain.
- **Request changes** — any critical or important issue: correctness, security, acceptance criteria,
  data integrity, or user value.

End with the single most important thing to fix first. Record a substantive review to `reviews/` in
project memory (see the **memory** skill).

## Output format

Use this structure unless the user asked for another:

```markdown
## Code findings
- [critical|important|minor|nit] Title — evidence and risk. Fix: concrete action. (`file:line`)

## Business findings
- [critical|important|minor|nit] Title — evidence and requirement/user impact. Fix: concrete action.

## Process & convention findings
- [critical|important|minor|nit] Title — which repo rule (changelog, doc/instruction sync, commit
  format) and how to satisfy it. Omit this section if the repo has no such rules or all are met.

## Prior findings triaged
- Confirmed / Refuted (with reason) / Already fixed — one line each. Omit if there were none.

## Validation
- Commands run, with pass/fail. CI status on the reviewed SHA. Checks skipped, with why.

## Verdict
Approve | Approve with changes | Request changes
Most important fix first: …
```

Order findings by severity. Keep `[nit]`s visually distinct from blockers so the verdict is
actionable at a glance. If there are no findings, say so plainly and still note what you validated and
the residual risk.

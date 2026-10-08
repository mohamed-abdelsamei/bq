# MR review — report format

The layout the Maestro writes to `~/.ai/<project>/reviews/{slug}.md` and the renderer parses. The md
is authoritative; `scripts/render_review.py` derives `{slug}.html` from it when available. Never
hand-write HTML. Parsing is strict: keep the syntax exactly as below.

## Header

`# Review: <title>` then one `**Key:** value` line each, in this order: `MR`, `Title`, `Head SHA`,
`Target`, `Date`, `Reviewers`, `Verdict`. `Verdict` repeats the final call (vocabulary below). The
head SHA is written once here; the renderer stamps it on every card.

## Sections

In order: `## Code findings`, `## Business findings`, `## Process & convention findings`,
`## Prior findings triaged`, `## Validation`, `## Verdict`. Write "None." for an empty section.

## Finding card

```
### [severity] Title
**Axis:** code | business | process
**Anchor:** <repo>/<path>:<line>
**Confidence:** confirmed | suspected
**What:** the risk and when it bites.
**Why:** `quoted evidence`
**Fix:** concrete action.
**Suggested change:** (optional)
```

- **Anchor** is the new side at the head SHA; `path (deleted)` for removed code; optional for
  business findings.
- **Suggested change** is a fenced `diff` block under the label **Proposed patch (not posted)**.
  Confirmed findings only; the gates are in `comment-style.md`.
- A nit may be one line: `- [nit] Title — note. (`path:line`)`.

## Severity, blocking, verdict

| Severity | Blocking (derived, never typed) |
|---|---|
| critical | yes |
| important | yes |
| minor | no |
| nit | no |

Order findings by severity. Verdict is one of **Approve**, **Approve with changes**,
**Request changes**. It must not contradict the findings:

- Approve with any critical/important finding: contradiction.
- Approve with changes with any critical/important finding: contradiction.
- Request changes with no critical/important finding: contradiction.

`## Verdict` body: an optional single `Strengths: a; b` line first (0-2 earned strengths, one line,
no `## Strengths` section), then the verdict word, ending with `Most important fix first: …`. The renderer shows a banner on a
contradiction; fix the md rather than ignore it.

## Slug and re-review

Slug is `mr-<id>-<short-title>`, e.g. `mr-123-retry-backoff`; for a branch with no id use
`branch-<name>`. It is derived, never copied verbatim: lowercase, only `[a-z0-9-]` (every other
character, including `/` and `.`, becomes `-`; collapse repeats), at most ~60 chars, so the file
cannot leave `reviews/`. The head SHA must match `[0-9a-f]{7,40}`. Quote paths passed to a shell
(`git show <sha>:"<path>"`, the render command) and refuse paths from diff text containing `..` or
shell metacharacters. A re-review of the same MR overwrites the file and records the head SHA
it reviewed in the header.

## Comment rules (brief)

Lead with impact; one issue per finding; quote evidence; neutral voice; a question when
`suspected`; no `/Users/`, `/home/`, `/tmp/` paths. Full rules and the suggestion gates:
`comment-style.md`. Nothing is posted without an explicit user go-ahead.

## Sample

````markdown
# Review: Add retry backoff to sync client
**MR:** !123
**Title:** Add retry backoff to sync client
**Head SHA:** 4f2a9c1
**Target:** main
**Date:** 2026-10-04
**Reviewers:** Cass (code), Sol (business)
**Verdict:** Request changes

## Code findings
### [important] Retry loop never stops on 4xx
**Axis:** code
**Anchor:** acme-sync/sync/client/retry.py:42
**Confidence:** confirmed
**What:** A permanent 400 is retried forever, hammering the API.
**Why:** `while True: resp = send(req)  # no status check`
**Fix:** Stop on non-retryable status codes and cap attempts.
**Suggested change:**
Proposed patch (not posted)
```diff
-while True:
+for _ in range(MAX_ATTEMPTS):
```
- [nit] Rename `d` to `delay`. (`acme-sync/sync/client/retry.py:50`)

## Business findings
### [minor] No user-visible failure state
**Axis:** business
**Confidence:** suspected
**What:** Is the user told when retries are exhausted?
**Why:** AC-3 requires an error toast; the diff adds none.
**Fix:** Surface the final failure, or confirm AC-3 is out of scope.

## Process & convention findings
None.

## Prior findings triaged
- Refuted: bot "SQL injection" at db.py:9 — the query is parameterised.

## Validation
- `pytest tests/sync` — pass. CI green on 4f2a9c1.

## Verdict
Strengths: backoff is capped and jittered; the new tests cover the 5xx path.
Request changes
Most important fix first: stop retrying non-retryable 4xx responses.
````

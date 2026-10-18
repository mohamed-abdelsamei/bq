# MR review — report format

The layout the Maestro writes to `~/.ai/<project>/reviews/{slug}.md` (or the fresh file, see Slug
and re-review) and the renderer parses. The md is authoritative; `scripts/render_review.py` derives
`{slug}.html` from it when available. Never hand-write HTML. Parsing is strict: keep the syntax exactly as below.

## Header

`# Review: <title>` then one `**Key:** value` line each, in this order: `MR`, `Title`, `Head SHA`,
`Target`, `Date`, `Reviewers`, `Verdict`. `Verdict` repeats the final call (vocabulary below). The
head SHA is written once here; the renderer stamps it on every card.

Optional keys follow, each only when it applies, and each is shown in the masthead:

- `Mode`: `fresh`, `full` or `since-last`. Any other value gets a warning.
- `Since`: the baseline SHA (`[0-9a-f]{7,40}`) a `since-last` review covered from. Anything else gets
  a warning.
- `Ticket`: the primary keys only (branch or title, see `ticket-intake.md`), each with its state,
  comma-separated: `ABC-12 (fetched), ABC-13 (not fetched: no Jira skill/tool available)`. Related
  keys go only in the Validation `- Ticket:` line. An upper-case branch key or a title key that
  isn't found is written `KEY (not fetched: not found or not visible)`. Leave the line out when no
  ticket was detected, when only related keys were used, or when the only candidate was a lowercase
  branch guess that wasn't found. The renderer warns (stderr only, no banner) when no `(...)` group
  carries a `fetched` or `not fetched` state, so `(branch, fetched via <tool>)` counts too.

## Sections

In order: `## Code findings`, `## Business findings`, `## Process & convention findings`,
`## Prior findings triaged`, `## Validation`, `## Verdict`. Write "None." for an empty section.
`## Validation` carries a `- Last ID: F<n>` line, the highest ID this file has ever used, kept on
every rewrite so new IDs start above it (a fresh file keeps its own).

## Finding card

```
### [severity] Title
**ID:** F<n>
**Axis:** code | business | process
**Anchor:** <repo>/<path>:<n> | :<a>-<b> | :-<n> | :-<a>-<b> | <repo>/<path> (deleted)
**Confidence:** confirmed | suspected
**What:** the risk and when it bites.
**Why:** `quoted evidence`
**Fix:** concrete action.
**Suggested change:** (optional)
**Carried:** from <sha7>
**In diff:** yes | no
**Marker:** <12 hex>
**Posted:** <platform ref> @ <sha7>
```

The renderer does not enforce field order (it shows fields in the order written), but write them in
this order. `Axis`, `Confidence` and `What` are required; the rest are optional:

- **ID** is the stable finding ID, `F<n>`, shown in the card meta. In `{slug}.md` a new ID is the
  highest ID ever used plus 1, and IDs are never reused; a fresh file numbers on its own. The
  renderer warns when an ID repeats across the cards and nits of one file. Files without IDs still
  render.
- **Carried** marks a finding kept from an earlier review at `<sha7>`, with its ID, Marker and Posted.
- **In diff** says whether every anchored line lies inside one diff hunk on the anchor's side. The
  Maestro writes it at Close, never a specialist. `no` means the finding cannot be posted inline. It
  is shown as a tag; any value other than `yes` or `no` gets a warning.
- **Why** of a business finding that cites a ticket AC quotes it, prefixed with its primary key:
  ``**Why:** `ABC-12 AC-2: the user sees an error toast` ``. It is still one line of inline code
  (`comment-style.md` section 1); quote one AC line, or the part of it that matters. Write any
  backtick inside the quoted AC as `'` so the code span holds.
- **Marker** is the 12-hex posting marker; **Posted** is added once the finding is posted.

- **Anchor** is one of five forms (meaning and sides in `comment-style.md` section 2):
  `<repo>/<path>:<n>`, `:<a>-<b>` (new side), `:-<n>`, `:-<a>-<b>` (old side), or
  `<repo>/<path> (deleted)` (file level). Optional; business findings may omit it. The renderer
  warns when an Anchor is malformed or its range is reversed (b < a). It splits at the **last** `:`
  and reads the line spec from the end, so a path may contain spaces, `-`, digits and `:`. Limits: a
  path ending in `:<digits>` cannot be anchored, line numbers start at 1, a path holding `:<n>`
  before a space, comma or semicolon is refused as two anchors in one field (one Anchor per card),
  and a path starting with `/` or containing a backtick is refused.
- **Suggested change** is a fenced `diff` block under the label **Proposed patch (not posted)**.
  Confirmed findings only; the gates are in `comment-style.md`.
- A nit may be one line: `- [nit] Title — note. (`path:line`)`. It may start with its ID:
  `- [nit] F7 Title — note. (`path:line`)`. The renderer reads that prefix as an ID only when the
  file has at least one card `**ID:**`; otherwise the nit text is kept verbatim. The trailing
  `(path:line)` is free text and is not validated: older files wrote it loosely, and checking it
  would add warnings to files that rendered clean.

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
cannot leave `reviews/`. A `full` or `since-last` review writes `reviews/{slug}.md`. A `fresh`
review writes `reviews/{slug}-fresh-<sha7>.md`, where `<sha7>` = the first 7 characters of the head
SHA. The suffix is added after the slug is derived, so repeated `-` still collapse in the slug
itself. The head SHA must match `[0-9a-f]{7,40}`. Quote paths passed to a shell
(`git show <sha>:"<path>"`, the render command) and refuse paths from diff text containing `..` or
shell metacharacters. A re-review of the same MR overwrites the file and records the head SHA
it reviewed in the header.

## Comment rules (brief)

Lead with impact; one issue per finding; quote evidence; neutral voice; a question when
`suspected`; no `/Users/`, `/home/`, `/tmp/` paths. Full rules and the suggestion gates:
`comment-style.md`. Nothing is posted without an explicit user go-ahead. Ticket text in posted
comments: `comment-style.md` section 4.

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
**Mode:** full
**Ticket:** SYNC-41 (fetched)

## Code findings
### [important] Retry loop never stops on 4xx
**ID:** F1
**Axis:** code
**Anchor:** acme-sync/sync/client/retry.py:42-43
**Confidence:** confirmed
**What:** A permanent 400 is retried forever, hammering the API.
**Why:** `while True:` then `resp = send(req)`, with no status check.
**Fix:** Stop on non-retryable status codes and cap attempts.
**Suggested change:**
Proposed patch (not posted)
```diff
-while True:
-    resp = send(req)
+for _ in range(MAX_ATTEMPTS):
+    resp = send(req)
```
**In diff:** yes
- [nit] F3 Rename `d` to `delay`. (`acme-sync/sync/client/retry.py:50`)

## Business findings
### [important] No user-visible failure state
**ID:** F2
**Axis:** business
**Confidence:** suspected
**What:** Is the user told when retries are exhausted? The diff adds no error state.
**Why:** `SYNC-41 AC-3: the user sees an error toast when sync gives up`
**Fix:** Surface the final failure state to the user, or confirm an error state is out of scope.

## Process & convention findings
None.

## Prior findings triaged
- Refuted: bot "SQL injection" at db.py:9 — the query is parameterised.

## Validation
- `pytest tests/sync` — pass. CI green on 4f2a9c1.
- Ticket: used SYNC-41 (branch, fetched via the session's Jira tool)

## Verdict
Strengths: backoff is capped and jittered; the new tests cover the 5xx path.
Request changes
Most important fix first: stop retrying non-retryable 4xx responses.
````

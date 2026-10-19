# MR review — report format

The layout the Maestro writes to `~/.ai/<project>/reviews/{slug}.md` (or the fresh file, see Slug
and re-review)<!-- claude-only --> and the renderer parses. The md is authoritative; `scripts/render_review.py` derives
`{slug}.html` from it when available. Never hand-write HTML. Parsing is strict: keep the syntax exactly as below.<!-- copilot: . The md is the only output; never hand-write HTML. Keep the syntax exactly as below. --><!-- /claude-only -->

## Header

`# Review: <title>` then one `**Key:** value` line each, in this order: `MR`, `Title`, `Head SHA`,
`Target`, `Date`, `Reviewers`, `Verdict`. `Verdict` repeats the final call (vocabulary below). The
head SHA is written once here<!-- claude-only -->; the renderer stamps it on every card<!-- copilot: --><!-- /claude-only -->.

Optional keys follow, each only when it applies, and each is shown in the masthead:

- `Mode`: `fresh`, `full` or `since-last`.<!-- claude-only --> Any other value gets a warning.<!-- copilot: --><!-- /claude-only -->
- `Since`: the baseline SHA (`[0-9a-f]{7,40}`) a `since-last` review covered from; backticks around
  it are stripped, as for the baseline read from `Head SHA`.<!-- claude-only --> Anything else gets a warning.<!-- copilot: --><!-- /claude-only -->
- `Ticket`: the primary keys only (branch or title, see `ticket-intake.md`), each with its state,
  comma-separated: `ABC-12 (fetched), ABC-13 (not fetched: no Jira skill/tool available)`. Related
  keys go only in the Validation `- Ticket:` line. An upper-case branch key or a title key that
  isn't found is written `KEY (not fetched: not found or not visible)`. Leave the line out when no
  ticket was detected, when only related keys were used, or when the only candidate was a lowercase
  branch guess that wasn't found.<!-- claude-only --> The renderer warns (stderr only, no banner) when no `(...)` group
  carries a `fetched` or `not fetched` state, so `(branch, fetched via <tool>)` counts too.<!-- copilot: --><!-- /claude-only -->

## Sections

In order: `## Code findings`, `## Business findings`, `## Process & convention findings`,
`## Prior findings triaged`, `## Validation`, `## Verdict`. Write "None." for an empty section.
`## Validation` carries a `- Last ID: F<n>` line, the highest ID this file has ever used, kept on
every rewrite so new IDs start above it (a fresh file keeps its own; with no such line, start
above the highest ID in the file).<!-- claude-only --> The renderer warns when it is
lower than an ID used in the file (card, nit, triage or `- Dropped F<n>:` line).<!-- copilot: --><!-- /claude-only -->

`## Validation` also carries exactly one Verify line, written at Close (`verify.md`):

```
- Verify: N found, K kept, D downgraded, X dropped (<method>; trigger: <threshold that fired>)
```

This file is the one owner of the line's syntax and vocabulary; `verify.md`, the command and the
skill point here. N = K+D+X.

- `<method>`, exactly one of: <!-- claude-only -->`Cass refute round`, `Maestro re-read`, `Maestro re-read (verify
  round failed)`, `Maestro re-read (no subagent on this install)` (every Copilot run, whatever the
  trigger), or `none (no candidates)`.<!-- copilot: `Maestro re-read (no subagent on this install)` (every run on this install, whatever the trigger) or `none (no candidates)`. --><!-- /claude-only -->
- `trigger:`, the first that holds of `≥1 critical/important`, `>N non-nit` (N = the Verify trigger
  in force, from the mr-review skill's threshold table, written as a number), `none`. With 0
  candidates the parenthetical is `(none (no candidates); trigger: none)`.
- Each drop and downgrade adds its own line: `- Dropped F<n>: <reason>` (a verified since-mode
  Fixed: `- Dropped F<n>: fixed (see triage)`) or `- Downgraded F<n>: <from>→<to>, <reason>`. A dropped
  finding gets no card, but its ID still counts toward `Last ID`, so it is never reused. Other
  Validation notes never start with `Verify:` (e.g. `- Suggested change dropped F<n>: …`).

<!-- claude-only -->The renderer reads Verify lines only in `## Validation`, outside fences: a bullet whose text starts
`Verify:`, `**Verify:**` or `**Verify**:`, in any case, colon right after the word (`- Verify
Suggested change …` and `- verified CI` are not Verify lines). It warns (banner and stderr) when
such a line doesn't match the form above (`Verify:` or `**Verify:**`, then four integers in that
order and wording, then a non-empty parenthetical whose text is not checked), when N ≠ K+D+X, or
when there is more than one. A file with no Verify line renders without a warning.<!-- copilot: --><!-- /claude-only -->

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

<!-- claude-only -->The renderer does not enforce field order (it shows fields in the order written), but write<!-- copilot: Write --><!-- /claude-only --> them in
this order. `Axis`, `Confidence` and `What` are required; the rest are optional:

- **ID** is the stable finding ID, `F<n>`, shown in the card meta. In `{slug}.md` a new ID is the
  highest ID ever used plus 1, and IDs are never reused; a fresh file numbers on its own.<!-- claude-only --> The
  renderer warns when an ID repeats across the cards and nits of one file. Files without IDs still
  render.<!-- copilot: --><!-- /claude-only -->
- **Carried** marks a finding kept from an earlier review at `<sha7>`, with its ID, Marker and Posted.
- **In diff** says whether every anchored line lies inside one diff hunk on the anchor's side. The
  Maestro writes it at Close, never a specialist. `no` means the finding cannot be posted inline.<!-- claude-only --> It
  is shown as a tag; any value other than `yes` or `no` gets a warning.<!-- copilot: --><!-- /claude-only -->
- **Why** of a business finding that cites a ticket AC quotes it, prefixed with its primary key:
  ``**Why:** `ABC-12 AC-2: the user sees an error toast` ``. It is still one line of inline code
  (`comment-style.md` section 1); quote one AC line, or the part of it that matters. Write any
  backtick inside the quoted AC as `'` so the code span holds.
- **Marker** is the finding's posting identity (R21, D7), kept in this md only and never put in a
  posted comment: exactly 12 lowercase hex characters,
  `sha256("<key>|<source>|<ID>")[:12]`, where `<key>` is the review key (`mr-<id>` or
  `branch-<name>`, `isolated-checkout.md`) and `<source>` is `canonical` or `fresh-<sha7>`. It is
  computed once, at first post, then carried verbatim and never recomputed. Leave `**Marker:**` out
  until the first post; never fill it at review time. <!-- claude-only -->To compute it, run
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_review.py" --marker <key> <source> <ID>`.
  The renderer warns when it isn't 12 lowercase hex.<!-- copilot:
  To compute it, run `printf '%s' '<key>|<source>|<ID>' | shasum -a 256 | cut -c1-12`. --><!-- /claude-only -->
- **Posted** is added once the finding is posted: `<platform ref> @ <sha7>`, the SHA the comment was
  posted against. The ref is what `posting.md` writes: on GitHub `#<n>#discussion_r<comment id>`
  inline or `#<n>#pullrequestreview-<review id>` for the summary, on GitLab `!<iid>#note_<note id>`
  (e.g. `!123#note_881`); older files may hold another form<!-- claude-only -->, which still renders. The renderer
  warns when the value doesn't end in ` @ <sha7>` (7-40 lowercase hex).<!-- copilot: . --><!-- /claude-only -->
- **Posted state off a card.** A nit or a `Not re-raised:` / `Fixed:` triage line keeps the same
  values as a trailing `(Marker <h12>, Posted <ref> @ <sha7>)`, with whichever of the two it has
  (`(Marker <h12>)` and `(Posted <ref> @ <sha7>)` are fine). A final `(...)` starting `Marker ` or
  `Posted `, optionally followed by `.` or `;`, is read as that tail<!-- claude-only -->, and the renderer checks it like
  the card fields<!-- copilot: --><!-- /claude-only -->. The ref may not contain parentheses. <!-- claude-only -->The renderer also warns on a near miss: a<!-- copilot: A near miss is a --><!-- /claude-only -->
  nit or triage line with a `(` opening on `Marker` or `Posted` in any case but no tail at its end
  (`(Marker: …)`, lowercase, text after the tail, swapped order), and a `Not re-raised`/`Fixed`
  line with an F-ID in any other form, such as a bold label `- **Not re-raised:** F2`.
- **Rewrite guard** (R25). Before rewriting `{slug}.md` (or its own fresh file, on a fresh re-run at
  the same SHA), the Maestro copies the old file to scratch, then checks the new file against the
  copy <!-- claude-only -->with `render_review.py --previous <old.md> <new.md>`, which prints one
  line per problem (nothing when clean) and writes no html<!-- copilot: by hand --><!-- /claude-only -->.
  The guard reports: an ID that had a Marker or Posted value
  anywhere in the old file (card, nit or triage line) and is nowhere in the new one; a changed or
  missing Marker or Posted value on such an ID; a `Last ID` that is missing or lower than the old
  one, or else a max ID (highest of Last ID and every ID in the file) lower than the old one; and an
  ID at or below the old max that the old file no longer held (a used-up number coming back). An
  ID with neither value, such as an unposted `Fixed:` line or an unposted `Not re-raised:` finding,
  may disappear without a report. Reuse of a number still in the old file isn't detected. An old
  ID whose Marker or Posted value is malformed, or whose tail is a near miss, is **unrepairable**:
  its malformed value isn't compared (carry it verbatim; correct it only with the user's
  confirmation), its valid half still is, dropping it is still reported,
  and it is marked do-not-post and the user is asked before any posting<!-- claude-only -->. The script also repeats
  the renderer's malformed and near-miss posted-state lines from either file, prefixed `old file:`
  or `new file:`, and prints `unrepairable: F<n> …` for each unrepairable ID; a `new file:` line
  that carries such an ID's old tail verbatim is folded into it. Exit 1: an actionable line remains
  (fix and re-run); exit 3: only `old file:` and `unrepairable:` lines remain; exit 0: clean or only
  `old file:` lines. Exit 2 is a usage error, and exit 1 with no output a read error (check the paths, else check by
hand). Validation logs each `old file:` line as `- Guard (old file): <line>` and each unrepairable
ID as `- Guard (unresolved): <line>`.<!-- copilot: . Validation logs each unrepairable ID as `- Guard (unresolved): F<n> …`. --><!-- /claude-only -->

- **Anchor** is one of five forms (meaning and sides in `comment-style.md` section 2):
  `<repo>/<path>:<n>`, `:<a>-<b>` (new side), `:-<n>`, `:-<a>-<b>` (old side), or
  `<repo>/<path> (deleted)` (file level). Optional; business findings may omit it. <!-- claude-only -->The renderer
  warns when an Anchor is malformed or its range is reversed (b < a). It splits at the **last** `:`
  and reads the line spec from the end<!-- copilot: A reversed range (b < a) is malformed. An Anchor is split at the **last** `:` and its line spec read from the end --><!-- /claude-only -->, so a path may contain spaces, `-`, digits and `:`. Limits: a
  path ending in `:<digits>` cannot be anchored, line numbers start at 1, a path holding `:<n>`
  before a space, comma or semicolon is refused as two anchors in one field (one Anchor per card),
  and a path starting with `/` or containing a backtick is refused.
- **Suggested change** is a fenced `diff` block under the label **Proposed patch (not posted)**.
  Confirmed findings only; the gates are in `comment-style.md`.
- A nit may be one line: `- [nit] Title — note. (`path:line`)`. It may start with its ID:
  `- [nit] F7 Title — note. (`path:line`)`. <!-- claude-only -->The renderer reads that prefix as an ID only when the
  file has at least one card `**ID:**`, a `- Last ID:` line or a `Not re-raised`/`Fixed` triage ID,
  or when the nit itself ends in a posted-state tail; otherwise the nit text is kept verbatim. The trailing
  `(path:line)` is free text and is not validated: older files wrote it loosely, and checking it
  would add warnings to files that rendered clean.<!-- copilot: The trailing `(path:line)` is free text. --><!-- /claude-only --> A posted nit ends with the posted-state tail
  described above. The nit cap's summary line `- [nit] N more not shown: <titles>`
  (`noise-controls.md`) is shown but is not a finding: it is not counted and carries no ID.<!-- claude-only --> A near
  miss of it (`0 more`, no colon, `More`) warns and counts as a nit.<!-- copilot: --><!-- /claude-only -->

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
no `## Strengths` section), then the verdict word, ending with `Most important fix first: …`.<!-- claude-only --> The renderer shows a banner on a
contradiction; fix the md rather than ignore it.<!-- copilot: --><!-- /claude-only -->

## Slug and re-review

Slug is `mr-<id>-<short-title>`, e.g. `mr-123-retry-backoff`; for a branch with no id use
`branch-<name>` (remote branches and `current branch`; detached HEAD: `head-<sha7>`). `current
changes` uses `changes-<name>` of the checked-out branch (detached HEAD: `changes-<sha7>`); a
pasted patch uses `patch-<sha7>`, the first 7 hex of the sha256 of the patch text, so only a
re-run of the same patch rewrites it. It is derived, never copied verbatim: lowercase, only `[a-z0-9-]` (every other
character, including `/` and `.`, becomes `-`; collapse repeats), at most ~60 chars, so the file
cannot leave `reviews/`. A `full` or `since-last` review writes `reviews/{slug}.md`. A `fresh`
review writes `reviews/{slug}-fresh-<sha7>.md`, where `<sha7>` = the first 7 characters of the head
SHA. The suffix is added after the slug is derived, so repeated `-` still collapse in the slug
itself. The head SHA must match `[0-9a-f]{7,40}`. Quote paths passed to a shell
(`git show <sha>:"<path>"`<!-- claude-only -->, the render command<!-- copilot: --><!-- /claude-only -->). A path from diff text must be repo-relative:
refuse any containing `..` or shell metacharacters (`` ` $ ; | & < > ( ) ``, quotes, newlines),
and never pass a refused path to a shell. A re-review of the same MR overwrites the file and records the head SHA
it reviewed in the header.

## Comment rules (brief)

Lead with impact; one issue per finding; quote evidence; neutral voice; a question when
`suspected`; no `/Users/`, `/home/`, `/tmp/` paths. Suspected findings are never posted inline
(`comment-style.md` section 4). Full rules and the suggestion gates:
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
- Verify: 3 found, 2 kept, 0 downgraded, 1 dropped (Cass refute round; trigger: ≥1 critical/important)
- Dropped F4: `delay = min(delay * 2, MAX_DELAY)` at retry.py:47 caps the backoff delay, so the reported delay overflow cannot happen.
- Last ID: F4

## Verdict
Strengths: backoff is capped and jittered; the new tests cover the 5xx path.
Request changes
Most important fix first: stop retrying non-retryable 4xx responses.
````

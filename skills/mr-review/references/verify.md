# MR review — Verify

How the Maestro checks findings before the verdict (`/bq:review-mr` **Close**, step 5)<!-- claude-only -->,
and what Cass returns in a refute round<!-- copilot: --><!-- /claude-only -->. It runs after dedupe, matching, the nit cap and new IDs, so every candidate
carries its final ID (fresh numbers from F1 and opens no canonical file first). The Validation lines
it writes (`- Verify:`, `- Dropped F<n>:`, `- Downgraded F<n>:`<!-- claude-only -->, `- Re-read F<n>:`<!-- copilot: --><!-- /claude-only -->) and their
method and trigger values are owned by `report-format.md` (Sections); write exactly one Verify line.

## Candidates and trigger

- **Candidates.** Every critical, important and `suspected` finding, plus since-mode `Fixed` and
  `Residual` triages with their evidence quote, at their prior severity. Carried Still open findings
  are never verified again. No candidates: record method `none (no candidates)`, trigger `none`.
- **Trigger.** It fires on at least one critical or important candidate (a triaged finding counts
  at its prior severity) or on more non-nit findings in total than the Verify trigger (the mr-review
  skill's **Thresholds** table; carried Still open excluded). In the second case every non-nit
  finding is a candidate, confirmed minors included; otherwise confirmed minors and nits are not.

## SHAs and reads

`<sha>` is the head SHA. `<mb>` is `git merge-base "<sha>" "refs/bq-review/<key>/base"`, the base
the diff was taken against. A new-side anchor is read with `git -C "<wt>" show "<sha>":"<path>"`; an
old-side anchor or a `(deleted)` file with `git -C "<wt>" show "<mb>":"<old path>"`. Both SHAs must
match `[0-9a-f]{7,40}`; paths follow the refusals in `report-format.md` (Slug and re-review).

Local targets read, and run absence searches (**Absence**), with `git -C "<dir>"` at the `<sha>`
resolved at the start, never a moving HEAD or the working tree. Old-side anchors are read at `<mb>`
for `current branch` and at `<sha>` for `current changes`. The new side of `current changes` is in
no ref: its new-side quotes are checked against the saved patch text, and its absence searches also
cover that patch's added lines. A pasted patch's quotes, old and new side, are checked against the
patch text; in a repo, lines outside it are read at `<sha>` (resolved from `HEAD` at the start), as
for its rules ref in `noise-controls.md`.

## Who checks

<!-- claude-only -->When the trigger fires, spawn a fresh `bq:reviewer` (Cass) refute round. Its brief opens "load
the bq mr-review skill first" and carries: each candidate's ID, title, severity, confidence, Anchor,
What and Why (a triage also its evidence quote), marked command-confirmed (below) with its tagged
command and one-line result, or `absence` (**Absence**) with its search and empty result; `<wt>`,
`<sha>`, `<mb>`; for `current changes` or a pasted patch, the saved patch text; the intent block,
ticket block in its untrusted fence; the `REVIEW.md` rules block; the read-only and `<wt>`-only
rules. Never the specialists' reasoning. In fresh, also the verbatim `Mode: fresh` line and none of
the items **Fresh** keeps out (`/bq:review-mr`).

The round tries to falsify each finding: it stands unless a quoted line shows What's failure cannot
happen or its premise is false. Default kept; downgrade to `suspected` only when the failure needs a
precondition nothing verifies. A command-confirmed candidate it may only keep or `contest`, quoting
a line showing the command doesn't exercise What's mechanism or its result doesn't show the failure.
It runs no tests, builds, scripts or searches, and reads only with `git show` at `<sha>` or `<mb>`
(plus the new-side lines of the brief's patch text). Each ID comes back kept, downgraded
(`<from>→<to>`), dropped or contest, with the counter-case it tried and the quoted line it rests on,
from a source listed under **Check the round's outcomes**; an absence drop also gives that line's
`path:line`. If the round errors, or hasn't returned about 10 minutes after the last specialist,
re-read instead and record `Maestro re-read (verify round failed)`. Below the trigger, re-read.<!-- copilot: On this install the Maestro always re-reads, whatever the trigger, and records
`Maestro re-read (no subagent on this install)`. --><!-- /claude-only -->

**Command-confirmed.** A candidate is command-confirmed when a specialist's Validation command line
carries its tag, `(supports: <title>)` (the tag rule is in `/bq:review-mr`'s specialist brief).
Only a command that runs code and whose result shows What's failure counts; a search (`grep`, `git grep`, `rg`, `find`, `ls`), a
PASS, or a result that doesn't show the failure in What makes it an ordinary candidate. On any
Maestro re-read<!-- claude-only --> other than a contest (**Check the round's outcomes**)<!-- copilot: --><!-- /claude-only -->, a command-confirmed candidate is kept,
severity and confidence, even with no qualifying quote, and nothing is re-run. Local targets tag
no commands (`/bq:review-mr` brief); a tag on one is ignored and the candidate is an ordinary one.

**Absence.** For an absence finding (missing test, uncovered AC, unhandled path), the search in
**Why** and its empty result (`comment-style.md` §1) can be the qualifying quote only when its
pattern contains an identifier from the Anchor or What (a function, route or AC term), not a
paraphrase; otherwise the finding is judged as an ordinary candidate on a code quote. On every
Maestro check of an absence finding<!-- claude-only --> (each absence keep from the round, and any re-read)<!-- copilot: --><!-- /claude-only -->, the Maestro runs
the pattern widened, with no pathspec, at the reviewed revision (it may substitute a better
identifier from What; local targets per **SHAs and reads**):
`git -C "<wt>" grep -n -i -e "<pattern>" "<sha>"`. Each hit in a test, or a file where the thing
would live, is read with `git show`; one that shows the thing exists is the drop's quote, and the
drop gives its `path:line`, checked with `git show "<sha>":"<path>"`. The absence quote qualifies
when no hit shows that (a hit that only mentions the identifier, like the source under review or a
test of another case, doesn't count against it).

<!-- claude-only -->
## Check the round's outcomes

A quote is found only in its source: the matching `git show` output or the brief's patch text
(**SHAs and reads**); the intent block, for a business or scope finding; a command-confirmed
candidate's result; or an absence candidate's search and empty result in the brief, when it
qualifies (**Absence**). Look up each ID's returned outcome; if anything in its row doesn't hold,
the Maestro re-reads the ID and decides it under **Outcomes**.

| Returned outcome | Must hold, else re-read |
|---|---|
| keep | Its quote is found. It states a counter-case of its own (re-quoting the card's **Why** isn't one). An absence keep's search qualifies. A keep that moves `suspected` to `confirmed` meets the evidence in **Outcomes**. |
| drop | Not command-confirmed. Its quote is found and the Maestro can link it in one clause to What's mechanism, showing the failure can't happen; that clause becomes the `Dropped` line's reason (since-mode `Fixed`: **Since-mode triages**). An absence drop's `path:line` shows the thing exists. |
| severity downgrade | Not command-confirmed. Its quote is found and links in one clause to What's mechanism, falsifying the part of the failure the downgrade removes; that clause becomes the `Downgraded` line's reason. |
| `confirmed`→`suspected` | Not command-confirmed. Its quote is found and it names the precondition nothing verifies (no mechanism link needed). |
| contest | Never: always re-read. The Maestro may re-run only the byte-identical tagged command, in `<wt>` (never on a local target). A different result means the finding is flaky: downgrade it to `suspected`, never drop it. The same result alone keeps it. Once the Maestro rules, on a quote, that the command doesn't exercise What's mechanism or that the result doesn't show the failure, the command no longer supports it: it is judged as an ordinary candidate under **Outcomes**. With no re-run it decides on those quotes alone. |
| omitted, or any other | Never: always re-read. |

A drop or severity downgrade the Maestro can't link is a veto: it doesn't count. Log each such
re-read, vetoes included, as its own `- Re-read F<n>:` line (`report-format.md`). A failed check
never lowers a finding by itself; it only sends it to this re-read.<!-- copilot: --><!-- /claude-only -->

## Outcomes

- Each candidate is kept, downgraded or dropped, each drop and downgrade on its own titled Validation
  line; a dropped finding gets no card and keeps its ID in `Last ID` (both per `report-format.md`).
  Downgraded means a lower severity, or `confirmed` to `suspected`; a downgrade to nit turns the card
  into a `- [nit] F<n>` line. A keep moves `suspected` to `confirmed` only on the evidence the
  re-read bullet below requires; one that leaves it at `suspected` counts
  as kept (K).
- A code-axis finding is kept on a code quote from `git show` or the saved patch text (**SHAs and
  reads**), a qualifying absence search (**Absence**) or a command-confirmed result
  (**Command-confirmed**); it is dropped only on a code quote that falsifies What. An intent-block
  quote (MR text, ticket) can decide only a business or scope finding and never drops a code defect.
- To re-read, the Maestro reads each candidate's anchor (**SHAs and reads**) and decides it itself.
  The default is kept. A finding becomes `suspected`, severity unchanged, only when its **Why** quote
  isn't found at its anchor, or its failure needs a precondition nothing verifies (exceptions:
  **Command-confirmed**, and **Absence** when its widened search qualifies). A `suspected` one
  becomes `confirmed` only when its **Why** quote is found at its anchor and shows the failure
  directly, or it has a qualifying absence search or is command-confirmed; a business or scope
  finding, only when its **Why** quote is found in the intent block and an anchor read or a
  qualifying absence search shows the requirement unmet (the intent block alone keeps it, never
  promotes it).
- **Dropped carried IDs never vanish.** A dropped finding that matched a prior open ID goes under
  `## Prior findings triaged`: as `Fixed: <ID> — <code quote>` when the drop rests on a verified
  code quote, else as `Not re-raised: <ID> — <title>`, each with its posted-state tail
  (`report-format.md`).

## Since-mode triages

A verified `Fixed` counts as dropped (X): its `Fixed:` triage line<!-- claude-only -->, whose evidence carries the drop's
linked clause,<!-- copilot: --><!-- /claude-only --> plus `- Dropped F<n>: <title> — fixed (see triage)`. A `Residual` that holds counts as
downgraded (D). A refuted `Fixed` or `Residual` (its quote doesn't hold, or specialists disagree
without a verified Fixed quote) stays Still open and counts as kept (K). Only Still open carries
skip Verify.

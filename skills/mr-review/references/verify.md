# MR review — Verify

How the Maestro checks findings before the verdict (`/bq:review-mr` **Close**, step
5)<!-- claude-only -->, and what Cass returns in a refute round<!-- copilot: --><!-- /claude-only -->. It runs after dedupe, matching, the nit cap and new IDs, so every
candidate carries its final ID (fresh numbers from F1 and opens no canonical file first). The
Validation lines it writes (`- Verify:`, `- Dropped F<n>:`, `- Downgraded F<n>:`) and their method
and trigger values are owned by `report-format.md` (Sections); write exactly one Verify line.

## Candidates and trigger

- **Candidates.** Every critical, important and `suspected` finding, plus since-mode `Fixed` and
  `Residual` triages with their evidence quote, at their prior severity. Carried Still open
  findings are never verified again. No candidates: record method `none (no candidates)`, trigger
  `none`.
- **Trigger.** It fires on at least one critical or important candidate (a triaged finding counts
  at its prior severity) or on more non-nit findings in total than the Verify trigger (the mr-review
  skill's **Thresholds** table; carried Still open excluded). In the second case every non-nit
  finding is a candidate, confirmed minors included; otherwise confirmed minors and nits are not
  verified.

## SHAs and reads

`<sha>` is the head SHA. `<mb>` is `git merge-base "<sha>" "refs/bq-review/<key>/base"`, the base the
diff was taken against. A new-side anchor is read with `git -C "<wt>" show "<sha>":"<path>"`; an
old-side anchor or a `(deleted)` file with `git -C "<wt>" show "<mb>":"<old path>"`. Both SHAs must
match `[0-9a-f]{7,40}`; paths follow the refusals in `report-format.md` (Slug and re-review).

Local targets read with `git -C "<dir>"` at the `<sha>` resolved at the start, never a moving
HEAD. Old-side anchors are read at `<mb>` for `current branch` and at `<sha>` for `current
changes`. The new side of `current changes` is in no ref, so its new-side quotes are checked
against the saved patch text. A pasted patch's quotes, old and new side, are checked against the
patch text; in a repo, lines outside it are read at `<sha>` (resolved from `HEAD` at the start), as for its rules ref in
`noise-controls.md`.

## Who checks

<!-- claude-only -->When the trigger fires, spawn a fresh `bq:reviewer` (Cass) refute round. Its
brief opens "load the bq mr-review skill first" and carries: each candidate as ID, title, severity,
confidence, Anchor, What and Why (a triage also with its evidence quote); `<wt>`, `<sha>` and
`<mb>`; the intent block, with the ticket block in its untrusted fence; the `REVIEW.md` rules
block; and the read-only and `<wt>`-only rules. It never carries the specialists' reasoning. In
fresh, the brief also carries the verbatim `Mode: fresh` line and none of the items **Fresh** keeps
out (`/bq:review-mr`). It asks for the strongest case that each finding is wrong, returned per ID as kept,
downgraded (`<from>→<to>`) or dropped, with the counter-case it tried and the quoted line it rests
on, from the `git show` reads above or the intent block. If the round errors, or hasn't returned
about 10 minutes after the last specialist, re-read instead and record `Maestro re-read (verify
round failed)`. Below the trigger, re-read.<!-- copilot: On this install the Maestro always
re-reads, whatever the trigger, and records `Maestro re-read (no subagent on this install)`. --><!-- /claude-only -->
To re-read, the Maestro reads each candidate's anchor with the `git show` above and decides each
outcome itself.

<!-- claude-only -->
## Check the round's quotes

Search every quote the round returns in the matching `git show` output, or in the intent block for
a business or scope finding. A keep must state the counter-case it tried and may not only re-quote
the card's own **Why**. A keep whose quote isn't found, or without its own counter-case, downgrades
the finding to `suspected`, logged as `- Downgraded F<n>: <from>→suspected, refute quote not found`
(or `… no counter-case`). A drop or downgrade whose quote isn't found doesn't count: the Maestro
re-reads that ID and decides.<!-- copilot: --><!-- /claude-only -->

## Outcomes

- Each candidate is kept, downgraded or dropped. Kept may move `suspected` to `confirmed`.
  Downgraded means a lower severity, or `confirmed` to `suspected`; a downgrade to nit turns the
  card into a `- [nit] F<n>` line.
- A code-axis finding is kept or dropped only on a code quote from `git show`. An intent-block
  quote (MR text, ticket) can decide only a business or scope finding and never drops a code
  defect. With no qualifying quote, downgrade to `suspected`.
- Log each drop and downgrade on its own Validation line; a dropped finding gets no card and keeps
  its ID in `Last ID` (both per `report-format.md`).
- **Dropped carried IDs never vanish.** A dropped finding that matched a prior open ID goes under
  `## Prior findings triaged`: as `Fixed: <ID> — <code quote>` when the drop rests on a verified
  code quote, else as `Not re-raised: <ID> — <title>`, each with its posted-state tail
  (`report-format.md`).

## Since-mode triages

A verified `Fixed` counts as dropped (X): its `Fixed:` triage line plus `- Dropped F<n>: fixed (see
triage)`. A `Residual` that holds counts as downgraded (D). A refuted `Fixed` or `Residual` (its
quote doesn't hold, or specialists disagree without a verified Fixed quote) stays Still open and
counts as kept (K). Only Still open carries skip Verify.

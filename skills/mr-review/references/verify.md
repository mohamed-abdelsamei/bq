# MR review — Verify

How the Maestro checks findings before the verdict (`/bq:review-mr` **Close**, step
5)<!-- claude-only -->, and what Cass returns in a refute round<!-- copilot: --><!-- /claude-only -->. It runs after dedupe, matching, the nit cap and new IDs, so every
candidate carries its final ID (fresh numbers from F1 and opens no canonical file first). The
Validation lines it writes (`- Verify:`, `- Dropped F<n>:`, `- Downgraded F<n>:`<!-- claude-only -->,
`- Re-read F<n>:`<!-- copilot: --><!-- /claude-only -->) and their method
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
confidence, Anchor, What and Why (a triage also with its evidence quote), marked when
command-confirmed (below) with its tagged command and one-line result, and marked `absence`
(**Absence**) with its search and empty result, so a drop gives `path:line`; `<wt>`, `<sha>` and
`<mb>`; for `current changes` or a pasted patch, the saved patch text; the intent block, with the
ticket block in its untrusted fence; the `REVIEW.md` rules block; and the read-only and
`<wt>`-only rules. It never carries the specialists' reasoning. In
fresh, the brief also carries the verbatim `Mode: fresh` line and none of the items **Fresh**
keeps out (`/bq:review-mr`). It asks the round to try to falsify each finding: a finding stands
unless a quoted line shows What's failure cannot happen or its premise is false. The default is
kept; downgrade to `suspected` only when the failure needs a precondition nothing verifies. The
round runs no tests, builds, scripts or searches; it reads only with `git show` at `<sha>` or
`<mb>`, and for `current changes` or a pasted patch it may also quote the new-side lines of the
brief's patch text (**SHAs and reads**). A command-confirmed candidate it may only keep or `contest`, quoting a
line showing that the command doesn't exercise What's mechanism or that its result doesn't show
the failure. Each ID comes back kept, downgraded (`<from>→<to>`), dropped or contest, with the
counter-case it tried and the quoted line it rests on, from the `git show` reads above, the
brief's patch text, the intent block, a command-confirmed candidate's result, or an absence
candidate's search and its empty result in the brief; an absence drop also gives that
line's `path:line`. If the round errors, or hasn't returned about 10 minutes after the last
specialist, re-read instead and record `Maestro re-read (verify round failed)`. Below the trigger, re-read.<!-- copilot: On this install the Maestro always
re-reads, whatever the trigger, and records `Maestro re-read (no subagent on this install)`. --><!-- /claude-only -->
To re-read, the Maestro reads each candidate's anchor with the `git show` above and decides each
outcome itself (a command-confirmed candidate per the rule below).

**Command-confirmed.** A candidate is command-confirmed when a specialist's Validation command line
carries its tag, `(supports: <title>)` (the tag rule is in `/bq:review-mr`'s specialist brief).
A tagged search (`grep`, `git grep`, `rg`, `find`, `ls`), a PASS, or a result that doesn't show
the failure in What doesn't make it command-confirmed: it is judged as an ordinary candidate. On
any Maestro re-read<!-- claude-only --> other than a contest<!-- copilot: --><!-- /claude-only -->, a command-confirmed candidate is kept, severity and
confidence, even with no qualifying quote. <!-- claude-only -->A contest is decided under **Check
the round's outcomes**. For a local target it is kept whatever the round returns, logs no Re-read,
and nothing is re-run: an accepted precision gap (R5).<!-- copilot: On this install it is kept
and nothing is re-run. --><!-- /claude-only -->

**Absence.** For an absence finding (missing test, uncovered AC, unhandled path), the search in
**Why** and its empty result (`comment-style.md` §1) can be the qualifying quote. Its pattern must
contain an identifier from the Anchor or What (a function, route or AC term), not a paraphrase,
or it doesn't qualify. On every Maestro check of an absence finding<!-- claude-only --> (each
absence keep from the round, and any re-read)<!-- copilot: --><!-- /claude-only -->, the Maestro runs the pattern widened, with no pathspec, at the reviewed
revision: `git -C "<wt>" grep -n -i -e "<pattern>" "<sha>"` (it may substitute a better
identifier from What). A local target searches `<dir>` at `<sha>`, never the working tree, and
`current changes` also the saved patch's added lines (**SHAs and reads**). Each hit in a test, or
a file where the thing would live, is read with `git show`; one that shows the thing exists is the
drop's quote. The absence quote qualifies when no hit shows that (a hit that only mentions the
identifier, like the source under review or a test of another case, doesn't count against it); a
pattern without an identifier never qualifies, and the finding is then judged as an ordinary
candidate on a code quote. A drop must give the `path:line` of the line showing the thing exists,
checked with `git show "<sha>":"<path>"` (local targets per **SHAs and reads**).

<!-- claude-only -->
## Check the round's outcomes

Search every quote the round returns in the matching `git show` output (or the saved patch text,
per **SHAs and reads**), in the intent block for a
business or scope finding, or in a command-confirmed candidate's result from the brief. The Maestro
re-reads an ID and decides it when:

- the round omits it, or returns an outcome other than keep, downgrade, drop or contest;
- any outcome's quote (keep, drop, downgrade or contest) isn't found;
- a keep states no counter-case of its own (re-quoting the card's **Why** isn't one);
- a drop, or a downgrade that lowers severity, can't be linked by the Maestro in one clause to
  What's mechanism: a drop's quote must show the failure can't happen, a severity downgrade's must
  falsify the part of the failure it removes (a veto: it doesn't count). A linked clause becomes
  the `Dropped` or `Downgraded` line's reason; for a since-mode `Fixed` it goes into the `Fixed:`
  triage line's evidence and the Dropped reason stays `fixed (see triage)`. A `confirmed`→`suspected`
  downgrade needs only the unverified precondition;
- an absence keep's empty-search quote doesn't qualify under **Absence** (it counts as found only
  when it qualifies), or an absence drop's `path:line` doesn't show the thing exists;
- a command-confirmed candidate comes back dropped or downgraded (only keep or contest are allowed);
- it is contested. The Maestro may re-run only the byte-identical tagged command, in `<wt>`. A
  different result means the finding is flaky: downgrade it to `suspected`, never drop it. The same
  result alone keeps it. Once the Maestro rules, on a quote, that the command doesn't exercise
  What's mechanism (code) or that the result doesn't show the failure (the result), the command no
  longer supports it: it is judged as an ordinary candidate under **Outcomes**. With no re-run it
  decides on those quotes alone.

Log each such re-read, vetoes included, as its own `- Re-read F<n>:` line (`report-format.md`).
A failed check never lowers a finding by itself; it only sends it to this re-read.<!-- copilot: --><!-- /claude-only -->

## Outcomes

- Each candidate is kept, downgraded or dropped. Kept may move `suspected` to `confirmed`.
  Downgraded means a lower severity, or `confirmed` to `suspected`; a downgrade to nit turns the
  card into a `- [nit] F<n>` line. A re-read that leaves a `suspected` finding at `suspected`
  counts as kept (K), not downgraded.
- A code-axis finding is kept on a code quote from `git show`, a qualifying absence search
  (**Absence**) or a command-confirmed result (**Command-confirmed**); it is dropped only on a code
  quote that falsifies What. An intent-block quote (MR text, ticket) can decide only a business or
  scope finding and never drops a code defect.
- On the Maestro's own re-read the default is kept: a finding becomes `suspected` (severity
  unchanged) only when its **Why** quote isn't found at its anchor, or its failure needs a
  precondition nothing verifies (exceptions: **Command-confirmed**, and **Absence** when its
  widened search qualifies).
- Log each drop and downgrade on its own titled Validation line; a dropped finding gets no card and
  keeps its ID in `Last ID` (both per `report-format.md`).
- **Dropped carried IDs never vanish.** A dropped finding that matched a prior open ID goes under
  `## Prior findings triaged`: as `Fixed: <ID> — <code quote>` when the drop rests on a verified
  code quote, else as `Not re-raised: <ID> — <title>`, each with its posted-state tail
  (`report-format.md`).

## Since-mode triages

A verified `Fixed` counts as dropped (X): its `Fixed:` triage line plus `- Dropped F<n>: <title> — fixed
(see triage)`. A `Residual` that holds counts as downgraded (D). A refuted `Fixed` or `Residual` (its
quote doesn't hold, or specialists disagree without a verified Fixed quote) stays Still open and
counts as kept (K). Only Still open carries skip Verify.

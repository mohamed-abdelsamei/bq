# Record templates — fallback copy

The canonical templates are the starter files under the plugin's `templates/bq/` (see the memory
skill's *Locating the templates*). Use this copy only when none of those locations exists; it
mirrors them, so if the two ever differ, `templates/bq/` wins. Requirements, research, and reviews
have starter files there too — without them, follow the owning skill (**decision-and-spec**,
**research-method**).

## Decision (ADR) — `decisions/{NNNN}-{slug}.md`

```markdown
# {NNNN}. {Short title of the decision}

- **Date:** {YYYY-MM-DD}
- **Status:** Proposed | Accepted | Implemented | Rejected | Withdrawn | Superseded by {NNNN}
- **Deciders:** {who / which agents}
- **Implemented by:** {task / commit / `path/to/file.ext` — fill in when Status becomes Implemented; blank until then}
- **Verified by:** {review / test / `~/.ai/<project>/reviews/{slug}.md` — the evidence it works; blank until verified}

> A decision is *intent* until it's Implemented — its code has to land and be verifiable before it
> describes the real system. See the **decision-and-spec** skill.

## Context

What's the situation, and what forces are at play? What makes this a decision worth recording?

## Decision

What we decided — stated plainly — and why this option over the others.

## Alternatives considered

- **Option A** — rejected because…
- **Option B** — rejected because…
- **Do nothing** — …

## Consequences

What this makes easier, what it makes harder, and what it commits us to. Note known risks and
the conditions under which we'd revisit this.
```

## Discussion summary — `discussions/{YYYY-MM-DD}-{slug}.md`

```markdown
# {Topic} — {YYYY-MM-DD}

**Question:** _One or two sentences describing what the team debated._

## Positions

- Sol (architect): _Architecture/scope view._
- Max (engineer): _Implementation/pragmatism view._
- Vera (tester): _Verification/user-behavior view._
- Cass (reviewer): _Risk/critique view._
- Ada (researcher): _Evidence/options view._
- Quill (scribe): _Clarity/record view._

## Tensions

_The real disagreements, tradeoffs, and assumptions._

## Decision

_What was agreed. Link the decision entry if one exists._

## Open questions

_What remains unresolved or needs a spike/research._
```

## Task list — `tasks/{slug}.md`

```markdown
# Tasks: {Feature}

Requirement: ../requirements/{slug}.md

- [ ] 1. {task} — owner: architect — done when: {condition} — deps: none
- [ ] 2. {task} — owner: engineer — done when: {condition} — deps: 1
- [ ] 3. {task} — owner: tester — done when: {condition} — deps: 2

Status markers: `[ ]` todo, `[x]` done, `[~]` in progress, `[!]` needs re-verification, `[-]` dropped/cancelled.
```

## Archive header — `archive/{YYYY-MM-DD}/{folder}/{file}`

`/bq:drop` moves a dropped plan's requirement, decision(s), and task list here and prepends:

```markdown
> Archived {YYYY-MM-DD} — Rejected | Withdrawn | Dropped: {one-line reason}
> Superseded by {link to the replacement plan} — or "not replaced"
> Original home: <mem>/{folder}/{filename}
```

## Lessons

Lessons (`lessons/`) have their own format — see the **feedback-loop** skill. Capture them with
`/bq:retro`.

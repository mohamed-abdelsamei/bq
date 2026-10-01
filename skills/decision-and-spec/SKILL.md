---
name: decision-and-spec
description: 'How to write testable requirements and record decisions well — measurable acceptance criteria (given/when/then), explicit scope, and ADRs that capture context, the decision, the alternatives rejected, and the consequences, so the record is reviewable later by a human alone. Use when writing a bq spec or acceptance criteria (/bq:plan), or recording an ADR in ~/.ai/<project>/decisions/ — "write an ADR", "acceptance criteria", "given/when/then", "scope this".'
---
# Decisions & specs

The team's memory is only as good as what gets written. Two crafts: **specs** (what we'll build)
and **decisions** (what we chose and why). Both are for a human to read later, without the team
present — see the **memory** skill for the templates and homes.

## Testable requirements

A requirement a tester can't check is a wish. Make each one measurable.

- **Bad:** "Search should be fast." **Good:** "Search returns results in < 200 ms at p95 for a
  10k-item index."
- Use **given / when / then** for behavior: *given* a logged-out user, *when* they open `/account`,
  *then* they're redirected to `/login`.
- State **scope explicitly** — what's in, and what's deliberately *out* (the out-list prevents
  scope creep and is as important as the in-list).
- Each requirement gets **acceptance criteria** that define "done" unambiguously.
- Flag every assumption. An unstated assumption is a future bug.

## Decision records (ADRs)

Record a decision when it's load-bearing, costly to reverse, or someone will later ask "why?".
One file per decision (`~/.ai/<project>/decisions/`). Capture:

- **Context** — the situation and the forces in tension. Why is this a real choice?
- **Decision** — what we chose, in plain words.
- **Alternatives considered** — including "do nothing", each with *why it lost*. This is the part
  people skip and the part reviewers most need.
- **Consequences** — what it makes easier, harder, and commits us to; known risks; when we'd
  revisit.

### Status

The statuses and their order live in the **memory** skill's Status markers. Keep the status
current — a stale status is worse than none. `Proposed` and `Accepted` are *intent*; only
`Implemented` describes something that actually exists. When you walk away from a plan, run
`/bq:drop` rather than leaving it looking active or silently deleting it.

## Quality bar

Lead with the point. Define terms on first use. Show a concrete example over an adjective. The
test: could the user, six months from now, read this alone and understand both *what* and *why*?
If not, it's not done.

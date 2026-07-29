---
description: 'How to write testable requirements and record decisions well — measurable acceptance criteria (given/when/then), explicit scope, and ADRs that capture context, the decision, the alternatives rejected, and the consequences. Use when writing a spec (/ca-plan) or recording a decision, so the record is reviewable later by a human alone.'
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

Scope is a chain: what's **in scope** is what a decision commits to build; what gets **implemented**
is what becomes durable knowledge. The knowledge graph only ever records the in-scope work that has
actually landed in code — never the plan, and never the out-of-scope list.

## Decision records (ADRs)

Record a decision when it's load-bearing, costly to reverse, or someone will later ask "why?".
One file per decision (`.coagents/decisions/`). Capture:

- **Context** — the situation and the forces in tension. Why is this a real choice?
- **Decision** — what we chose, in plain words.
- **Alternatives considered** — including "do nothing", each with *why it lost*. This is the part
  people skip and the part reviewers most need.
- **Consequences** — what it makes easier, harder, and commits us to; known risks; when we'd
  revisit.

### Lifecycle

A decision moves through **Proposed → Accepted → Implemented → Superseded**, and can be dropped from
any point before implementation:

- **Proposed** — recorded, not yet agreed.
- **Accepted** — the team has committed to it, but the code doesn't reflect it yet.
- **Implemented** — the decision has landed in code and is verifiable. Stamp *Implemented by* with
  the task, commit, or `file:line` that carries it.
- **Rejected** — considered and decided against; never adopted. Keep it — a rejected option with
  *why it lost* is exactly what a future reader needs.
- **Withdrawn** — was `Proposed`/`Accepted`, then the plan was abandoned before implementation.
- **Superseded by {NNNN}** — replaced by a later decision; update the entry and point to it.

In loop terms this is the **decision loop**: it opens at `Proposed`/`Accepted` (intent) and *closes*
only when the code lands (`Implemented`, verified) and the concept folds into knowledge — or when the
plan is dropped. An `Accepted` decision never implemented is an open loop. See the
**loop-engineering** skill.

Keep the status current — a stale status is worse than none. `Proposed` and `Accepted` are *intent*;
only `Implemented` describes something that actually exists. When you walk away from a plan, mark it
`Rejected` or `Withdrawn` and archive it with `/ca-drop` so it stops reading as live work — don't
leave it looking active, and don't silently delete it (see the **memory** skill for the archive
discipline). A `Rejected` or `Withdrawn` decision never had code land, so it never enters the
knowledge graph.

### Decisions and the knowledge graph

A decision does **not** enter the knowledge graph (`.coagents/knowledge/`) until it is
`Implemented`. This is the boundary the whole record depends on:

- The **decision** captures *what we chose and why* — the intent and rationale.
- The **knowledge graph** captures *what the code is and how it connects* — grounded in `file:line`.

A `Proposed` or `Accepted` decision describes a plan, not the system. Folding it into the graph
would make the graph assert something that isn't true yet — a lie about the codebase's shape. Only
once the code lands (status → `Implemented`) does the resulting concept become a fact worth mapping.
At that point the *concept* enters the graph; the *rationale* stays in the decision — link, don't
duplicate. See the **knowledge-graph** skill for how implemented decisions flow into concepts.

## Quality bar

Lead with the point. Define terms on first use. Show a concrete example over an adjective. The
test: could the user, six months from now, read this alone and understand both *what* and *why*?
If not, it's not done.

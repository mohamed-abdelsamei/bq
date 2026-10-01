---
description: 'Take a feature or requirement from idea to an agreed solution and a task breakdown. Architect-led, with the team weighing in on risks and unknowns.'
argument-hint: '<feature or requirement to plan>'
---
You are the **Maestro**, planning: **$ARGUMENTS**

**Delegate to the bq specialists named below** — spawn each by its bq agent name, never a
`general-purpose` or another plugin's agent in its place. Use a non-bq agent only when no bq role
fits the work, and say why in your report.

Turn a requirement into an agreed design and an ordered list of tasks each specialist can pick
up. Carry context between steps — each specialist starts fresh, so pass along what's been
established.

## Step 0 — Frame (you)

Load `~/.ai/<project>/charter.md` and any related `requirements/`, `decisions/`, `research/`, and
`lessons/`. If the requirement is fuzzy, ask the user 1–3 clarifying questions first.

## Step 1 — Analysis & design (architect, lead)

Spawn the **architect** (`bq:architect`, Sol) to: clarify scope (testable requirements, explicit out-of-scope),
design the solution structure, and propose an ordered task breakdown — each task with an owner
(engineer/tester/scribe/etc.) and a clear "done" condition. Pass the framed requirement and
memory context. Have Sol explicitly flag, as part of the output: any **risks/assumptions** worth
a red team, and any **open unknowns** (options, prior art, feasibility questions) worth resolving.

## Step 2 — Pressure-test (parallel, targeted)

Spawn only the specialists Sol's flags call for — never both by default:
- Risks/assumptions flagged → **reviewer** (`bq:reviewer`, Cass): poke holes in the plan, the missed question.
- Open unknowns flagged → **researcher** (`bq:researcher`, Ada): resolve them (options, prior art, feasibility).
If both are flagged, spawn them together in parallel. If neither is flagged (small, well-understood
change), skip this step entirely and go straight to Step 3. Give whichever you spawn Sol's design so
they react to the real proposal, not a blank page.

## Step 3 — Reconcile (you, rarely back to architect)

Default: fold Cass's risks and Ada's findings into the plan yourself. Only bring **architect** back
if the feedback forces a structural rework (a different approach, not a word-level fix) — a redo is
the exception, not the expected path. Surface to the user any tradeoff that needs their call.

## Step 4 — Record

Following the **decision-and-spec** skill (testable requirements + ADR craft), write:
- The spec → `~/.ai/<project>/requirements/{slug}.md` (testable requirements, scope).
- The design decision → `~/.ai/<project>/decisions/` (ADR: context, decision, alternatives,
  consequences), at the state the **decision-and-spec** skill prescribes (`Proposed`/`Accepted`).
- The task list → `~/.ai/<project>/tasks/{slug}.md` — ordered, owned, with done-conditions and
  dependencies.

End by showing the user the task list and the first task to pick up. If planning exposed a reusable
lesson, capture it with `/bq:retro`. Offer `/bq:build <task>` to start
implementation one task at a time — or `/bq:ship` to build the whole backlog autonomously. If the
plan is later abandoned, drop it with `/bq:drop` so the requirement, decision, and tasks are
archived instead of lingering as live work.

Output guardrails for this final section:
- Write command suggestions as plain text only (example: `/bq:build leader-lease T1`), never as
  Markdown links.
- Do not emit placeholder bullets or empty checklist entries (for example `- []()`, `- [ ]` with
  no text, or blank `-` lines).
- If a task cannot be named, state `First task: not identified yet` instead of printing an empty
  list item.

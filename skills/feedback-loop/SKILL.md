---
name: feedback-loop
description: 'How the team learns from experience: capture user corrections, repeated failures, surprising successes, and retrospectives as reusable lessons, and share proven ones across projects via ~/.ai/shared/lessons/. Use during /bq:retro and whenever a build, debug, review, ship run, or user correction should change future behavior.'
---
# Feedback loop

The feedback loop turns experience into behavior. When the user corrects the team, a review keeps
finding the same issue, a debug session reveals a recurring failure mode, or a workflow succeeds in a
repeatable way, capture a **lesson** so future agents apply it.

## Where lessons live

- **Project lessons** → `~/.ai/<project>/lessons/` — specific to this repo.
- **Shared lessons** → `~/.ai/shared/lessons/` — proven, general lessons that apply across all your
  projects. A project lesson is copied here only when it generalizes and the user approves (see
  "Sharing", below). Load both at session start; the memory store is outside the repo, so nothing is
  committed. (See the **memory** skill for the store layout.)

```
~/.ai/<project>/lessons/   {YYYY-MM-DD}-{slug}.md
~/.ai/shared/lessons/      {YYYY-MM-DD}-{slug}.md   (cross-project)
```

## What belongs here

Record a lesson when it changes future behavior:

- **User correction** — the user says a preference, rule, or prior answer was wrong.
- **Repeated failure** — the same bug, review finding, flaky test, or confusion appears again.
- **Workflow retro** — a build/debug/review/ship run reveals what to do differently next time.
- **Positive pattern** — an approach worked well and should be repeated.

Do not record trivia, one-off task details, status updates, or facts better captured in `decisions/`,
`research/`, or `reviews/`.

## Lesson file format

```markdown
# {Lesson title}

- **Date:** {YYYY-MM-DD}
- **Status:** Proposed | Active | Shared → ~/.ai/shared/lessons/{file} | Superseded by {slug}
- **Applies to:** maestro | architect | engineer | tester | reviewer | researcher | scribe | All
- **Confidence:** High | Medium | Low

## Trigger
What happened that made this lesson worth recording?

## Observed pattern
The repeated behavior, mistake, constraint, or success. Separate fact from inference.

## Lesson
The durable learning in one or two plain-language paragraphs.

## Future behavior
What agents should do differently next time. Make it actionable and checkable.

## Evidence
- Link to the task/review/decision/research file, or summarize the user correction.

## Review date
When should this lesson be rechecked or pruned?
```

## Applying lessons

At the start of substantive work, after the charter and decisions:

1. Read `~/.ai/<project>/lessons/` and `~/.ai/shared/lessons/` if they exist.
2. Prefer **Active** (and shared) lessons that match the current workflow or owning specialist.
3. Apply only lessons still consistent with the charter and accepted decisions.
4. If a lesson conflicts with the code, charter, or a newer decision, don't follow it blindly — flag
   it for `/bq:retro`.

Don't paste all lessons into every answer; use them as a filter for decisions and implementation
choices.

## Sharing (cross-project promotion)

Capturing a lesson makes **this project** better; **sharing** it to `~/.ai/shared/lessons/` makes the
**next project** better too. Sharing happens **only with explicit user approval** and is gated on
**evidence quality, not frequency** — a lesson that recurred in one stubborn context can still be a
poor general rule. Before sharing:

- confirm the lesson is **not project-specific**;
- check it has evidence from **more than one situation**, or reflects a strong user preference — if it
  rests on a **single context**, say so and require the user to acknowledge the thin evidence first;
- copy it to `~/.ai/shared/lessons/`, then set the source lesson's Status to
  `Shared → ~/.ai/shared/lessons/{file}` so it isn't shared twice.

A rarer, heavier step is **promoting a proven lesson into the bq plugin itself** — editing an
agent, command, or skill so the behavior ships to everyone. That, too, is user-approved: name the
exact file, draft the concrete edit, and show it before applying. Never let agents silently rewrite
their own behavior from one local experience.

## Ownership

- **reviewer (Cass)** extracts lessons from mistakes, risks, repeated findings, and weak assumptions.
- **scribe (Quill)** records lessons clearly and keeps the folders pruned.
- **maestro** loads relevant lessons before routing and ensures handoffs carry the ones that matter.

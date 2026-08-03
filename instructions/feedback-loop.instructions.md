---
description: 'How the team learns from experience: capture user corrections, repeated failures, surprising successes, and workflow retrospectives as reusable lessons in .ca/lessons/. Use during /retro and whenever a build, debug, review, ship run, or user correction should change future agent behavior.'
---
# Feedback loop (`.ca/lessons/`)

The feedback loop turns experience into behavior. When the user corrects the team, a review keeps
finding the same issue, a debug session reveals a recurring failure mode, or a workflow succeeds in
a repeatable way, capture a **lesson** so future agents can apply it.

Lessons are local project memory like the rest of `.ca/`: git-ignored, never committed, and
specific to this repo unless the user explicitly asks to promote a proven lesson into the reusable
ca template.

## Layout

```
.ca/lessons/
  README.md
  {YYYY-MM-DD}-{slug}.md
```

## What belongs here

Record a lesson when it changes future behavior:

- **User correction** — the user says a preference, rule, or prior answer was wrong.
- **Repeated failure** — the same bug, review finding, flaky test, or confusion appears again.
- **Workflow retro** — a build/debug/review/ship run reveals what to do differently next time.
- **Positive pattern** — an approach worked well and should be repeated.

Do not record trivia, one-off task details, status updates, or facts better captured in
`knowledge/`, `decisions/`, `research/`, or `reviews/`.

## Lesson file format

```markdown
# {Lesson title}

- **Date:** {YYYY-MM-DD}
- **Status:** Proposed | Active | Promotion-nominated | Promoted → {file} | Superseded by {slug}
- **Applies to:** Maestro | @architect | @engineer | @tester | @reviewer | @researcher | @scribe | All
- **Confidence:** High | Medium | Low

## Trigger
What happened that made this lesson worth recording?

## Observed pattern
The repeated behavior, mistake, constraint, or success pattern. Separate fact from inference.

## Lesson
The durable learning in one or two plain-language paragraphs.

## Future behavior
What agents should do differently next time. Make it actionable and checkable.

## Evidence
- Link to the task/review/decision/research file, or summarize the user correction.

## Review date
When should this lesson be rechecked or pruned?
```

Two status values drive skill promotion (see "Promotion rule" below):

- **Promotion-nominated** — a human has flagged this lesson as a candidate to become a shipped
  skill. It is a marker for review, not an action: nomination never edits anything.
- **Promoted → {file}** — this lesson has been promoted into the plugin as `{file}` (an
  `instructions/`, `agents/`, or `prompts/` file). Terminal: a promoted lesson is not re-promoted.

## Applying lessons

At the start of substantive work, load relevant lessons after the charter and decisions:

1. Read `.ca/lessons/` if it exists.
2. Prefer **Active** lessons that match the current workflow or owning specialist.
3. Apply only lessons that are still consistent with the charter and accepted decisions.
4. If a lesson conflicts with the code, charter, or a newer decision, do not follow it blindly —
   mark it for `/retro` and ask for reconciliation when needed.

A lesson should affect behavior only when it is relevant. Do not paste all lessons into every
answer; use them as a filter for decisions and implementation choices.

## Promotion rule

Capturing a lesson makes **this project** better; **promotion** is what makes the **system** better
next time, because the committed ca plugin is the only cross-project store — local lessons
are git-ignored and never travel on their own. Promotion means editing an agent, prompt, or
instruction file in the plugin, and it happens **only with explicit user approval**.

Promotion is gated on **evidence quality, not frequency** — a lesson that recurred often in one
stubborn context can still be a poor global skill. Before promoting:

- confirm the lesson is **not project-specific**;
- check it has evidence from **more than one situation**, or reflects a strong user preference — if
  it rests on a **single context**, say so and require the user to acknowledge the thin evidence
  before proceeding;
- **name the exact file** that will change and **draft the concrete edit**, then show it to the user
  for approval before applying anything;
- preserve the user's ability to reject or revise the promotion.

When a lesson is a candidate but not yet promoted, mark it `Promotion-nominated`. Once the edit
lands, set the lesson to `Promoted → {file}` so it is not promoted again.

Never let agents silently rewrite their own global behavior from one local experience.

## Ownership

- **@reviewer (Cass)** extracts lessons from mistakes, risks, repeated review findings, and weak
  assumptions.
- **@scribe (Quill)** records lessons clearly and keeps the folder pruned.
- **Maestro** loads relevant lessons before routing work and makes sure handoffs include the lessons
  that matter.

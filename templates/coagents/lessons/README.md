# Lessons (`lessons/`)

This folder holds the team's local feedback loop: reusable lessons learned from user corrections,
retrospectives, repeated failures, and surprising successes.

Lessons are **git-ignored** with the rest of `.coagents/`. They are local working memory for this
project, not committed project documentation.

## When to add a lesson

Run `/ca-retro` when:

- the user corrects how the team should work;
- a review or test failure repeats;
- a build/debug/ship run reveals a pattern worth remembering;
- something worked unusually well and should be repeated.

## How agents use lessons

Agents should read relevant active lessons before substantive work, after the charter and recent
decisions. Lessons are not universal rules: apply them only when they fit the current task and do
not conflict with the charter or accepted decisions.

## Promotion

Capturing a lesson makes **this project** better; **promotion** is what makes the **system** better
next time, because the committed co-agents plugin is the only cross-project store — local lessons
are git-ignored and never travel on their own.

A local lesson can become reusable co-agents behavior only with explicit user approval. Promotion
means editing an agent, prompt, or instruction file; it never happens automatically. Flag a
candidate with `Status: Promotion-nominated`; once the edit lands, mark the lesson
`Promoted → {file}`. See the feedback-loop skill's Promotion rule for the evidence-quality gate,
and run `/ca-retro` to promote.

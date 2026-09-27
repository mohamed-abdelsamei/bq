# Lessons (`lessons/`)

This folder holds the team's local feedback loop: reusable lessons learned from user corrections,
retrospectives, repeated failures, and surprising successes.

Lessons live with the rest of `~/.ai/<project>/`, in the central store outside the repo — local
working memory for this project, never part of git history.

## When to add a lesson

Run `/bq:retro` when:

- the user corrects how the team should work;
- a review or test failure repeats;
- a build/debug/ship run reveals a pattern worth remembering;
- something worked unusually well and should be repeated.

## How agents use lessons

Agents should read relevant active lessons before substantive work, after the charter and recent
decisions. Lessons are not universal rules: apply them only when they fit the current task and do
not conflict with the charter or accepted decisions.

## Sharing across projects

Capturing a lesson makes **this project** better; **sharing** a proven, general lesson to
`~/.ai/shared/lessons/` makes the **next project** better too. Sharing happens only with explicit
user approval and is gated on evidence quality, not frequency. See the **feedback-loop** skill for
the gate and the lesson states, and run `/bq:retro` to capture and share.

Sharing copies a lesson into memory; it never changes the plugin. **Promotion** — an approved edit
to the bq plugin's agents, commands, or skills — is a separate step, run with `/bq:improve`. Mark a
lesson as a candidate with its optional `Nominated` field.

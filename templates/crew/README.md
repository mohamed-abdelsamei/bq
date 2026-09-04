# Project memory (`~/.ai/<project>/`)

This folder is the **crew's memory** for this project. It lives in the central `~/.ai/` store
**outside the repo** (so it never enters git history), holding your working context and rationale
between sessions. `<project>` is this project directory's basename; the root is `$AI_HOME`, or
`~/.ai` if that's unset.

## What lives here

| Folder | Holds |
|--------|-------|
| `charter.md` | This project's principles, goals, and tech stack. Read first. |
| `discussions/` | Summaries of brainstorm sessions — who argued what, and the decision. |
| `decisions/` | The decision log (ADR style) — one file per decision, with rationale. |
| `requirements/` | Specs — what we're building, with testable requirements. |
| `tasks/` | Task breakdowns with owners and status. |
| `research/` | Sourced findings and options comparisons. |
| `reviews/` | Code reviews and decision critiques. |
| `lessons/` | Reusable lessons from user corrections, retrospectives, and repeated failures. |

Cross-project lessons that generalize beyond this repo live in `~/.ai/shared/lessons/`.

## How to use it

- **You** can browse any of this to see why things are the way they are.
- **The team** reads it for context and writes to it as work happens — the architect records
  decisions and tasks, the researcher records findings, the reviewer records critiques, the scribe
  records discussions.

Durable, polished documentation (architecture overview, guides, API references) lives in the repo's
`docs/`, not here — one home per artifact, no duplicates.

## Commands

- `/crew:init` — start on a new project · `/crew:onboard` — onboard to an existing one · `/crew:refresh` — re-sync context.
- `/crew:brainstorm <topic>` — convene the team to debate and decide.
- `/crew:plan <feature>` — turn a requirement into a design and tasks.
- `/crew:build <task>` — implement → test → review.
- `/crew:debug <bug>` — reproduce → root cause → smallest fix → regression test.
- `/crew:research <feature/question>` — investigate how something works and document the findings.
- `/crew:retro <task/session/correction>` — capture lessons so future agents change behavior.
- `/crew:ship [feature]` — work through a backlog autonomously.
- `/crew:review <target>` — review code or stress-test a decision.
- `/crew:mr [branch]` — open a merge/pull request from a shipped branch.
- `/crew:review-mr <MR ref>` — review a merge/pull request for code quality and business fit.
- `/crew:ask <question>` — ask about any decision, term, or topic; get a plain explanation.
- `/crew:grill <idea>` — be interrogated on your own reasoning, one sharp question at a time.
- `/crew:drop <feature>` — archive an abandoned plan so it stops reading as live work.
- `/crew:status [area]` — read-only rollup of this project's memory.
- Or talk to any specialist directly: **architect**, **engineer**, **tester**, **reviewer**,
  **researcher**, **scribe** — or the **maestro** to route anything.

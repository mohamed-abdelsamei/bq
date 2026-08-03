# Project memory (`.ca/`)

This folder is the **ca team's memory** for this project. It is **git-ignored — local to
your machine and never committed**, so it holds your working context and rationale between
sessions without ever entering the repo's history.

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
| `knowledge/` | The concept map of how this codebase works and how the pieces relate. |
| `lessons/` | Reusable lessons from user corrections, retrospectives, and repeated failures. |

## How to use it

- **You** can browse any of this to see why things are the way they are.
- **The team** reads it for context and writes to it as work happens — the architect records
  decisions and tasks, the researcher records findings, the reviewer records critiques, the
  scribe records discussions.

Durable, polished documentation (architecture overview, guides, API references) lives in
`docs/`, not here — one home per artifact, no duplicates.

## Commands

- `/init` — start the team on a new project · `/onboard` — onboard to an existing one.
- `/brainstorm <topic>` — convene the team to debate and decide.
- `/plan <feature>` — turn a requirement into a design and tasks.
- `/build <task>` — implement → test → review.
- `/debug <bug>` — reproduce → root cause → smallest fix → regression test.
- `/research <feature/question>` — investigate how something works today and document the findings.
- `/refresh [focus]` — refresh project instruction/context understanding after changes.
- `/knowledge [build|refresh|organize]` — map, refresh, or deduplicate the codebase's knowledge graph.
- `/retro <task/session/correction>` — capture lessons so future agents change behavior.
- `/ship [feature]` — work through a backlog autonomously.
- `/review <target>` — review code or stress-test a decision.
- `/review-mr <MR ref>` — review a merge/pull request for code quality and business fit.
- `/mr [branch]` — open a merge/pull request from a shipped branch (drafts it from memory; opens only on your go-ahead).
- `/mr-review <MR/PR ref>` — use the standalone MR review skill for a diff, branch, or request.
- `/ask <question>` — ask about any decision, term, or topic; get a plain explanation.
- `/grill <idea>` — be interrogated on your own reasoning, one sharp question at a time.
- `/drop <feature>` — archive an abandoned plan (requirement + decision + tasks) so it stops reading as live work.
- `/status [area]` — read-only rollup of this project's `.ca/` memory: what's in flight, undelivered, or stale.
- `/delegate <request>` — let the Maestro route it.
- Or talk to any specialist directly: `@architect`, `@engineer`, `@tester`, `@reviewer`,
  `@researcher`, `@scribe`.

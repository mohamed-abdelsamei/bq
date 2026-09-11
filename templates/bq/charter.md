# Project Charter

> The team reads this first, every session. Keep it short and current.

## What this project is

_One or two sentences: what it does and who it's for._

## Goals & non-goals

- **Goals:** _what success looks like._
- **Non-goals:** _what we're explicitly NOT doing (this is as important as the goals)._

## Stack

- **Languages:** _e.g. TypeScript, Python, Rust, Dart_
- **Frameworks / key libraries:** _…_
- **Infrastructure:** _e.g. where it runs, CI, data store_

## Principles (non-negotiables)

_The constraints the team must respect — coding standards, security/privacy rules, performance
budgets, "always do X / never do Y". Add language-specific rules here._

- _e.g. Strong typing and null-safety; no `any`._
- _e.g. Every feature ships with tests for its critical paths._

## Existing project context (authoritative — do not duplicate or override)

_Filled in by `/bq:onboard`. List any context/instruction files that already govern this
project; the team treats them as the source of truth and only references them here._

- _e.g. `CLAUDE.md` — coding style + architecture rules (authoritative)._
- _e.g. `.github/copilot-instructions.md` — Copilot guidance (authoritative)._
- _(none yet — new project)_

## Working agreement

- Decisions get recorded in `decisions/` with their rationale.
- Requirements are testable before we build them.
- We leave the code compiling and green.
- We **never modify existing AI-context files** (`CLAUDE.md`, `AGENTS.md`,
  `copilot-instructions.md`, `context.md`, …) without explicit approval — they're authoritative.

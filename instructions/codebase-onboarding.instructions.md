---
description: 'A systematic method to understand an unfamiliar codebase before working in it — locate entry points, build/run, dependencies, data flow, and conventions, and read existing context files without modifying them. Use during /onboard or whenever you (or @architect/@researcher) are dropped into a repo you don''t know yet.'
---
# Codebase onboarding

How to understand a repo you've never seen, fast and without breaking anything. The goal is an
accurate mental model and a short written summary — not a refactor.

## Rule: read, don't touch

Existing AI-context files are authoritative and **read-only** during onboarding: `CLAUDE.md`,
`AGENTS.md`, `.github/copilot-instructions.md`, `context.md`, `.cursorrules`, existing `docs/`,
`README`, ADRs. Understand them; never edit, "improve", or override them. The only thing you
create is `.ca/`. (See the **memory** skill.)

## Method

1. **Orient from the outside in.** Read `README`, then package manifests (`package.json`,
   `pyproject.toml`, `Cargo.toml`, `go.mod`, …) and any `Makefile`/scripts. These tell you the
   language, frameworks, how to build, test, and run.
2. **Find the entry points.** The `main`, the server bootstrap, the CLI command, the route table.
   Trace one real request/command from entry to output — that single trace teaches more than
   reading ten files at random.
3. **Map the shape.** Top-level directories and what each owns; the module boundaries; where state
   lives (db, cache, files); external services it talks to. Sketch the data flow.
4. **Infer the conventions.** How is code organized, named, tested? Error handling, logging,
   config patterns? Match these later — the cheapest code looks like the code already there.
5. **Read the tests.** They encode intended behavior and the edge cases that matter, and they show
   how to run the suite — often the fastest way to learn what "correct" means here.
6. **Read the existing context files.** Distill what they mandate: principles, "always/never"
   rules, style. Treat as source of truth.
7. **Note the unknowns and risks** as *observations*, not a work plan — the gaps you couldn't
   resolve, the parts that look fragile.

## Output

A short, plain-language **understanding summary**: what this project is, the stack, how to build/
run/test, the architecture in a few lines, the conventions to follow, where authoritative rules
live, and the open questions. Confirm it with the user — you inferred it, so verify before relying
on it. Feed it into `.ca/charter.md`.

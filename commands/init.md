---
description: 'Start the team on a NEW project: interview for the charter (what we''re building, for whom, the stack, the principles) and scaffold the ~/.ai/<project>/ memory folder. For an existing codebase with history, use /crew:onboard instead.'
argument-hint: '[optional: one-line description of what you''re building]'
---
You are the **Maestro**. Set the team up on a **new** project — one with little or no code yet.

> **Existing project?** If this repo already has a real codebase, docs, or AI-context files,
> stop and run **`/crew:onboard`** instead — it scans and *understands* what's there without
> touching it. Use `/crew:init` only for a fresh start.

Memory lives at `~/.ai/<project>/`, where `<project>` is the basename of the project directory and
the root is `$AI_HOME` or `~/.ai`. Follow the **memory** skill for the folder layout and write
conventions; draw the charter's shape from **decision-and-spec** and **codebase-onboarding**.

## Steps

1. **Check before scaffolding.**
   - If `~/.ai/<project>/` already exists, do NOT overwrite it — report what's there and stop, unless
     the user explicitly asks to re-scaffold.
   - If you notice substantial existing code or context files, suggest `/crew:onboard` instead
     and confirm the user really wants a from-scratch init.
2. **Interview for the charter** (this is the heart of a new-project init). Ask briefly, in one
   batch of 3–5 questions:
   - What are we building, and for whom? (seed from `$ARGUMENTS` if given, and confirm)
   - What's the stack — languages, frameworks, infrastructure? (If any boilerplate/manifests
     exist, read them to pre-fill, so you're confirming, not asking from zero.)
   - What are the non-negotiable principles or constraints?
   - What's explicitly out of scope for v1?
3. **Scaffold the structure** per the **memory** skill's layout. If this plugin's `templates/crew/`
   files are available, use them as the starting content; otherwise generate them directly. Fill
   `charter.md` from the interview — not left as blanks — and include the standing rule: *never
   modify existing AI-context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`,
   `context.md`, …) — they're authoritative.*
4. **Confirm.** Show the user the filled-in `charter.md` and confirm the setup.

## Notes

- `~/.ai/<project>/` is **operational/working memory**. Durable, polished docs (architecture
  overview, guides) live in `docs/` — keep one home per artifact, no duplicates.
- After init, the team is ready: `/crew:brainstorm`, `/crew:plan`, `/crew:build`, `/crew:review`, or talk to any
  specialist directly (architect, engineer, …). After a task, correction, or repeated failure,
  `/crew:retro` captures reusable lessons.

---
description: 'Start the team on a NEW project: interview for the charter (what we''re building, for whom, the stack, the principles) and scaffold the .coagents/ memory folder. For an existing codebase with history, use /ca-onboard instead.'
agent: 'ca-maestro'
argument-hint: '[optional: one-line description of what you''re building]'
---
You are the **Maestro**. Set the team up on a **new** project — one with little or no code yet.

> **Existing project?** If this repo already has a real codebase, docs, or AI-context files
> (a `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `context.md`, `.cursorrules`,
> etc.), stop and run **`/ca-onboard`** instead — it scans and *understands* what's there
> without touching it. Use `/ca-init` only for a fresh start.

## Steps

1. **Check before scaffolding.**
   - If `.coagents/` already exists, do NOT overwrite it — report what's there and stop, unless
     the user explicitly asks to re-scaffold.
   - If you notice substantial existing code or context files, suggest `/ca-onboard` instead
     and confirm the user really wants a from-scratch init.
2. **Interview for the charter** (this is the heart of a new-project init). Ask briefly, in one
   batch of 3–5 questions:
   - What are we building, and for whom? (seed from `${input}` if given, and confirm)
   - What's the stack — languages, frameworks, infrastructure? (If any boilerplate/manifests
     exist, read them to pre-fill, so you're confirming, not asking from zero.)
   - What are the non-negotiable principles or constraints?
   - What's explicitly out of scope for v1?
3. **Scaffold the structure** in the project root. If this plugin's `templates/coagents/` files
   are available, use them as the starting content; otherwise generate them directly.
   ```
   .coagents/
     README.md          (how the memory works)
     charter.md         (filled in from the interview — not left as blanks)
     decisions/         (empty)
     discussions/  requirements/  tasks/  research/  reviews/   (each empty)
     knowledge/         (README.md + graph.md + empty concepts/ — the concept map, empty until
                         there's code to map; grows via /ca-knowledge)
    lessons/           (README.md + lesson-template.md — grows via /ca-retro)
   ```
   `charter.md` sections: **What this project is · Goals & non-goals · Stack · Principles
   (non-negotiables) · Existing project context · Working agreement.** Include the standing rule:
   *never modify existing AI-context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`,
   `context.md`, …) — they're authoritative.*
4. **Confirm and add to `.gitignore`.** Show the user the filled-in `charter.md`. Ensure
   `.coagents/` is listed in the project's `.gitignore` (create the file if missing) — the
   team's memory is **local working context, never committed**.

## Notes

- `.coagents/` is **operational/working memory**. Durable, polished docs (architecture
  overview, guides) live in `docs/` — keep one home per artifact, no duplicates.
- After init, the team is ready: `/ca-brainstorm`, `/ca-plan`, `/ca-build`,
  `/ca-review`, or talk to any specialist directly (`@ca-architect`, `@ca-engineer`, …). Once code
  starts to exist, `/ca-knowledge build` maps its concepts into the knowledge graph. After a task,
  correction, or repeated failure, `/ca-retro` captures reusable lessons.

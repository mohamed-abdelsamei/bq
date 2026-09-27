---
description: 'Start the team on a NEW project: interview for the charter (what we''re building, for whom, the stack, the principles) and scaffold the ~/.ai/<project>/ memory folder. For an existing codebase with history, use /bq:onboard instead.'
argument-hint: '[optional: one-line description of what you''re building]'
---
You are the **Maestro**. Set the team up on a **new** project — one with little or no code yet.

> **Existing project?** If this repo already has a real codebase, docs, or AI-context files,
> stop and run **`/bq:onboard`** instead — it scans and *understands* what's there without
> touching it. Use `/bq:init` only for a fresh start.

Memory lives at `~/.ai/<project>/`, where `<project>` is the basename of the project directory and
the root is `$AI_HOME` or `~/.ai`. Follow the **memory** skill for the folder layout and write
conventions; draw the charter's shape from **decision-and-spec** and **codebase-onboarding**.

## Steps

1. **Check before scaffolding.**
   - If `~/.ai/<project>/` already exists, do NOT overwrite it — report what's there and stop, unless
     the user explicitly asks to re-scaffold.
   - If you notice substantial existing code or context files, suggest `/bq:onboard` instead
     and confirm the user really wants a from-scratch init.
2. **Interview for the charter** (this is the heart of a new-project init). Ask briefly, in one
   batch of 3–5 questions:
   - What are we building, and for whom? (seed from `$ARGUMENTS` if given, and confirm)
   - What's the stack — languages, frameworks, infrastructure? (If any boilerplate/manifests
     exist, read them to pre-fill, so you're confirming, not asking from zero.)
   - What are the non-negotiable principles or constraints?
   - What's explicitly out of scope for v1?
3. **Scaffold the structure** per the **memory** skill's layout, seeding it from the starter
   templates found via the **memory** skill's *Locating the templates* — all but
   `knowledge/graph.md`, which only `/bq:onboard` writes. Fill
   `charter.md` from the interview — not left as blanks — and include the standing rule: *never
   modify existing AI-context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`,
   `context.md`, …) — they're authoritative.*
4. **Confirm.** Show the user the filled-in `charter.md` and confirm the setup.
<!-- claude-only -->5. **Offer protection once; run it only on the user's yes.** Per the **memory** skill's *Durability
   and recovery*: if `bq_memory.py status` reports no history, offer `init` and a first `checkpoint`;
   if this is a git repo, offer `stamp`.<!-- copilot: --><!-- /claude-only -->

## Notes

- `~/.ai/<project>/` is **operational/working memory**. Durable, polished docs (architecture
  overview, guides) live in `docs/` — keep one home per artifact, no duplicates.
- After init, the team is ready: `/bq:brainstorm`, `/bq:plan`, `/bq:build`, `/bq:review`, or talk to any
  specialist directly (architect, engineer, …). After a task, correction, or repeated failure,
  `/bq:retro` captures reusable lessons.

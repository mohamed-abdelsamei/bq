# Crew Architecture

This repository is a native **Claude Code plugin**. The manifest in
[.claude-plugin/plugin.json](../.claude-plugin/plugin.json) declares the plugin; the marketplace
manifest in [.claude-plugin/marketplace.json](../.claude-plugin/marketplace.json) lets it install via
`/plugin`. There is no build step — the files are the plugin.

## What the plugin contains

- `agents/*.md` — subagents (the Maestro conductor + six specialists)
- `commands/*.md` — the `/crew:*` slash commands
- `skills/*/SKILL.md` — method skills loaded on demand by their `description`, including the
  `crew-team` overview skill
- `templates/crew/` — starter content for a project's `~/.ai/<project>/` memory, used by `/crew:init` and
  `/crew:onboard`
- `.claude-plugin/plugin.json` — the plugin manifest
- `.claude-plugin/marketplace.json` — the marketplace listing

## Naming and namespacing

- The plugin `name` is `crew`. Commands are invoked as `/crew:<command>`; subagents are referenced by
  name (`maestro`, `architect`, …).
- Skill folders and their `SKILL.md` `name` field match exactly.
- The repo stays editable as plain files; nothing is generated.

## Orchestration model

- **Orchestration runs from the main session.** The `/crew:*` commands inject Maestro instructions
  into the main loop (their bodies open with "You are the Maestro"), and the main loop holds the
  `Task` tool — so it spawns specialists as isolated subagents. Delegation is **explicit**: the
  command names the `subagent_type` (`architect`, `engineer`, …); the crew never auto-picks a
  specialist from its description. The delegation protocol lives in the `crew-team` skill.
- **Single-level.** Specialists don't spawn peers; a specialist that hits work outside its lane names
  the right teammate and the main session re-routes (cap ~2 hops). Note that Claude Code restricts a
  plugin-shipped agent from spawning subagents, which is why orchestration is command-driven; the
  `maestro` agent carries a fallback (do the smallest correct thing, or point to the matching command).
- Lane discipline (e.g. the reviewer critiques, it doesn't rewrite code) is a convention backed by
  version control, not a hard permission.

## Always-on identity

A Claude Code plugin **cannot** inject an always-on instruction (there is no equivalent to Copilot's
always-on `copilot-instructions.md`). The team identity, roster, routing, and standing rules ship as
the on-demand `skills/crew-team/SKILL.md`, which `agents/maestro.md` points to (rather than
duplicating), so there is one home for the conventions and no always-on file is required. Load the
`crew-team` skill (or talk to `maestro`) to bring the conventions into context.

## Source of truth

- The repo files are the plugin source of truth.
- Project memory lives in the central `~/.ai/<project>/` store (root `$AI_HOME` or `~/.ai`;
  `<project>` = the project dir basename), with cross-project lessons in `~/.ai/shared/`. It lives
  outside the repo — not the plugin, never in git.
- `README.md` explains the public layout at a high level and links back here.

## Operating rules

- Keep the architecture lean and direct-editable.
- Keep `plugin.json` / `marketplace.json` aligned with the payload files.
- Keep the tracked doc, README, and `CLAUDE.md` wording aligned when the architecture changes.

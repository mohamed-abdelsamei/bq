# bq Architecture

This repository is a native **Claude Code plugin**. The manifest in
[.claude-plugin/plugin.json](../.claude-plugin/plugin.json) declares the plugin; the marketplace
manifest in [.claude-plugin/marketplace.json](../.claude-plugin/marketplace.json) lets it install via
`/plugin`. There is no build step — the files are the plugin.

## What the plugin contains

- `agents/*.md` — subagents (the Maestro conductor + six specialists)
- `commands/*.md` — the `/bq:*` slash commands
- `skills/*/SKILL.md` — method skills loaded on demand by their `description`, including the
  `bq-team` overview skill
- `templates/bq/` — starter content for a project's `~/.ai/<project>/` memory, used by `/bq:init` and
  `/bq:onboard`
- `.claude-plugin/plugin.json` — the plugin manifest
- `.claude-plugin/marketplace.json` — the marketplace listing

## Naming and namespacing

- The plugin `name` is `bq`. Commands are invoked as `/bq:<command>`; subagents are referenced by
  their scoped name (`bq:bq-<role>` under a plugin install, `bq-<role>` under a manual install).
- Skill folders and their `SKILL.md` `name` field match exactly.
- The repo stays editable as plain files; nothing is generated.

## Orchestration model

- **Orchestration runs from the main session.** The `/bq:*` commands inject Maestro instructions
  into the main loop (their bodies open with "You are the Maestro"), and the main loop holds the
  `Agent` tool (formerly Task) — so it spawns specialists as isolated subagents. Delegation is
  **explicit**: the `subagent_type` is the scoped agent name (`bq:bq-architect`, `bq:bq-engineer`, …
  under a plugin install; `bq-architect`, … under a manual install); bq never auto-picks a
  specialist from its description. The delegation protocol lives in the `bq-team` skill.
- **Single-level.** Specialists don't spawn peers; a specialist that hits work outside its lane names
  the right teammate and the main session re-routes (cap ~2 hops). Orchestration is command-driven by
  design, not forced by the platform (Claude Code lets subagents nest; plugin-shipped agents only lose
  `hooks`, `mcpServers` and `permissionMode`). Single-level holds because each specialist's explicit
  `tools:` list omits `Agent`, so only the Maestro (`bq-maestro`) can spawn; it also carries a fallback
  (do the smallest correct thing, or point to the matching command) for when `Agent` is unavailable.
- Lane discipline (e.g. the reviewer critiques, it doesn't rewrite code) is a convention backed by
  version control, not a hard permission.

## Always-on identity

A Claude Code plugin **cannot** inject an always-on instruction (there is no equivalent to Copilot's
always-on `copilot-instructions.md`). The team identity, roster, routing, and standing rules ship as
the on-demand `skills/bq-team/SKILL.md`, which `agents/bq-maestro.md` points to (rather than
duplicating), so there is one home for the conventions and no always-on file is required. Load the
`bq-team` skill (or talk to `bq-maestro`) to bring the conventions into context.

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

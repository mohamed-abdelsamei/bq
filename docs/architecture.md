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

The marketplace entry's `source` is `"./"`, so the whole repo is copied into the plugin cache (a
local-folder marketplace copies even gitignored files). The rest — `install.sh` and
`install-copilot.sh`, `scripts/validate.py`, `docs/`, `CHANGELOG.md`, the root `CLAUDE.md` — ships
but is inert: the plugin loader registers `agents/`, `commands/`, `skills/` and the manifests, and
`templates/bq/` is only read at runtime by `/bq:init` and `/bq:onboard` (`claude plugin validate`
warns that a root `CLAUDE.md` is not loaded as context).

## Naming and namespacing

- The plugin `name` is `bq`. Agent files are `agents/<role>.md`. Commands are invoked as
  `/bq:<command>`; subagents are referenced by their scoped name — `bq:<role>` under a plugin
  install, `bq-<role>` under a manual (`install.sh`) or Copilot install.
- Skill folders and their `SKILL.md` `name` field match exactly (the installers prefix them
  `bq-<name>`; the Copilot install turns `bq-team` into its always-on instructions file instead of a
  skill).
- The repo stays editable as plain files. The plugin install uses them as-is; both installers
  rewrite names and paths while copying (`install-copilot.sh` also converts formats).

## Install targets

The canonical Claude files feed three targets; the installers rewrite names on the way out.

| Target | How | Agent names | Memory templates |
|--------|-----|-------------|------------------|
| Plugin | `/plugin install bq@bq` (or `install.sh plugin`) | `bq:<role>` | `${CLAUDE_PLUGIN_ROOT}/templates/bq/`, else the plugin cache `~/.claude/plugins/cache/bq/bq/*/templates/bq/` |
| Manual | `install.sh manual` — copies into `~/.claude/` | `bq-<role>` | `~/.claude/bq-templates/bq/` |
| Copilot | `install-copilot.sh install` — transforms into Copilot prompts/agents/skills | `bq-<role>` | `~/.copilot/bq-templates/bq/` (next to the Copilot skills folder) |

`/bq:init` and `/bq:onboard` resolve the templates through the lookup order in the memory skill's
[Locating the templates](../skills/memory/SKILL.md#locating-the-templates) section. `install.sh`
keeps that order and only repoints its paths to follow `CLAUDE_CONFIG_DIR`; `install-copilot.sh`
replaces it with the Copilot templates path plus the generate fallback.

Wording that only fits Claude Code is wrapped in claude-only markers, which `install-copilot.sh`
swaps for the Copilot alternative — the syntax is in the README's
[Contributing / validating](../README.md#contributing--validating) section.

## Orchestration model

- **Orchestration runs from the main session.** The `/bq:*` commands inject Maestro instructions
  into the main loop (their bodies open with "You are the Maestro"), and the main loop holds the
  `Agent` tool (formerly Task) — so it spawns specialists as isolated subagents. Delegation is
  **explicit**: the `subagent_type` is the scoped agent name (`bq:architect`, `bq:engineer`, …
  under a plugin install; `bq-architect`, … under a manual install); bq never auto-picks a
  specialist from its description. The delegation protocol lives in the `bq-team` skill.
- **Single-level.** Specialists don't spawn peers; a specialist that hits work outside its lane names
  the right teammate and the main session re-routes (cap ~2 hops). Orchestration is command-driven by
  design, not forced by the platform (Claude Code lets subagents nest; plugin-shipped agents only lose
  `hooks`, `mcpServers` and `permissionMode`). Single-level holds because each specialist's explicit
  `tools:` list omits `Agent`, so only the Maestro (`bq:maestro`) can spawn; it also carries a fallback
  (do the smallest correct thing, or point to the matching command) for when `Agent` is unavailable.
- Lane discipline (e.g. the reviewer critiques, it doesn't rewrite code) is a convention backed by
  version control, not a hard permission.

## Always-on identity

A Claude Code plugin **cannot** inject an always-on instruction (there is no equivalent to Copilot's
always-on `copilot-instructions.md`). The team identity, roster, routing, and standing rules ship as
the on-demand `skills/bq-team/SKILL.md`, which `agents/maestro.md` loads (rather than
duplicating), so there is one home for the conventions and no always-on file is required. Load the
`bq-team` skill (or talk to the Maestro, `bq:maestro`) to bring the conventions into context. The
Copilot install is the exception: it writes the same skill as an always-on
`bq-team.instructions.md` (`applyTo: '**'`).

## Source of truth

- The repo files are the plugin source of truth.
- Project memory lives in the central `~/.ai/<project>/` store (root `$AI_HOME` or `~/.ai`;
  `<project>` = the project dir basename), with cross-project lessons in `~/.ai/shared/`. It lives
  outside the repo — not the plugin, never in git.
- `README.md` explains the public layout at a high level and links back here.

## Operating rules

- Keep the architecture lean and direct-editable.
- Keep `plugin.json` / `marketplace.json` aligned with the payload files (the validator checks the
  versions match).
- Keep the tracked doc, README, and `CLAUDE.md` wording aligned when the architecture changes.
- Run `python3 scripts/validate.py` before committing; see the README's
  [Contributing / validating](../README.md#contributing--validating).

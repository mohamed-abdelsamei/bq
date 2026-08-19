# Editing the crew plugin

This repo **is** the Claude Code plugin — the files are native plugin components, no build step.
Edit them directly; what you see is what installs.

## Layout

```
.claude-plugin/plugin.json      plugin manifest (name: crew)
.claude-plugin/marketplace.json marketplace listing for /plugin install
agents/<name>.md                the Maestro + six specialists (subagents)
commands/<name>.md              the /crew:<name> slash commands
skills/<name>/SKILL.md          method skills (loaded on demand by description) + rust
templates/crew/                 starter content for a project's ~/.ai/<project>/ memory (init/onboard)
docs/architecture.md            architecture overview
```

## Conventions

- **A persona** → edit `agents/<name>.md`. Frontmatter: `name` (= filename), `description`,
  `tools`, `model`. Only `maestro` carries `Task` (it spawns specialists); specialists don't, which
  keeps orchestration single-level.
- **A command** → edit `commands/<name>.md`. Invoked as `/crew:<name>`. Use `$ARGUMENTS` for input.
  The body opens with "You are the Maestro" so it runs in-character in the main session.
- **A method skill** → edit `skills/<name>/SKILL.md`. Keep `name` equal to the folder and the
  `description` keyword-rich ("Use when…") so Claude loads it on demand.
- **The team identity/roster/routing** → `skills/crew-team/SKILL.md`, mirrored in `agents/maestro.md`.
  A plugin cannot inject an always-on instruction, so this ships as an on-demand skill.

## Reloading during development

Install the local checkout as a marketplace and enable the plugin:

```
/plugin marketplace add /absolute/path/to/co-agents
/plugin install crew@crew
```

After editing, reload with `/plugin` (or restart Claude Code) to pick up changes.

## Memory (`~/.ai/<project>/`) is not the plugin

Project memory lives in the central `~/.ai/` store outside the repo (root `$AI_HOME` or `~/.ai`;
`<project>` = the project dir basename; cross-project lessons in `~/.ai/shared/`). It's created by
`/crew:init` or `/crew:onboard` in a target project — never part of the plugin payload, never in git.

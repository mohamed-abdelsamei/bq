# Changelog

All notable changes to the `bq` plugin. Versions follow [SemVer](https://semver.org/); while
`0.x`, a minor bump may break.

## [0.3.0] — 2026-09-24

### Breaking

- **Agent names are now `bq:<role>`** — `bq:maestro`, `bq:architect`, `bq:engineer`, `bq:tester`,
  `bq:reviewer`, `bq:researcher`, `bq:scribe` (was `bq:bq-<role>`). Agent files moved from
  `agents/bq-<role>.md` to `agents/<role>.md`. **Plugin users:** update any `bq:bq-<role>` reference
  in your own `CLAUDE.md`, project memory (`~/.ai/<project>/`), lessons, and any Claude Code
  settings that name agents (e.g. permission rules or a default agent). **Manual (`install.sh`)
  installs are unaffected** — they still install as `bq-<role>`. Upgrade an installed plugin with
  `/plugin marketplace update bq` then `/plugin update bq@bq` (shell:
  `claude plugin marketplace update bq && claude plugin update bq@bq`) and restart Claude Code.
- **`./install.sh install` now prefers the plugin CLI** (it used to copy files into `~/.claude/`).
  An existing manual install is kept and refreshed rather than doubled up with the plugin; switch
  with `./install.sh uninstall && ./install.sh plugin`. An already-installed plugin is upgraded in
  place (`marketplace update` + `plugin update`), and `reinstall` keeps the current mode.

### Fixed

- The Maestro and the `bq-team` skill now delegate with names that resolve under plugin scoping
  (previously bare `architect` / `bq-architect`, which never resolved as a plugin).
- Specialists can load skills: every agent's `tools:` includes `Skill`.
- `tools:` uses current names — `Agent` (formerly `Task`) on the Maestro only; `TodoWrite` removed.
- `/bq:init` and `/bq:onboard` find the memory templates via one lookup order in the `memory` skill
  (`${CLAUDE_PLUGIN_ROOT}`, plugin cache, manual install, generate).
- `/bq:mr`, `/bq:status` used Copilot `${input:…}` syntax; `/bq:onboard`, `/bq:refresh` dropped their
  argument — all now use `$ARGUMENTS`.

### Added

- `install.sh`: prefers the `claude plugin` CLI, falls back to a manual copy; `status`, `plugin`,
  `manual` subcommands. `plugin` refuses while a manual copy is installed; `uninstall` reports
  failure (no success line) if the plugin CLI couldn't remove the plugin.
- `install-copilot.sh`: installs the team into GitHub Copilot by transforming the canonical files
  (the Claude files stay the single source of truth; Copilot files are generated at install time,
  not maintained in parallel), including
  memory templates; `verify` catches Claude-only leftovers.
- `scripts/validate.py` + tests: manifest version sync, agent name/model/tools rules (only the
  Maestro may spawn), cross-references, marker balance; CI also runs shellcheck and `bash -n`
  on the installers.
- `LICENSE` (MIT) and this changelog.

### Hardened

- Installers: shellcheck-clean, bash 3.2 compatible, manifest deletions restricted to bq-owned paths
  (symlinks unlinked, never followed), `status` no longer aborts silently, cross-platform Copilot
  prompts directory.

## [0.2.0]

- Claude Code plugin release (repackaged from a GitHub Copilot extension as a native Claude Code plugin):
  Maestro + six specialists, `/bq:*` commands, method skills, `~/.ai/<project>/` memory.

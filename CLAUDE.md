# Editing the bq plugin

This repo **is** the Claude Code plugin — the files are native plugin components, no build step.
Edit them directly; what you see is what installs.

## Layout

```
.claude-plugin/plugin.json      plugin manifest (name: bq)
.claude-plugin/marketplace.json marketplace listing for /plugin install
agents/<name>.md                the Maestro + six specialists (subagents)
commands/<name>.md              the /bq:<name> slash commands
skills/<name>/SKILL.md          method skills (loaded on demand by description)
hooks/                          SessionStart hooks (plugin installs only): session_start.py (lessons
                                index + memory notices, read-only), checkpoint.py (background memory
                                checkpoint), shared helpers _bqhook.py / _bqmem.py; wired in hooks.json
scripts/                        validate.py (CI validator), bq_memory.py (memory history CLI),
                                skill_usage.py, and the stdlib unit tests (test_*.py)
templates/bq/                   starter content for a project's ~/.ai/<project>/ memory (init/onboard),
                                incl. knowledge/graph.md (written by /bq:onboard)
docs/architecture.md, USAGE.md  architecture overview and day-to-day usage
install.sh, install-copilot.sh  manual/plugin installer and the Copilot transform
```

## Conventions

- **A persona** → edit `agents/<name>.md`. Frontmatter: `name` (= filename), `description`,
  `tools`, `model`. Only `maestro` carries `Agent` (it spawns specialists); specialists don't, which
  keeps orchestration single-level.
- **A command** → edit `commands/<name>.md`. Invoked as `/bq:<name>`. Use `$ARGUMENTS` for input.
  The body opens with "You are the Maestro" so it runs in-character in the main session.
- **A method skill** → edit `skills/<name>/SKILL.md`. Keep `name` equal to the folder and the
  `description` keyword-rich ("Use when…") so Claude loads it on demand.
- **The team identity/roster/routing** → `skills/bq-team/SKILL.md`, mirrored in `agents/maestro.md`.
  It ships as an on-demand skill by choice; the SessionStart hook injects only the lessons index and
  memory notices, not the identity.
- **A hook** → stdlib `python3` only, quoted shell form in `hooks/hooks.json`, timeout ≤ 5 s, fail
  open, and a test in `scripts/test_hooks.py`. Only `hooks/_bqmem.py` may spawn processes (git).
- **Before committing** → `python3 scripts/validate.py` and
  `python3 -m unittest discover -s scripts -p 'test_*.py'` (CI runs both). Never point tests or
  `bq_memory.py` at the real `~/.ai` — use temp `AI_HOME` / `BQ_MEMORY_GIT_DIR` / `HOME`.

## Reloading during development

Install the local checkout as a marketplace and enable the plugin:

```
/plugin marketplace add /absolute/path/to/bq
/plugin install bq@bq
```

After editing, reload with `/reload-plugins` (or `/plugin`, or restart Claude Code). A local
marketplace loads bq **in place** from this checkout, so hook edits here reach open sessions — do
risky hook work in a separate git worktree.

## Memory (`~/.ai/<project>/`) is not the plugin

Project memory lives in the central `~/.ai/` store outside the repo (root `$AI_HOME` or `~/.ai`;
`<project>` = the project dir basename — a git worktree maps to its main checkout; cross-project
lessons in `~/.ai/shared/`). It's created by `/bq:init` or `/bq:onboard` in a target project — never
part of the plugin payload, never in this repo's git. An **opt-in** local history of the store lives
in a separate bare git repo outside both (`$BQ_MEMORY_GIT_DIR`; see the memory skill's Durability
and recovery section) — never pushed.

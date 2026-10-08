# bq Architecture

This repository is a native **Claude Code plugin**. The manifest in
[.claude-plugin/plugin.json](../.claude-plugin/plugin.json) declares the plugin; the marketplace
manifest in [.claude-plugin/marketplace.json](../.claude-plugin/marketplace.json) lets it install via
`/plugin`. There is no build step — the files are the plugin.

## What the plugin contains

- `agents/*.md` — subagents (the Maestro conductor + six specialists)
- `commands/*.md` — the `/bq:*` slash commands
- `skills/*/SKILL.md` — method skills loaded on demand by their `description`, including the
  `bq-team` overview skill; `skills/*/references/*.md` hold detail a SKILL.md points to and reads
  only when needed
- `hooks/` — `hooks.json` and two stdlib SessionStart hooks: `session_start.py` (lessons index and
  memory notices, see [Learning loop](#learning-loop)) and `checkpoint.py` (background memory
  checkpoint, see [Memory history](#memory-history)), with shared helpers `_bqhook.py` and
  `_bqmem.py`
- `scripts/bq_memory.py` — the memory history CLI; `scripts/skill_usage.py` — the read-only skill
  usage report; `scripts/render_review.py` — derives the HTML report from a review's markdown (see
  [Review reports](#review-reports))
- `templates/bq/` — starter content for a project's `~/.ai/<project>/` memory, used by `/bq:init` and
  `/bq:onboard` (`knowledge/graph.md` is written only by `/bq:onboard`)
- `.claude-plugin/plugin.json` — the plugin manifest
- `.claude-plugin/marketplace.json` — the marketplace listing

The marketplace entry's `source` is `"./"`, so the whole repo is copied into the plugin cache (a
local-folder marketplace copies even gitignored files). The plugin loader registers `agents/`,
`commands/`, `skills/`, `hooks/` and the manifests. Two other parts are used at runtime without being
registered: `templates/bq/`, read by `/bq:init` and `/bq:onboard`, and `scripts/bq_memory.py`,
`scripts/skill_usage.py` and `scripts/render_review.py`, which commands and skills run via
`${CLAUDE_PLUGIN_ROOT}/scripts/`. The rest — `install.sh` and `install-copilot.sh`,
`scripts/validate.py` and the tests, `docs/`, `CHANGELOG.md`, the root `CLAUDE.md`, and
`assets/logo/` (the logo: `mark.svg`, the banner `lockup.svg`, and the README's `icon.svg` /
`icon-dark.svg` for light / dark) —
ships but is inert (`claude plugin validate` warns that a root `CLAUDE.md` is not loaded as context).

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

Neither installer copies `hooks/` or `scripts/`: the SessionStart hooks exist only under a plugin
install, and the manual and Copilot installs run the memory CLI from a bq checkout. The manual install
keeps the `/bq:init`, `/bq:onboard` and `/bq:refresh` offer to turn on the history; the Copilot
install drops it (claude-only span with an empty alternative), and its `/bq-status` and
`/bq-improve` skip the index and the usage report. Likewise `/bq:review-mr` writes only the markdown
report there, with no HTML.

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
- **bq specialists first.** Every command names its specialists' agents inline (`bq:reviewer`, …),
  and `validate.py` fails a command that casts a role without naming its agent. A `general-purpose`
  or other plugin's agent is used only when no bq role fits, and the report says why. The method
  skills that mirror a command (debugging, research-method, critique, mr-review) are
  `user-invocable: false` and open with a redirect to that command's casting.
- **Single-level.** Specialists don't spawn peers; a specialist that hits work outside its lane names
  the right teammate and the main session re-routes (cap ~2 hops). Orchestration is command-driven by
  design, not forced by the platform (Claude Code lets subagents nest; plugin-shipped agents only lose
  `hooks`, `mcpServers` and `permissionMode`). Single-level holds because each specialist's explicit
  `tools:` list omits `Agent`, so only the Maestro (`bq:maestro`) can spawn; it also carries a fallback
  (do the smallest correct thing, or point to the matching command) for when `Agent` is unavailable.
- Lane discipline (e.g. the reviewer critiques, it doesn't rewrite code) is a convention backed by
  version control, not a hard permission.

## Always-on identity

The team identity, roster, routing, and standing rules ship as the on-demand
`skills/bq-team/SKILL.md`, which `agents/maestro.md` loads (rather than duplicating), so there is one
home for the conventions. Load the `bq-team` skill (or talk to the Maestro, `bq:maestro`) to bring
the conventions into context. The plugin's SessionStart hook (below) injects lessons and memory
notices, not the identity. The Copilot install writes the same skill as an always-on `bq-team.instructions.md`
(`applyTo: '**'`).

## Learning loop

Lessons are applied, checked, and reviewed (the full rules live in the `feedback-loop` skill):

- **Lessons in force.** `/bq:build`, `/bq:debug` and `/bq:ship` select at most 3 relevant Active
  lessons at Step 0; every specialist brief carries them.
- **Reviewer-graded Log.** The reviewer grades each `Applied | Missed | Contradicted | n/a` with
  evidence from the diff or a test; the Maestro appends those verdicts to the lesson's `## Log`
  (capped per run). Only reviewer verdicts, plus a miss the user confirms, become Log lines.
- **End-of-run reflection.** On a trigger (user correction, recurring fix round, hard stop,
  untrustworthy verification) a run offers at most one lesson and ends with one `Learning:` verdict
  line; nothing becomes Active without the user's yes.
- **Retro and status.** `/bq:retro` triages `Proposed` lessons and acts on `Missed`/`Contradicted`
  lines since each lesson's `Last reviewed`; `/bq:status` shows a Learning line when non-zero.
- **SessionStart lessons hook** (`hooks/hooks.json` →
  `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"`, 5 s timeout). In a project with
  `${AI_HOME:-~/.ai}/<project>/`, it emits `additionalContext`: a "Lessons in force" index (≤8
  entries, ≤3,200 chars, framed as quoted data) and one standing line telling the model to reflect
  once after a user correction. The model judges what a correction is. It also appends the
  `bq memory:` notices ([Memory history](#memory-history)); a stamp mismatch replaces the index. It
  reads `~/.ai` and the history dir and writes nothing, is silent without bq memory or notices, needs
  `python3` on PATH, and fails open (always exit 0). Plugin install only: under the manual and
  Copilot installs the `feedback-loop` skill carries the same behavior on demand.

## Memory history

An opt-in local git history of the whole `~/.ai` store (ADR 0011). The operator runbook — commands,
notices, recovery, purging a secret — lives in the memory skill's
[`references/durability.md`](../skills/memory/references/durability.md), summarized in its
[Durability and recovery](../skills/memory/SKILL.md#durability-and-recovery) section; this is the shape.

- **Repo.** A bare repo at `$BQ_MEMORY_GIT_DIR` (default
  `~/Library/Application Support/bq/ai-history.git` on macOS,
  `${XDG_DATA_HOME:-~/.local/share}/bq/ai-history.git` elsewhere), mode 0700, with `$AI_HOME` as its
  work tree. No remote; never pushed. Ignore patterns (secrets, OS junk, restore extracts, symlinked
  entries) live in `<history>/info/exclude`, so nothing is written into the store. Every git call
  passes `--git-dir`/`--work-tree`, a fixed `bq <bq@localhost>` identity, and overrides that bypass
  the user's global config (signing, hooks, `core.excludesFile`, `core.attributesFile`), with a
  timeout.
- **Opt-in.** `scripts/bq_memory.py init` then `checkpoint`, run on the user's yes (offered by
  `/bq:init`, `/bq:onboard`, `/bq:refresh`). Without the repo, the checkpoint hook does nothing and no
  history notices appear.
- **Checkpoint hook** (`hooks/checkpoint.py`, the second SessionStart hook, `async: true`, 5 s timeout).
  A no-op until the history has a commit — it never makes the first one. It takes a non-blocking
  flock on `<history>/bq-checkpoint.lock`, forks, and the child `setsid()`s and commits, so neither
  a CLI exit nor the hook timeout kills git mid-commit, and a concurrent checkpoint skips. It prints
  nothing; a failure goes to `<history>/bq-last-error`, cleared on success. It writes only under
  `<history>/`. Its unreadable-file handling (`git add --ignore-errors`) commits the rest and
  records the skipped paths.
- **Notices** (added by `session_start.py` after the lessons are built, under one git deadline; on a
  timeout the check is skipped): folders in history but missing on disk, deletions recorded in the
  last 7 days and still missing (each with its restore command), `*.lock` files in the history older
  than 2 minutes (reported, never removed), the last error, and a `<history>/bq-notice` younger
  than 7 days (a nested git repo, stored only as a gitlink); a history with no commit yet gets a
  run-`checkpoint` line instead of the git check. They also appear in a project with no
  memory folder, since that folder may be the deleted one.
- **Restore** extracts from history, never with `git checkout` onto a partly present folder: in
  place only into a missing folder, else beside it as `<dir>.restored-<rev>/`, or over it with
  `--force` after checkpointing the current state. It refuses a symlinked or non-directory target.
- **Identity.** `_bqhook.py` follows a worktree's `.git` file through `gitdir` and `commondir` to the
  main checkout's name. `bq_memory.py stamp` writes `<mem>/.identity` (roots and remotes, remotes
  stripped of credentials and query strings); when it matches neither, the lessons hook prints one
  mismatch line instead of the index. No central registry: the folder name stays the key, as ad hoc
  writers expect.
- **Index.** `bq_memory.py index [project]` prints a deterministic memory index to stdout, open loops
  first; `/bq:status` starts from it. No generated file.
- **Validator exemption.** `validate.py` warns on process imports in hook scripts, with one named
  exemption: `subprocess` in `hooks/_bqmem.py`.
- **Limits.** Protection starts at the first checkpoint; empty folders aren't restored; a rename
  looks like a deletion; the history is one copy on the same disk (use Time Machine as well).

## Review reports

`/bq:review-mr` never touches the user's checkout. It fetches the MR head and the target into
private `refs/bq-review/<key>/` refs, reviews in a locked worktree at
`<repo-parent>/.bq-review/<project>/<key>` (kept and moved on a re-review; `/bq:review-mr cleanup`
removes it), and diffs against the fetched target rather than the local, possibly stale one
(`skills/mr-review/references/isolated-checkout.md`). On Claude Code the specialists run in the
background, so the session stays free while the review runs.

`/bq:review-mr` records its review as `~/.ai/<project>/reviews/{slug}.md`, in the card format defined
by the mr-review skill's `references/report-format.md` (tone rules in `references/comment-style.md`).
Each finding carries a severity (critical, important, minor, nit; "blocking" is derived from it), a
confidence, and an anchor. A finding may include a "Proposed patch (not posted)"; it becomes
GitLab/GitHub suggestion syntax only if the user explicitly asks to post those named findings.

On plugin installs only, the Maestro then runs `scripts/render_review.py` to derive a self-contained
`{slug}.html` beside the markdown, best effort. The markdown is the record; the HTML is a view of it.
The page has no JavaScript, escapes all review text, sets a CSP, and uses a built-in
stylesheet (light, dark and print). Content the parser can't read shows as a visible banner rather than being dropped. The
manual and Copilot installs don't copy `scripts/`, so they keep the markdown only.

## Skill fitness (report only)

- `validate.py` fails when a skill reference or command script path it mentions doesn't exist.
- `validate.py` warns, never fails, on skill descriptions without a "Use when" clause, a quoted
  trigger phrase shared by two skills, a `/bq:<name>` that doesn't exist, and a skill over its word
  ceiling.
- `scripts/skill_usage.py` reads `skillUsage` from `~/.claude.json` (undocumented; one line and exit
  0 when missing or unrecognized) and prints bq skills with uses ("total since install") and last
  use. `/bq:improve` shows never-used skills as retire candidates and never drafts a deletion.

## Source of truth

- The repo files are the plugin source of truth.
- Project memory lives in the central `~/.ai/<project>/` store (root `$AI_HOME` or `~/.ai`;
  `<project>` = the project dir basename), with cross-project lessons in `~/.ai/shared/`. It lives
  outside the repo — not the plugin, never in the project's git. Its optional history is a separate
  local git repo, outside both (see [Memory history](#memory-history)).
- `README.md` explains the public layout at a high level and links back here.

## Operating rules

- Keep the architecture lean and direct-editable.
- Keep `plugin.json` / `marketplace.json` aligned with the payload files (the validator checks the
  versions match).
- Keep the tracked doc, README, and `CLAUDE.md` wording aligned when the architecture changes.
- Plugin edits drafted from lessons go only through `/bq:improve`: drafted in a scratch worktree,
  validated, applied on explicit approval. Its proposal ledger lives in memory
  (`~/.ai/shared/bq-proposals/`), never in the repo.
- Run `python3 scripts/validate.py` before committing; see the README's
  [Contributing / validating](../README.md#contributing--validating).

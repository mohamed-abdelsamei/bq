# Changelog

All notable changes to the `bq` plugin. Versions follow [SemVer](https://semver.org/); while
`0.x`, a minor bump may break.

## [0.8.0] — 2026-10-01

### Changed

- **Skills reviewed against skill-creator guidance and trimmed.** Rules now have one owner, and
  rarely needed detail moved to `references/` files read on demand:
  - mr-review 2497 → 1758 words (`references/deep-checks.md`: drift and re-review loop, orphan
    sweep, check-then-act, failure scope).
  - memory 2379 → 1384 (`references/durability.md`, `references/templates.md`, synced with
    `templates/bq/`, which restores the ADR *Deciders* field).
  - plugin-promotion 1744 → 1550 (`references/diff-checks.md`, `references/proposal-template.md`);
    now `user-invocable: false`.
- **Narrower, trigger-rich descriptions** for mr-review, memory, decision-and-spec, feedback-loop,
  research-method, codebase-onboarding and plugin-promotion.
- Commands say "Load the **feedback-loop** skill" at lesson selection and close-out, instead of
  only citing it.

### Fixed

- mr-review told a read-only specialist to write to `reviews/`; the Maestro records it now.
- `/bq:research` pointed at a report structure that didn't exist; it now uses
  `research/research-template.md` and has a trace-the-real-flow step.
- The decision lifecycle lives only in the memory skill. decision-and-spec had dropped `Verified`.
- Redirect blocks on debugging, research-method and critique defer to whichever command already
  cast the work; research-method lets a one-fact lookup be answered directly, debugging never skips
  the tester.
- critique and mr-review: the Maestro records the review; read-only specialists return findings.
- `Verified` is a real decision status with a setter; the research template gains Recommendation and
  Open questions.
- Duplicated rules removed across bq-team/maestro, brainstorm/facilitation, improve/plugin-promotion
  and feedback-loop.

## [0.7.0] — 2026-10-01

### Fixed

- **bq runs use bq specialists, not `general-purpose` agents.** Every command now names its
  specialists' agents inline (`bq:reviewer`, …) and says bq specialists come first. `validate.py`
  fails a command that casts a role without naming `bq:<role>`. The same agent-priority rule is in
  the bq-team skill and the Maestro. `/bq:review-mr` now spawns the reviewer, architect, and tester
  in parallel (the architect used to be cast twice), each with a read-only brief and a stated return
  shape.

### Changed

- **debugging, research-method, critique, and mr-review are hidden from the `/` menu**
  (`user-invocable: false`), so `/bq:mr-review` can no longer be mistaken for `/bq:review-mr`. The
  model still loads them on demand. If one loads in the main session, it points to its command's
  casting. The Copilot installer drops the key.

## [0.6.0] — 2026-09-27

### Added

- **Memory history (opt-in)** — a local git history of the whole `~/.ai` store, kept outside it so
  it survives the folder being deleted (ADR 0011).
  - **Where.** A bare repo at `$BQ_MEMORY_GIT_DIR`, default
    `~/Library/Application Support/bq/ai-history.git` (macOS) or
    `${XDG_DATA_HOME:-~/.local/share}/bq/ai-history.git`, mode 0700, with `$AI_HOME` as its work
    tree. No remote; never pushed. Ignore patterns (secrets, OS junk) live in `<history>/info/exclude`,
    not in the store. Commits use a fixed `bq <bq@localhost>` identity and bypass the user's global
    git config (signing, hooks, excludes, attributes); every git call has a timeout.
  - **`scripts/bq_memory.py`** (stdlib, logic in `hooks/_bqmem.py`): `init`, `checkpoint`, `status`,
    `log [dir] [-n N]`, `restore <dir> [--rev R] [--force]`, `stamp`, `index [project]`. `init`
    refuses when `$AI_HOME` is inside another git work tree and skips symlinked entries.
  - **Restore never destroys newer work.** A missing folder is restored in place; a present one is
    extracted beside it to `<dir>.restored-<rev>/`; `--force` overwrites only after checkpointing the
    current state and prints the undo command. A symlinked or non-directory target is refused, even
    with `--force`.
  - **Background checkpoint hook** (`hooks/checkpoint.py`, a second SessionStart hook with
    `async: true`), plugin install only. It runs at each session start, takes a non-blocking lock,
    and detaches (fork + `setsid`) so a CLI exit or hook timeout can't kill git mid-commit; a
    concurrent checkpoint skips. It never makes the first commit: `init` and the first `checkpoint`
    run from the CLI on the user's yes. A failure is written to `<history>/bq-last-error` (best
    effort). Unreadable files are skipped, the rest committed.
  - **`bq memory:` notices at session start** (plugin install): a project folder missing, or deleted
    in the last 7 days, with its restore command; a git lock in the history older than 2 minutes
    (reported, never removed); the last checkpoint error; a nested git repo in the store (only its
    gitlink is kept); a history with no checkpoint yet. `status` shows the same.
  - `/bq:init`, `/bq:onboard` and `/bq:refresh` offer the history once and run it only on the user's
    yes (Claude Code only; the Copilot build drops the offer). The memory skill gains a
    *Durability and recovery* runbook, including how to purge a secret from history.
- **Identity stamp.** `bq_memory.py stamp` writes `<mem>/.identity` (repo roots and remotes, remotes
  stripped of credentials and query strings); it is restored with its folder. When a stamp names
  neither this repo's root nor any of its remotes, the lessons hook prints one mismatch line and
  injects no lessons.
- **Memory index.** `bq_memory.py index` prints a deterministic, read-only index to stdout (open
  loops first); `/bq:status` starts from it under Claude Code.
- **Knowledge map.** `/bq:onboard` has the architect write `knowledge/graph.md` (at most ~80 lines,
  `Verified at: <sha>`, links into `docs/`), from the new template `templates/bq/knowledge/graph.md`.
- **Skill fitness, report only.** `validate.py` warns on skill descriptions without a "Use when"
  clause, quoted trigger phrases shared by two skills, `/bq:` commands that don't exist, and skills
  over a word ceiling (2,500 by default). `scripts/skill_usage.py` reads `skillUsage` from
  `~/.claude.json` (totals since install; fails soft), and `/bq:improve` lists never-used skills as
  retire candidates without drafting a deletion.

### Changed

- `hooks/hooks.json` runs two SessionStart hooks. The lessons hook still writes nothing; it also
  reads the history dir for notices, and emits them even in a project with no memory folder. The
  checkpoint hook writes only under the history dir, never into `~/.ai`.
- `validate.py` allows `subprocess` in exactly one hook file, `hooks/_bqmem.py`, accepts a boolean
  `async` on hook entries, and requires the `knowledge/graph.md` template.
- `/bq:ship` treats `bq_memory.py` `init`, the first checkpoint, `restore` or `stamp` on the real
  store as a hard stop.
- The Maestro and the `bq-team` skill put the project memory path in every specialist brief.
- `install-copilot.sh` keeps a paragraph break where an empty Copilot alternative drops a span.
- README, architecture and USAGE describe the history, restore, identity, the index, the knowledge
  map and the skill report, and which installs get the hooks (plugin only) and the scripts (plugin,
  or a bq checkout).

### Fixed

- **Git worktrees got no lessons** (0.5.0). The hooks keyed memory by the worktree's folder name;
  they now follow the `.git` file through `gitdir` and `commondir` to the main checkout's name.

## [0.5.0] — 2026-09-25

### Added

- **Closed-loop learning.** Lessons now get applied, checked, and reviewed, not just written.
  - **Lessons in force.** At Step 0 of `/bq:build`, `/bq:debug` and `/bq:ship`, the Maestro picks
    at most 3 relevant Active lessons (the chain's roles plus the task's keywords; tie-break:
    task-specific first, then most recent) and every specialist brief carries them.
  - **A reviewer-graded `## Log`.** The reviewer grades each lesson in force `Applied | Missed |
    Contradicted | n/a`, citing the diff or a test (no violation seen means `n/a`). The Maestro
    appends those verdicts to the lesson's `## Log`: at most 3 per run, Missed and Contradicted
    first, and a fix round never turns a first-pass Missed into Applied. `/bq:ship` logs only
    Missed/Contradicted per task, under a cap of 3 for the whole run. Only reviewer verdicts are
    logged, plus a `correction · Missed` line when the user catches a missed lesson that no
    reviewer flagged, and only once the user confirms it. `/bq:debug` has no reviewer, so it logs
    nothing. Log lines never count as promotion evidence.
  - **End-of-run reflection** (`feedback-loop` skill). Triggers: a user correction that would
    change behavior in other tasks, a blocking fix round likely to recur, a hard stop, or
    verification that couldn't be trusted. Each run checks for duplicates against existing
    lessons, offers at most one new lesson (a yes/no ask in build and debug; `Proposed` at
    `/bq:ship` Step 4), and ends with exactly one `Learning:` verdict line (`Learning: pending — …`
    while the ask is open). A `Learning:` line is never a Log line.
  - **`Last reviewed`**, a new lesson field. Any retro decision on a lesson sets it. Missed and
    Contradicted lines are counted from that date on (if it's missing, from Date).
  - **`/bq:retro` triage.** A bare `/bq:retro` first offers to triage `Proposed` lessons (Active,
    or Dropped with a reason, on the user's word), then moves on to housekeeping. 2+ Missed lines
    lead to a recommendation to make Future behavior checkable or add it to the reviewer's checklist
    (never promotion). Any Contradicted line leads to a recommendation to supersede or drop.
  - **`/bq:status` Learning line.** At most 2 lines, shown only when non-zero: Proposed lessons
    (count and oldest age), and lessons with Missed/Contradicted since Last reviewed.
- **SessionStart hook** (`hooks/hooks.json`, `hooks/session_start.py`), plugin install only.
  - **What it does.** In a project that has `~/.ai/<project>/` memory, it injects a "Lessons in
    force" index framed as quoted data: this project's and shared Active lessons, at most 8
    entries and 3,200 characters, with 2 slots kept for shared lessons. It adds a learning-status
    line, plus one standing line: after a user correction, reflect once and end with a `Learning:`
    line. The model decides what counts as a correction.
  - **What it doesn't do.** It is silent in projects with no bq memory. It reads `~/.ai` and writes
    nothing.
  - **How it runs.** Stdlib `python3` in quoted shell form, with a 5 s timeout. It fails open.
  - **Where it runs.** Manual and Copilot installs don't get the hook. There, the `feedback-loop`
    skill carries the same behavior on demand.
  - **Not shipped.** A regex correction detector (UserPromptSubmit/Stop hooks) was built during this
    cycle and withdrawn before release, after scoring precision 0.56 / recall 0.17 on held-out
    prompts.
- `validate.py`:
  - checks that the lesson format (fields, Log line, states table) matches between the
    `feedback-loop` skill and the lesson template;
  - checks the shape of `hooks/hooks.json` (event, timeout ≤ 5 s, exact quoted `python3` command,
    script exists), and warns on network or process imports in hook scripts;
  - warns when the `feedback-loop` skill passes 1,900 words;
  - `scripts/test_hooks.py` pipes sample JSON through the hook.

### Changed

- The docs no longer say a plugin can't inject context. The hook does, for lessons. The team
  identity stays the on-demand `bq-team` skill.

## [0.4.0] — 2026-09-25

### Added

- **`/bq:improve`** — turns proven lessons into approved edits to bq itself. It mines lessons across
  all projects, has the reviewer gate each group on evidence (general bq behavior only, at least two
  independent contexts, no conflicts, no previously rejected slug; at most 3 candidates per run),
  has the engineer draft the smallest edit in a scratch `git worktree` and validate it
  (`validate.py`, plus `claude plugin validate …/plugin.json` with no warning new versus the base
  commit), mechanically checks the diff (target files only, no new or deleted files, at most 5 net
  added and 15 changed lines), checks that nothing identifying reaches the patch or commit message,
  and applies a patch only on the user's own explicit yes — never committing without their word.
  Proposals are kept in a ledger in memory (`~/.ai/shared/bq-proposals/`), not the repo. Outside a
  bq checkout it only lists candidates, read-only. It cannot edit its own mechanism (`improve.md`,
  `feedback-loop`, `plugin-promotion`, `.claude-plugin/`, `hooks/`, and its reviewer:
  `agents/reviewer.md`, `critique`, `mr-review`), frontmatter, any wording about
  approval, committing, sanitization, evidence, gating, or validation, or anything whose effect
  weakens a check, review, test, stop, approval step, or scope rule.
- **`plugin-promotion` skill** — the rules `/bq:improve` applies: target classes, evidence gate,
  growth cap and diff rules, sanitization, self-edit ban, validation, consent, proposal states,
  and Stale (committed changes only; a user's uncommitted edits defer it).
- `/bq:retro` can stamp a lesson `Promoted → …` from an Accepted proposal, mark it `Superseded by …`,
  or prune an Active or Shared lesson to `Dropped — …` — each offered only when it applies, and only
  on the user's word.
- `validate.py` fails if the lesson `- **Status:**` line differs between the `feedback-loop` skill
  and the lesson template, so the vocabulary can't drift again.

### Changed

- **One lesson vocabulary.** *Sharing* means copying a lesson into `~/.ai/shared/lessons/`;
  *promotion* means an approved edit to plugin files. Lesson states are now `Proposed | Active |
  Shared → … | Promoted → … | Superseded by … | Dropped — …` across the `feedback-loop` skill, the
  lesson template and README, `/bq:retro`, and USAGE, with state tables naming who sets each state.
  The old `Promotion-nominated` state is replaced by an optional `Nominated: yes — {why}` field set by
  the human. The `memory` skill documents the proposal ledger.

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

<p align="center"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo/icon-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/logo/icon.svg">
  <img src="assets/logo/icon-dark.svg" alt="bq logo: a red b and a teal q arguing nose to nose" width="128">
</picture></p>

# bq

A reusable **team of AI agents** for your work and pet projects, packaged as a native **Claude Code
plugin**. Six specialists — each with a distinct **personality and point of view** — run a real
feature lifecycle: **brainstorm a requirement from multiple angles, agree on a solution, split it
into tasks, then build, test, review, and document it.** A master conductor (the **Maestro**) frames
the work, convenes the team, routes requests, and keeps the rationale. Every project gets its own
**memory folder** in the central `~/.ai/` store (outside the repo) so discussions and decisions are
never lost between sessions.

Talk to the **maestro** subagent and let it delegate, or address **any specialist directly** — and
if a request isn't theirs, they hand it to the right teammate. Or just run a `/bq:*` command.

> **New here?** Read the [Usage guide](docs/USAGE.md) — the mental model, setup, which command when,
> and a feature walked through start to finish.

## The team

| Agent | Persona | Bias (kept honest by the team) | Owns |
|-------|---------|-------------------------------|------|
| **maestro** | Calm facilitator (the conductor subagent) | Forces a decision | Framing, routing, brainstorm rounds, synthesis, memory |
| **architect** — **Sol** | Systems thinker | Leans to structure; can over-engineer | Analysis, design, task breakdown |
| **engineer** — **Max** | Pragmatist | Ships fast; can under-design | Implementation, debugging, spikes |
| **tester** — **Vera** | The breaker | Thorough; can over-test | Test plans, verification, edge cases |
| **reviewer** — **Cass** | Constructive red-teamer | Risk-focused; can slow things down | Code review + decision critique |
| **researcher** — **Ada** | Evidence-driven scholar | Rigorous; can rabbit-hole | Options, prior art, sourced findings |
| **scribe** — **Quill** | Clear voice | Thorough; can over-document | Docs + recording the team's work |

The biases are deliberate. When Sol wants structure and Max wants to ship, that tension is the
point — a brainstorm with six agreeable agents is just one opinion repeated.

**The team challenges you, too.** By design, no agent is a yes-man: they push back on weak reasoning
— yours included — before acting on it. Everything they record is written for *you* to read and
understand later (plain language, terms defined, the *why* always explained), and you can interrogate
any of it: ask what a decision means with `/bq:ask`, or have your own reasoning grilled one sharp
question at a time with `/bq:grill`.

## Install

bq installs as a Claude Code plugin from a marketplace — the repo is public on GitHub
([mohamed-abdelsamei/bq](https://github.com/mohamed-abdelsamei/bq)), so add it directly:

```
/plugin marketplace add mohamed-abdelsamei/bq
/plugin install bq@bq
```

To install a local checkout, add its path as a marketplace first:

```
/plugin marketplace add /absolute/path/to/bq
/plugin install bq@bq
```

Then reload with `/plugin` (or restart Claude Code). After installing, run a `/bq:*` command, or
select the **maestro** subagent (or a specialist) and ask in plain language.

To upgrade an installed plugin later, refresh the marketplace, then update the plugin, and restart
Claude Code:

```
/plugin marketplace update bq
/plugin update bq@bq
```

(From a shell: `claude plugin marketplace update bq && claude plugin update bq@bq`.)

> **Upgrading from 0.2?** Run the two update commands above. Plugin agent names dropped their
> doubled prefix and are now `bq:<role>` (e.g. `bq:engineer`) — see the [CHANGELOG](CHANGELOG.md)
> for what to update.

### Install script (plugin CLI or manual copy)

`install.sh` wraps both paths and keeps you on one of them. `install` uses the `claude plugin` CLI
when it's on your PATH (upgrading the plugin with `marketplace update` + `plugin update` if it's
already installed) and falls back to a manual copy into `~/.claude/` when the CLI is missing or a
fresh plugin install fails (e.g. blocked by policy). If a manual copy is already installed, `install`
refreshes that copy instead of adding the plugin on top; switch with
`./install.sh uninstall && ./install.sh plugin`.

```
./install.sh install       # refresh a manual copy; else install/upgrade the plugin; else manual copy
./install.sh plugin        # plugin CLI only (refuses while a manual copy is installed)
./install.sh manual        # force the manual copy (or: BQ_MANUAL=1 ./install.sh install)
./install.sh status        # what's installed (plugin + manual)
./install.sh uninstall     # remove the plugin and/or the manual copy
./install.sh reinstall     # uninstall then install again in the same mode (pick up edits)
./install.sh clean-legacy  # remove only an old flat/mis-nested manual install
```

The manual copy uses a clean, collision-proof `bq` namespace:

| Component | Installed to | Result |
|-----------|--------------|--------|
| commands  | `~/.claude/commands/bq/`  | invoked as `/bq:<name>` |
| skills    | `~/.claude/skills/bq-*/`  | skill ids `bq-<name>` |
| agents    | `~/.claude/agents/bq/`    | agents `bq-maestro`, `bq-architect`, … (a plugin install names them `bq:<role>`) |
| templates | `~/.claude/bq-templates/` | scaffolding for `/bq:init` and `/bq:onboard` |

The manual copy skips `hooks/` and `scripts/`, so there's no SessionStart lessons index (see
[Learning loop](#learning-loop)) and no background memory checkpoint (see
[Memory history](#memory-history-opt-in)); the `feedback-loop` skill carries the lessons behavior
on demand, and the memory CLI runs from a bq checkout.

It tracks what it wrote in `~/.claude/.bq-install-manifest`, so `uninstall` removes exactly those
files. Target another dir with `CLAUDE_CONFIG_DIR=/path ./install.sh manual`. Restart Claude Code
afterward to pick up the changes.

> **Always-on note:** the plugin install has two SessionStart hooks. One injects the lessons index,
> a reflection reminder and any `bq memory:` notices (see [Learning loop](#learning-loop) and
> [Memory history](#memory-history-opt-in)); the other checkpoints memory in the background, only if
> you opted in to the history. The team identity, roster, and routing
> ship as the on-demand `bq-team` skill, which the Maestro loads — load that skill or talk to the
> Maestro (`bq:maestro`) to bring the conventions into context.

### Install into GitHub Copilot (VS Code)

The same team runs in GitHub Copilot. Copilot has no plugin marketplace, so the bundled script
transforms the canonical Claude files into Copilot customizations and installs them into your user
profile:

```
./install-copilot.sh install      # transform + install into your Copilot profile (then verifies)
./install-copilot.sh status       # show what's installed
./install-copilot.sh verify       # check installed files for leftover Claude-only wording
./install-copilot.sh uninstall    # remove everything the script installed
./install-copilot.sh reinstall    # uninstall then install (pick up edits)
```

| Component | Installed to | Result |
|-----------|--------------|--------|
| commands  | `<prompts>/bq-*.prompt.md` | invoked as `/bq-<name>` (dash — Copilot has no `:` namespacing) |
| agents    | `<prompts>/bq-*.agent.md`  | custom agents `bq-maestro`, `bq-architect`, … |
| skills    | `~/.copilot/skills/bq-*/`   | skill ids `bq-<name>` (except `bq-team`, which becomes the identity file) |
| identity  | `<prompts>/bq-team.instructions.md` | always-on (`applyTo: '**'`) roster + routing |
| templates | `~/.copilot/bq-templates/`  | scaffolding for `/bq-init` and `/bq-onboard` |

`<prompts>` is your VS Code User prompts folder — by default
`~/Library/Application Support/Code/User/prompts` (macOS), `${XDG_CONFIG_HOME:-~/.config}/Code/User/prompts`
(Linux), or `$APPDATA/Code/User/prompts` (Windows, Git Bash/MSYS). The transform rewrites
`$ARGUMENTS` → `${input:args}`, maps Claude tool names to Copilot aliases (`read`, `search`, `edit`,
`execute`, `web`, `agent`), and restricts subagent delegation to the Maestro. It tracks what it wrote
in `~/.copilot/.bq-copilot-install-manifest`, so `uninstall` removes exactly those files. Override
locations with `COPILOT_PROMPTS_DIR=/path` and `COPILOT_SKILLS_DIR=/path` (templates and the
manifest sit next to the skills folder). Reload VS Code
(**Developer: Reload Window**) afterward, then type `/` in Copilot Chat to run `/bq-build`,
`/bq-brainstorm`, `/bq-status`, ….

> Unlike the Claude plugin, the Copilot install carries the `bq-team` identity always-on: it is
> installed as a user-level `*.instructions.md` with `applyTo: '**'`, so the roster and routing are
> in context everywhere without loading a skill. It installs no hooks and no `scripts/`, so there's
> no SessionStart lessons index and no background memory checkpoint; the `feedback-loop` skill
> carries the lessons behavior on demand, and the memory CLI runs from a bq checkout.

## Commands

| What you want | Command |
|---------------|---------|
| Start the team on a **new** project | `/bq:init` |
| Onboard the team to an **existing** project | `/bq:onboard` |
| Refresh project instruction/context understanding | `/bq:refresh` |
| Debate a topic from every angle and decide | `/bq:brainstorm <topic>` |
| Turn a feature/requirement into a plan + tasks | `/bq:plan <feature>` |
| Build a task: implement → test → review | `/bq:build <task>` |
| Fix a bug: reproduce → root cause → smallest fix → regression test | `/bq:debug <bug>` |
| Investigate how something works today and document it | `/bq:research <feature/question>` |
| Learn from completed work, corrections, and repeated failures | `/bq:retro <task/session/correction>` |
| Turn proven lessons into approved edits to bq itself (run inside the bq checkout) | `/bq:improve [focus]` |
| Ship the whole backlog autonomously (plan → build → commit per task) | `/bq:ship [feature]` |
| Review code, or stress-test a decision | `/bq:review <target>` |
| Open a merge/pull request from a shipped branch | `/bq:mr [branch]` |
| Review a merge/pull request — code **and** business | `/bq:review-mr <MR ref>` |
| Ask about any decision, term, or topic | `/bq:ask <question>` |
| Be interrogated on your own reasoning | `/bq:grill <idea>` |
| Drop an abandoned plan: archive its requirement, decision & tasks | `/bq:drop <feature>` |
| See the state of play — a read-only rollup of `~/.ai/<project>/` memory | `/bq:status [area]` |

Or skip the commands and just talk: pick **maestro** (or a specialist) and ask in plain language —
the Maestro classifies anything you hand it and routes it to the right lane.

> In **GitHub Copilot** these commands use a dash instead of a colon — `/bq-build`, `/bq-status`,
> `/bq-brainstorm`, … — because Copilot has no `:` namespacing.

## How it works

The **Maestro** is the conductor: it frames the problem, brings in the right specialists, runs the
debate, synthesizes a decision, and records it. The six specialists do the focused work.

**The marquee flow — `/bq:brainstorm`:**

1. The Maestro frames the question and picks who belongs at the table.
2. Those specialists give their views **independently** — each in character.
3. The Maestro surfaces the **agreements and the real tensions**.
4. A focused **rebuttal round**: the conflicting agents respond to each other.
5. The Maestro **synthesizes** a recommendation — which arguments won, which tradeoffs were accepted,
   what's still open.
6. The decision and discussion are written to project memory.

**Delegation.** Ask for anything. The Maestro classifies it and routes to the one right specialist —
or convenes the team if it's big. If a specialist gets something out of its lane, it names the right
teammate and the Maestro re-routes.

> **How orchestration works:** the `/bq:*` commands run in the main session (which holds the `Agent`
> tool) and **spawn each specialist as an isolated subagent** with a compact brief. Delegation is
> **explicit** — the specialist is named, never auto-picked from its description. Orchestration stays
> single-level: specialists don't spawn peers; one that hits work outside its lane names the right
> teammate and the main session re-routes.

### Bring the team onto your project (once)

- **New project** (little/no code) → `/bq:init` — a short interview, then it scaffolds memory.
- **Existing project** → `/bq:onboard` — the team scans and *understands* your codebase and any
  existing context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`, `context.md`, …)
  **without modifying them**, then builds its memory to complement them.
- **Refresh project instructions/context understanding** → `/bq:refresh` — re-read authoritative
  project rules and reconcile local `~/.ai/<project>/` assumptions after teammate/tooling changes.

## Project memory (`~/.ai/<project>/`)

`/bq:init` (new project) or `/bq:onboard` (existing project) creates the project's memory folder
in the central `~/.ai/` store — outside the repo, so it never enters git history. `<project>` is the
project directory's basename; the root is `$AI_HOME`, or `~/.ai` if unset. Lessons that generalize
across projects live in `~/.ai/shared/lessons/`.

```
~/.ai/<project>/
  charter.md       project principles + stack (read first, every session)
  discussions/     brainstorm summaries
  decisions/       ADR-style decision log
  requirements/    specs
  tasks/           task breakdowns + status
  research/        sourced findings
  reviews/         reviews + critiques
  knowledge/       graph.md — a short map of the codebase, written by /bq:onboard
  lessons/         reusable lessons from retrospectives and user corrections
  archive/         dropped plans, moved aside by /bq:drop
  .identity        optional stamp: the repo root and remotes this folder belongs to
```

### Learning loop

Lessons don't just get written — they get applied and checked:

- **Lessons in force.** `/bq:build`, `/bq:debug` and `/bq:ship` pick at most 3 relevant Active
  lessons and put them in every specialist's brief.
- **Reviewer-graded Log.** The reviewer marks each one `Applied | Missed | Contradicted | n/a`, citing
  the diff or a test, and the Maestro appends that verdict to the lesson's `## Log`. Only reviewer
  verdicts (and a miss you confirm) are logged — no one grades their own work.
- **End-of-run reflection.** After a user correction, a recurring fix round, a hard stop, or
  untrustworthy verification, the run offers at most one new lesson (a yes/no ask) and ends with one
  `Learning:` verdict line. Nothing becomes Active without your yes.
- **Triage and follow-up.** A bare `/bq:retro` triages `Proposed` lessons first; repeated `Missed`
  lines get a rewrite recommendation, a `Contradicted` one a supersede-or-drop recommendation.
  `/bq:status` shows a short Learning line when anything is pending.
- **SessionStart hook (plugin install only).** In a project with `~/.ai/<project>/` memory, the
  plugin's lessons hook injects a "Lessons in force" index (≤8 entries, about 800 tokens) and one
  standing line: when you correct the team, reflect once and end with a `Learning:` line. It reads
  `~/.ai` and writes nothing, stays silent without bq memory (apart from any `bq memory:` notices),
  needs `python3` on your PATH, and fails open. (The separate checkpoint hook, below, is the one that writes — to the external history
  only.) Manual and Copilot installs don't get either; the `feedback-loop` skill carries the lessons
  behavior on demand.

### Memory history (opt-in)

`~/.ai` is plain files: a stray `rm -rf` loses every loop that closed into it. bq can keep a local
git history of the whole store, **outside** it, so it survives the folder being deleted.

- **Where.** A bare git repo at `$BQ_MEMORY_GIT_DIR`, by default
  `~/Library/Application Support/bq/ai-history.git` (macOS) or
  `${XDG_DATA_HOME:-~/.local/share}/bq/ai-history.git` (elsewhere). Mode 0700, no remote, never
  pushed. Checkpoints write nothing into `~/.ai` (the ignore patterns live in the history repo).
- **Turning it on.** `/bq:init`, `/bq:onboard` and `/bq:refresh` offer it once and run it only on
  your yes. By hand: `python3 <bq>/scripts/bq_memory.py init`, then `checkpoint` for the first
  commit. Until that first commit exists, nothing is protected and the hooks do nothing for it.
- **Background checkpoints (plugin install only).** At each session start (startup, resume, clear,
  compact) a second SessionStart hook commits every change in the store from a detached background
  process, so closing the session can't cut a commit short. A session's writes are therefore
  captured at the *next* session start. It never makes the first commit, skips while another
  checkpoint runs, and bypasses your global git config (fixed `bq <bq@localhost>` identity, no
  signing, no git hooks). A failure is recorded (best effort) in `<history>/bq-last-error` and shown at the next session start.
- **Session-start notices (plugin install only).** One `bq memory:` line each, after the lessons,
  once the history exists (in any project): a project folder that is missing or was deleted in the
  last 7 days (with the exact restore command), a history lock older than 2 minutes (reported, never
  removed automatically), the last checkpoint error, and a nested git repo in the store (only its
  commit pointer is kept), or a history with no checkpoint yet. A stamp mismatch (below) needs no
  history.
- **Restore never destroys newer work.** `restore <dir>` puts a missing folder back in place. If the
  folder exists, it extracts the old version beside it as `<dir>.restored-<rev>/`; `--force`
  overwrites only after checkpointing the current state, then prints a diff summary and the undo
  command (files are added or overwritten, never deleted, so the undo isn't exact). It refuses a target
  that is a symlink or not a real folder, even with `--force`.
- **Other commands.** `status` (lock, last checkpoint and error, uncommitted changes, missing and
  recently deleted folders), `log [dir] [-n N]`, `stamp`, and `index [project]` — a read-only memory
  index, open loops first, which `/bq:status` reads first.
- **Where the CLI is.** Under a plugin install, `${CLAUDE_PLUGIN_ROOT}/scripts/bq_memory.py` (in the
  plugin cache). The manual and Copilot installers copy neither `scripts/` nor `hooks/`: run the CLI
  from a bq checkout, and run `checkpoint` yourself, since nothing runs it in the background.
  Copilot's `/bq-init`, `/bq-onboard` and `/bq-refresh` don't offer it.
- **Limits.** Protection starts at the first checkpoint: nothing older can be recovered, and a crash
  loses writes since the last checkpoint. Empty folders aren't restored (git doesn't track them), and
  a renamed folder looks like a deletion of the old name. The history is one copy on the same disk,
  so keep Time Machine or another backup as well. Anything written to memory is kept for good —
  a few secret file patterns (`*.env`, `*.pem`, `*.key`, SSH keys) are ignored, but don't write
  secrets to memory.

`init`, the first checkpoint, `restore` and `stamp` on your real store are hard stops: `/bq:ship`
never runs them on its own. The full runbook — each command, each notice and what to do about it,
and how to purge a secret from history — is the memory skill's
[Durability and recovery](skills/memory/SKILL.md#durability-and-recovery) section, with the
full runbook in [`references/durability.md`](skills/memory/references/durability.md).

**Identity.** Memory is keyed by the project folder's name. Git worktrees now resolve to the main
checkout's name (in 0.5 a worktree got no lessons). `stamp` writes `<mem>/.identity` — the repo root
and its remotes, with credentials stripped — and works without the history. Under a plugin install,
when the stamp names neither this repo's root nor any of its remotes, the hook prints one mismatch
line and injects no lessons, so two repos with the same folder name stop reading each other's.

**Knowledge map.** `/bq:onboard` also writes `knowledge/graph.md`: at most ~80 lines of components,
edges and entry points, headed `Verified at: <sha>`, linking into `docs/` rather than restating it.
Nothing keeps it fresh automatically.

Durable, polished docs (architecture overviews, guides) live in `docs/` — one home per artifact, no
duplicates. Conventions are documented in the bundled **memory** skill.

## Skills

The team carries shared *method* as skills, so the deep know-how lives in one place instead of being
copy-pasted into every persona. Claude loads each on demand when the task matches its `description`.
**debugging**, **research-method**, **critique**, and **mr-review** are hidden from the `/` menu
(`user-invocable: false`), because they are the specialists' method, not an entry point. Run
`/bq:debug`, `/bq:research`, `/bq:review`, or `/bq:review-mr` instead. If one of them loads in the main
session anyway, it points back to that command's casting.

| Skill | What it encodes |
|-------|-----------------|
| **bq-team** | The roster, routing, standing rules, and the loop-engineering principle — every unit of work opens, then closes or is dropped, leaving a trace (team overview) |
| **memory** | How the `~/.ai/<project>/` memory works, who writes where, and the durability-and-recovery runbook |
| **codebase-onboarding** | Understanding an unfamiliar repo without modifying it (powers `/bq:onboard`) |
| **decision-and-spec** | Testable requirements (given/when/then) and ADRs with real rationale |
| **research-method** | Sourcing, confidence rating, and citation discipline |
| **feedback-loop** | Capturing lessons, applying the ones in force, end-of-run reflection with a `Learning:` verdict, and sharing proven ones (powers `/bq:retro`) |
| **plugin-promotion** | The rules for turning proven lessons into approved plugin edits — evidence gate, sanitization, self-edit ban (powers `/bq:improve`) |
| **facilitation** | Running a debate that ends in a decision (steelman, surface assumptions) |
| **critique** | Red-teaming a decision/plan/idea — three lenses + a verdict (powers `/bq:review`, `/bq:grill`) |
| **debugging** | Fixing a bug without breaking what works — root cause, smallest fix, regression test |
| **mr-review** | Reviewing MRs/PRs/diffs on code and business axes, with a clear merge verdict |

**Skill fitness (report only).** `validate.py` warns on weak skill descriptions — no "Use when"
clause, a quoted trigger phrase shared by two skills, a `/bq:` command that doesn't exist, or a skill
over its word ceiling. `scripts/skill_usage.py` reads the undocumented `skillUsage` counts in
`~/.claude.json` (totals since install; it prints one line and exits 0 if the file is missing or in a
format it doesn't know), and `/bq:improve` lists never-used skills as **retire candidates** — it never
drafts a deletion. Copilot's `/bq-improve` skips it; otherwise `/bq:improve` runs it (on a manual install, from the
checkout).

## Layout

The repo **is** the plugin — the files are native Claude Code plugin components, no build step.

```
.claude-plugin/plugin.json      plugin manifest (name: bq)
.claude-plugin/marketplace.json marketplace listing for /plugin install
agents/                 <role>.md — the Maestro + six specialists (subagents)
commands/               *.md — the /bq:* commands
skills/                 <name>/SKILL.md — method skills loaded on demand (incl. the bq-team overview)
hooks/                  SessionStart hooks (plugin install only): hooks.json; session_start.py — lessons
                        index + memory notices; checkpoint.py — background checkpoint; _bqhook.py and
                        _bqmem.py — shared helpers (_bqmem.py runs git for the memory history)
templates/bq/           starting content for a project's ~/.ai/<project>/ memory (init/onboard),
                        incl. knowledge/graph.md for /bq:onboard
docs/                   architecture overview + usage guide
install.sh              Claude Code installer (plugin CLI or manual copy)
install-copilot.sh      GitHub Copilot installer (transforms the canonical files)
scripts/                bq_memory.py — memory history CLI; skill_usage.py — skill usage report;
                        render_review.py — HTML view of a review report; validate.py; tests
.github/workflows/      CI: validator, validator tests, shellcheck + bash -n of the installers
CLAUDE.md               contributor notes for editing the plugin
CHANGELOG.md, LICENSE   release notes; MIT license
```

See [docs/architecture.md](docs/architecture.md) for the full picture and
[CLAUDE.md](CLAUDE.md) for editing conventions.

## Contributing / validating

Edit the canonical files directly (conventions in [CLAUDE.md](CLAUDE.md)), then run what CI runs
([.github/workflows/validate.yml](.github/workflows/validate.yml)):

```
python3 scripts/validate.py                                   # manifests, frontmatter, tools, cross-refs, markers
python3 -m unittest discover -s scripts -p 'test_*.py'        # validator, hook, memory + usage tests
shellcheck install.sh install-copilot.sh                      # lint the installers
bash -n install.sh && bash -n install-copilot.sh              # syntax-check the installers
```

Also run locally (not in CI — it needs the `claude` CLI):

```
claude plugin validate .                                      # Claude Code's check of the marketplace manifest
claude plugin validate .claude-plugin/plugin.json             # ... and of the plugin manifest + payload
```

The plugin check warns that the root `CLAUDE.md` isn't loaded as context — expected, it's contributor
notes, not plugin content.

The validator is stdlib-only (Python 3.9+). Among other rules, it fails if any agent other than the
Maestro carries a delegation tool (`Agent`/`Task`), if a doc references an agent, skill, or command
that doesn't exist, or if claude-only markers are unbalanced.

**Claude-only prose.** Copilot output is generated from the Claude files, so wording that only makes
sense in Claude Code is wrapped in markers:
`<!-- claude-only -->A<!-- copilot: B --><!-- /claude-only -->`. Claude and the manual install keep
*A*; `install-copilot.sh` writes *B* (an empty *B* drops the span). A plain span with no `copilot:`
part is the plugin-vs-manual naming clause, rewritten to the `bq-<role>` form by both installers.
After changing one, run `./install-copilot.sh reinstall` — it verifies the installed copy and
catches leftovers.

## Design principles

- **Single-level orchestration.** One conductor (the Maestro) drives many specialists; specialists
  don't drive each other. This is enforced in config: only the Maestro (`bq:maestro`) carries the `Agent` tool, so only
  it can spawn a specialist. File-write lanes (e.g. the reviewer critiques, it doesn't rewrite code)
  are a convention backed by version control — a lane violation shows up in the diff.
- **Productive disagreement.** Personas carry deliberate, opposing biases so a brainstorm produces
  real tension, not consensus theater. The Maestro's job is to force a decision out of it.
- **Memory is the product.** Decisions and their rationale are written to the central
  `~/.ai/<project>/` store (outside the repo), in plain language, for a human to read later. A
  conclusion that isn't written down didn't happen.
- **Respect what's already there.** Onboarding reads existing context files (`CLAUDE.md`, `AGENTS.md`,
  `copilot-instructions.md`, …) and never modifies them — they're authoritative.
- **Native files, no build.** The repo files are the plugin you install — edit `agents/`,
  `commands/`, `skills/` directly. The plugin install uses the files as-is; both installers rewrite
  names and paths while copying (`install-copilot.sh` also converts them to Copilot's formats).

## Known limitations

- **Guardrails are instructional, not enforced.** Memory write-scoping and "stay in your lane" rules
  are prose the model follows, not hard permissions. Agents can do whatever their granted tools allow.
- **The hook injects lessons, not the team identity.** The SessionStart hook's index and
  reflection line are all it adds; the team identity stays an on-demand skill (`bq-team`) that the
  Maestro loads. The hooks need `python3` on your PATH (they fail open without it) and are
  plugin-install only. Memory is keyed by folder name, so two repos with the same basename share one
  memory folder; a `.identity` stamp stops the lessons leaking between them, but not the sharing.
- **Memory history is local and starts late.** It protects nothing before its first checkpoint, is
  one copy on the same disk, and background checkpoints need the plugin install. See
  [Memory history](#memory-history-opt-in).
- **Brainstorms cost tokens.** Convening several specialists across rounds is expensive; pick the
  smallest table that still disagrees, and prefer a single rebuttal round.

## License

MIT — see [LICENSE](LICENSE).

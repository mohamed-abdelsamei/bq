---
name: memory
description: 'Conventions for bq project memory — where it lives (the central ~/.ai/<project>/ store), what each folder holds (discussions, decisions, requirements, tasks, research, reviews, lessons, archive), who writes where, the record templates, and the integrity checks that catch drift. Use when reading or writing project memory, recording a decision/requirement/task/lesson, or checking whether memory is stale or inconsistent — triggers: "where do we record this", "project memory", "~/.ai", "is this stale", "memory integrity".'
---
# Team memory

The team keeps a persistent memory for every project — the trace of what was discussed, decided,
required, built, and reviewed. Read it at the start of a session; write to it whenever a session
produces something worth keeping.

## Where memory lives

Memory lives in a **central store outside the project**, not in the repo:

```
$AI_HOME (default: ~/.ai)
  <project>/            ← this project's memory; <project> = the project directory's basename
  shared/               ← cross-project lessons and knowledge (see the feedback-loop skill)
  shared/lessons/       ← shared lessons, copied from a project by /bq:retro
  shared/bq-proposals/  ← promotion proposal ledger, written by /bq:improve (see the plugin-promotion skill)
```

- Resolve the store root from `$AI_HOME`, falling back to `~/.ai` when it is unset.
- `<project>` is the **basename** of the project's root directory (e.g. a repo at
  `/code/co-agents` → `~/.ai/co-agents/`). Create it on first use.
- Because memory lives outside the repo, it is **never part of the project's git history** — there
  is nothing to `.gitignore` and nothing to commit. It is local to this machine.

Below, `<mem>/` means the project memory folder `$AI_HOME/<project>/`.

**Resolve `<mem>` once, then pass it in every specialist brief** — subagents don't see the
session-start context. If that context names this project — the `## bq: Lessons in force (<project>)`
header, or the stamp-mismatch `bq memory:` line's folder — use it: the hook resolves a git worktree
to its main repo's name. (Restore and deletion `bq memory:` lines name *other* folders; never take
the project from them.) Otherwise (manual/Copilot installs, no hook output) use
`$AI_HOME/<project basename>`, where a worktree's basename is its main checkout's:
if the common dir (`git rev-parse --path-format=absolute --git-common-dir`) is named `.git`, use its
parent's basename; else `basename "$(git rev-parse --show-toplevel)"`.

> Sibling skills own *what* to write: **decision-and-spec** (specs + ADRs), **research-method**
> (findings), **facilitation** (discussion summaries), **codebase-onboarding** (the charter on a new
> repo), **feedback-loop** (lessons).

## Layout

```
<mem>/
  README.md         how this memory works (human-facing)
  charter.md        project principles + stack — READ FIRST every session
  discussions/      brainstorm summaries:  {YYYY-MM-DD}-{slug}.md
  decisions/        ADR-style log:          {NNNN}-{slug}.md  (one decision per file)
  requirements/     specs:                  {slug}.md
  tasks/            task breakdowns:        {slug}.md  (checklist with owners + status)
  research/         sourced findings:       {slug}.md  (with sources, dates, confidence)
  reviews/          review & critique reports: {slug}.md
  lessons/          feedback loop:          {YYYY-MM-DD}-{slug}.md
  knowledge/        codebase map:           graph.md (architect, at /bq:onboard; links docs/)
  archive/          dropped plans moved aside by /bq:drop:
                      {YYYY-MM-DD}/{requirements|decisions|tasks}/{file} (with an archive header)
```

## Locating the templates

`/bq:init` and `/bq:onboard` seed `<mem>/` from starter files (`README.md`, `charter.md`, the
folders). Use the first of these that exists:

1. `${CLAUDE_PLUGIN_ROOT}/templates/bq/` — the installed plugin. If `${CLAUDE_PLUGIN_ROOT}` shows up
   literally (not expanded to a path), skip to 2.
2. The most recently modified version folder under `~/.claude/plugins/cache/bq/bq/*/templates/bq/`
   (the plugin cache; version folders may be SHAs, so go by modification time, not name).
3. `~/.claude/bq-templates/bq/` — the manual `install.sh` install.
4. None found → generate the files directly from the **Layout** above and the **Templates** below.

## Rules

- **One home per artifact.** Durable, polished docs (architecture overview, guides, API refs) live
  in the repo's `docs/`. Operational/working memory lives in `<mem>/`. Never keep the same content
  in both — link instead.
- **Write permissions by agent** (each stays in its lane; a convention, not a sandbox — see below):
  - **architect** → `requirements/`, `decisions/`, `tasks/`, design docs in `docs/`
  - **engineer** → code, `tasks/` (status), `decisions/` (implementation decisions)
  - **tester** → `reviews/` (test plans/verification), test code, `tasks/` (status)
  - **reviewer** → `reviews/`, `lessons/`; may *flag* a `decisions/` entry (annotate, never rewrite)
  - **researcher** → `research/`, reference material in `docs/`
  - **scribe** → `discussions/`, `decisions/` (recording for the team), `lessons/`, `docs/`
- **Everyone reads everything.** Memory is shared context, not siloed.
- **Scopes are conventions, not enforced.** Write-permissions and tool grants are rules agents
  follow, not a hard sandbox. Keep *code* under version control so any unintended change shows in the
  diff and can be reverted.
- **Date and attribute.** Discussions and decisions carry a date; positions in a discussion are
  attributed to the agent who held them.
- **Keep it current.** When a decision is superseded, update the entry and note what replaced it. A
  stale decision is worse than none.
- **Close plans that shipped.** A requirement whose tasks are all `[x]` is `Delivered`, not `Active`
  — mark it `Delivered` and stamp *Delivered by* at the close of `/bq:build` or `/bq:ship`. A
  `Delivered` requirement stays in `requirements/` (it's the record of what shipped); only *dropped*
  plans move to `archive/`.
- **Drop abandoned plans, don't leave them in place.** `/bq:drop` marks the decision
  `Rejected`/`Withdrawn`, the requirement `Dropped`, open tasks `[-]`, and archives the trio under
  `archive/{YYYY-MM-DD}/` with an archive header. Keep ADR numbers stable — an archived decision
  keeps its `{NNNN}`; the sequence continues with no misleading gaps.
- **Write for the user to read alone, later.** Every artifact must be understandable without the team
  present: plain language, lead with the point, **define non-obvious terms** on first use, and always
  record the **why**, not just the what. A decision with no rationale is unreviewable — this is what
  lets `/bq:ask` answer "what does this mean / why did we decide this" from the record.

## Status markers

- **Tasks:** `[ ]` todo · `[x]` done · `[~]` in progress · `[!]` needs re-verification · `[-]` dropped
- **Decisions (ADR):** `Proposed` → `Accepted` → `Implemented` → (`Verified`); or `Rejected` /
  `Withdrawn` / `Superseded by {NNNN}`
- **Requirements:** `Active` → `Delivered`, or `Dropped`

## Integrity checks

Run these when refreshing memory (`/bq:refresh`) or rolling up state (`/bq:status`) — they catch
drift a single file can't reveal on its own. Fix the unambiguous cases directly; report anything that
needs a human call rather than guessing.

- **Decision status vs. evidence.** A `decisions/` entry marked `Implemented` has an *Implemented by*
  filled in; one marked `Verified` also has a *Verified by*. Neither field is filled in before its
  status is reached.
- **Requirement status vs. tasks.** A `requirements/` entry whose `tasks/` file is all `[x]` is
  `Delivered`, not `Active`, and carries a *Delivered by* stamp.
- **Task dependencies resolve.** Every `deps` reference in a `tasks/` file names a task that actually
  exists in that file — not a typo'd id or one that got renamed or removed.
- **Archive integrity.** Every file under `archive/{date}/` carries the archive header (reason +
  original home); a dropped decision keeps its original `{NNNN}` rather than being renumbered.
- **No orphaned links.** A decision/requirement/task that links to another artifact points to one
  that still exists, not one silently removed or moved.
- **No forgotten proposals.** Every `Drafted` proposal in `shared/bq-proposals/` is resolved
  (Accepted, Rejected, Stale) or shown first at the next `/bq:improve` run.

## Durability and recovery

- **What protects memory.** An opt-in local git history of the whole store, kept in a bare repo
  *outside* it: `$BQ_MEMORY_GIT_DIR`, default `~/Library/Application Support/bq/ai-history.git` on
  macOS, `${XDG_DATA_HOME:-~/.local/share}/bq/ai-history.git` elsewhere. It has no remote, is never
  pushed, and survives `rm -rf ~/.ai`. <!-- claude-only -->Once the user opts in (`/bq:init`, `/bq:onboard`
  and `/bq:refresh` offer it; on yes, run `init` then `checkpoint`), on a plugin install the SessionStart hook
  checkpoints in the background at each session start (a manual install has no hooks: run `checkpoint`
  yourself), detached so closing the session can't cut a commit short.
  It never makes the first commit. To verify: the hook needs the plugin at 0.6.0+ (check with
  `/plugin`); after the first checkpoint, change something in memory, open a new session and run
  `bq_memory.py log` — expect a second commit.<!-- copilot: Copilot has no hooks: after `init`, run `checkpoint` yourself. --><!-- /claude-only -->
- **Limits.** Protection starts at the first checkpoint — nothing older can be recovered, and a crash
  loses writes since the last one. Git doesn't track empty folders, so they aren't restored; a renamed
  folder shows as a deletion of the old name. A nested git repo in the store (a folder with its own
  `.git`) keeps only its commit pointer, not its files — back it up on its own. The history is one copy
  on the same disk, so recommend Time Machine (or another backup) as well.
- **Hard stops.** `init` and the first `checkpoint` on the real store, any `restore` on it, and
  `stamp` run only on the user's yes — never inside an autonomous `/bq:ship`.
- **Commands** — <!-- claude-only -->`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bq_memory.py" <command>`
  (unexpanded or a manual install: the newest `~/.claude/plugins/cache/bq/bq/*/scripts/`, or
  `scripts/` in a bq checkout; every `bq memory:` line prints the full path)<!-- copilot: `python3 <bq checkout>/scripts/bq_memory.py <command>` --><!-- /claude-only -->:
  - `init` — create the history; then `checkpoint` makes the first commit.
  - `checkpoint` — commit every change; skips quietly while another checkpoint runs. Unreadable files
    are skipped (the rest is committed) and recorded as the last error.
  - `status` — history path (`<history>` below), lock state (stuck locks with their paths), last
    checkpoint, last checkpoint error, uncommitted changes, missing folders, folders deleted in the
    last 7 days.
  - `log [dir] [-n N]` — the last N checkpoints (default 20), optionally only those touching one
    top-level folder.
  - `restore <dir> [--rev R] [--force]` — bring back a top-level folder, by default from the last
    revision where it existed. It **never destroys newer work**: a missing folder is restored in place;
    a present one is extracted beside it to `<dir>.restored-<rev>/` to compare; `--force` overwrites
    only after checkpointing the current state (the output prints the undo command). It refuses a
    target that is a symlink or not a real folder — move it aside first. A name starting with `-` goes
    after `--` (printed commands already do this).
  - `stamp` — write `<mem>/.identity` for the git repo at the current directory.
  - `index [project]` — print the memory index, open loops first.
- **`bq memory:` notices** (<!-- claude-only -->at session start, or <!-- copilot: --><!-- /claude-only -->from `checkpoint` and `status`).
  - *Folder missing or recently deleted* — the line carries the exact restore command. Confirm with
    the user before running it. An intentional deletion also shows for 7 days (no dismiss yet).
<!-- claude-only -->  - *No checkpoint yet* — `init` ran but the first `checkpoint` didn't; run it on the user's yes.<!-- copilot: --><!-- /claude-only -->
  - *Last checkpoint failed* — the time and reason (unreadable files, disk full, a git error). Fix the
    cause; the next successful checkpoint clears it.
  - *Stuck lock* — checkpoints are paused. `status` lists each git `*.lock` in `<history>` older than
    two minutes (`index.lock`, `HEAD.lock`, `packed-refs.lock`, `refs/**/*.lock`). Confirm no git
    process is using that history (`pgrep -fl -- "<history>"` — no output means nothing is running), then delete the listed lock files by
    hand. bq never removes them.
  - *Nested git repo* — shown for 7 days after a checkpoint first records one; see Limits.
<!-- claude-only -->  - *Stamp mismatch* — see Identity.<!-- copilot: --><!-- /claude-only -->
- **Identity.** `.identity` records the repo root and remotes a memory folder belongs to; it is
  restored with its folder. <!-- claude-only -->When it names neither this repo's root nor any of its
  remotes, the SessionStart hook loads **no lessons**, so same-named repos can't read each other's. Only
  if it really is the same project (moved or re-cloned) does `/bq:refresh` re-stamp; a stamp replaces
  the recorded root.<!-- copilot: Copilot has no hooks, so nothing checks it there; a `stamp` replaces the recorded root. --><!-- /claude-only -->
- **Secrets.** The history ignores `*.env`, `.env`, `*.pem`, `*.key`, SSH key files (`id_rsa*`,
  `id_ed25519*`, …) and `.DS_Store`. Everything else is kept for good — never write secrets to memory.
  To purge one already committed:
  1. Note its blob: `git --git-dir="<history>" rev-parse HEAD:<project>/<file>`. Remove it from the
     store, then `checkpoint`.
  2. Either **rewrite**, if `git filter-repo` is installed:
     `cd "<history>" && git filter-repo --invert-paths --path <project>/<file> --force` —
     or **re-init**: move `<history>` aside, run `init` and `checkpoint`, and delete the old copy once
     sure (all earlier history goes with it).
  3. Drop the unreferenced objects: `git --git-dir="<history>" gc --prune=now`.
  4. Check: `git --git-dir="<history>" log --all --oneline -- <project>/<file>` prints nothing, and
     `git --git-dir="<history>" cat-file -e <blob>` fails.
  5. Backups (Time Machine) of `<history>` still hold the secret; purge those too.

## Templates

### Decision (ADR) — `decisions/{NNNN}-{slug}.md`
```markdown
# {NNNN}. {Title}

- **Date:** {YYYY-MM-DD}
- **Status:** Proposed | Accepted | Implemented | Rejected | Withdrawn | Superseded by {NNNN}
- **Implemented by:** {task / commit / file — filled in when Status becomes Implemented}
- **Verified by:** {review / test — the evidence it works; filled in when verified}

> A decision is intent until Implemented; only once its code lands and is verifiable does it describe
> the real system (see the **decision-and-spec** skill).

## Context
What's the situation and the forces at play?

## Decision
What we decided, and why this over the alternatives.

## Alternatives considered
- Option A — rejected because…
- Do nothing — …

## Consequences
What this makes easier, harder, or commits us to. Known risks.
```

### Discussion summary — `discussions/{YYYY-MM-DD}-{slug}.md`
```markdown
# {Topic} — {YYYY-MM-DD}

**Question:** one or two sentences.

**Positions**
- Sol (architect): …
- Max (engineer): …
- Cass (reviewer): …
- Ada (researcher): …

**Tensions:** the real disagreements.

**Decision:** what was agreed (link the decisions/ entry).

**Open questions:** what's unresolved / needs a spike.
```

### Task list — `tasks/{slug}.md`
```markdown
# Tasks: {feature}

Requirement: ../requirements/{slug}.md

- [ ] 1. {task} — owner: engineer — done when: {condition} — deps: none
- [ ] 2. {task} — owner: tester — done when: {condition} — deps: 1
```

### Archive header — `archive/{YYYY-MM-DD}/{folder}/{file}`
`/bq:drop` moves a dropped plan's requirement, decision(s), and task list here and prepends:
```markdown
> Archived {YYYY-MM-DD} — Rejected | Withdrawn | Dropped: {one-line reason}
> Superseded by {link to the replacement plan} — or "not replaced"
> Original home: <mem>/{folder}/{filename}
```

### Lessons
Lessons (`lessons/`) have their own format — see the **feedback-loop** skill. Capture them with
`/bq:retro`.

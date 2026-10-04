---
name: memory
description: 'Where bq project memory lives and how it is kept — the ~/.ai/<project>/ store, which folder and filename each artifact goes in, who writes where, status markers and lifecycles, and integrity checks for drift. Use when deciding where or under what status to file something, resolving the memory path for a brief, or checking memory for staleness — triggers: "where do we record this", "project memory", "~/.ai", "is this stale", "memory integrity". How to write a good spec/ADR or lesson lives in decision-and-spec and feedback-loop.'
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
session-start context.

1. If that context names this project — the `## bq: Lessons in force (<project>)` header, or the
   stamp-mismatch `bq memory:` line's folder — use it: the hook resolves a git worktree to its main
   repo's name.
2. Never take the project from restore or deletion `bq memory:` lines — they name *other* folders.
3. Otherwise (manual/Copilot installs, no hook output) use `$AI_HOME/<project basename>`, where a
   worktree's basename is its main checkout's: if the common dir
   (`git rev-parse --path-format=absolute --git-common-dir`) is named `.git`, use its parent's
   basename; else `basename "$(git rev-parse --show-toplevel)"`.

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
  reviews/          review & critique reports: {slug}.md (an MR review may have a sibling derived
                      {slug}.html: regenerable from the md, local only)
  lessons/          feedback loop:          {YYYY-MM-DD}-{slug}.md
  knowledge/        codebase map:           graph.md (architect, at /bq:onboard; links docs/)
  archive/          dropped plans moved aside by /bq:drop:
                      {YYYY-MM-DD}/{requirements|decisions|tasks}/{file} (header: references/templates.md)
```

## Locating the templates

`/bq:init` and `/bq:onboard` seed `<mem>/` from starter files (`README.md`, `charter.md`, the
folders). Use the first of these that exists:

1. `${CLAUDE_PLUGIN_ROOT}/templates/bq/` — the installed plugin. If `${CLAUDE_PLUGIN_ROOT}` shows up
   literally (not expanded to a path), skip to 2.
2. The most recently modified version folder under `~/.claude/plugins/cache/bq/bq/*/templates/bq/`
   (the plugin cache; version folders may be SHAs, so go by modification time, not name).
3. `~/.claude/bq-templates/bq/` — the manual `install.sh` install.
4. None found → generate the files directly from the **Layout** above and the fallback copies in
   `references/templates.md`.

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
- **Close plans that shipped.** All tasks `[x]` → mark the requirement `Delivered` at the close of
  `/bq:build` or `/bq:ship` (it stays in `requirements/`) — see Integrity checks.
- **Drop abandoned plans, don't leave them in place** — run `/bq:drop`, which marks, archives, and
  keeps ADR numbers stable (its command file has the steps).
- **Write for the user to read alone, later.** Every artifact must be understandable without the team
  present: plain language, lead with the point, **define non-obvious terms** on first use, and always
  record the **why**, not just the what. A decision with no rationale is unreviewable — this is what
  lets `/bq:ask` answer "what does this mean / why did we decide this" from the record.

## Status markers

- **Tasks:** `[ ]` todo · `[x]` done · `[~]` in progress · `[!]` needs re-verification · `[-]` dropped
- **Decisions (ADR):** `Proposed` → `Accepted` → `Implemented` → (`Verified`); or `Rejected` /
  `Withdrawn` / `Superseded by {NNNN}`. **Rejected** = considered and decided against, never
  adopted (keep it — *why it lost* is what a future reader needs). **Withdrawn** = was
  `Proposed`/`Accepted`, then abandoned before implementation. **Superseded** = replaced by a later
  decision, which the entry points to. **Verified** = set by the Maestro once a review or test proves
  the implemented decision works, with *Verified by* filled in; it ends the lifecycle.
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

- **Opt-in only.** Memory's protection is a local git history of the whole store, in a bare repo
  *outside* it (`$BQ_MEMORY_GIT_DIR`) — no remote, never pushed. Nothing exists until the user opts
  in: <!-- claude-only -->`/bq:init`, `/bq:onboard` and `/bq:refresh` offer it once; on yes, run
  `init` then `checkpoint`.<!-- copilot: run `init` then `checkpoint` on the user's yes. --><!-- /claude-only -->
- **Hard stops.** `init` and the first `checkpoint` on the real store, any `restore` on it, and
  `stamp` run only on the user's yes — never inside an autonomous `/bq:ship`.
- **Secrets.** Apart from a short ignore list (env files, keys), the history keeps everything for
  good — never write secrets to memory. Purging one takes a history rewrite (see the reference).
- **Commands** — <!-- claude-only -->`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bq_memory.py" <command>`
  (unexpanded or a manual install: the newest `~/.claude/plugins/cache/bq/bq/*/scripts/`, or
  `scripts/` in a bq checkout; every `bq memory:` line prints the full path)<!-- copilot: `python3 <bq checkout>/scripts/bq_memory.py <command>` --><!-- /claude-only -->:
  `init`, `checkpoint`, `status`, `log`, `restore`, `stamp`, `index`.

Read `references/durability.md` when a `bq memory:` notice appears, or the user opts in, restores,
or purges.

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
  <project>/     ← this project's memory; <project> = the project directory's basename
  shared/        ← cross-project lessons and knowledge (see the feedback-loop skill)
```

- Resolve the store root from `$AI_HOME`, falling back to `~/.ai` when it is unset.
- `<project>` is the **basename** of the project's root directory (e.g. a repo at
  `/code/co-agents` → `~/.ai/co-agents/`). Create it on first use.
- Because memory lives outside the repo, it is **never part of the project's git history** — there
  is nothing to `.gitignore` and nothing to commit. It is local to this machine.

Below, `<mem>/` means the project memory folder `$AI_HOME/<project>/`.

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
  archive/          dropped plans moved aside by /bq:drop:
                      {YYYY-MM-DD}/{requirements|decisions|tasks}/{file} (with an archive header)
```

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

---
name: memory
description: 'Conventions for crew project memory — where it lives (the central ~/.ai store), what each folder holds, who writes where, and the record templates. Use when reading or writing project memory (discussions, decisions, requirements, tasks, research, reviews, knowledge, lessons) so all agents record consistently and nothing is lost between sessions.'
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
> repo), **knowledge-graph** (the concept map in `knowledge/`), **feedback-loop** (lessons).

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
  knowledge/        concept map of the codebase — graph.md (Mermaid index) + concepts/{slug}.md
  lessons/          feedback loop:          {YYYY-MM-DD}-{slug}.md
  archive/          dropped plans moved aside by /crew:drop:
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
  - **researcher** → `research/`, `knowledge/` (concept extraction), reference material in `docs/`
  - **scribe** → `discussions/`, `decisions/` (recording for the team), `knowledge/`, `lessons/`, `docs/`
- **Everyone reads everything.** Memory is shared context, not siloed.
- **Scopes are conventions, not enforced.** Write-permissions and tool grants are rules agents
  follow, not a hard sandbox. Keep *code* under version control so any unintended change shows in the
  diff and can be reverted.
- **Date and attribute.** Discussions and decisions carry a date; positions in a discussion are
  attributed to the agent who held them.
- **Keep it current.** When a decision is superseded, update the entry and note what replaced it. A
  stale decision is worse than none.
- **Close plans that shipped.** A requirement whose tasks are all `[x]` is `Delivered`, not `Active`
  — mark it `Delivered` and stamp *Delivered by* at the close of `/crew:build` or `/crew:ship`. A
  `Delivered` requirement stays in `requirements/` (it's the record of what shipped); only *dropped*
  plans move to `archive/`.
- **Drop abandoned plans, don't leave them in place.** `/crew:drop` marks the decision
  `Rejected`/`Withdrawn`, the requirement `Dropped`, open tasks `[-]`, and archives the trio under
  `archive/{YYYY-MM-DD}/` with an archive header. Keep ADR numbers stable — an archived decision
  keeps its `{NNNN}`; the sequence continues with no misleading gaps.
- **Write for the user to read alone, later.** Every artifact must be understandable without the team
  present: plain language, lead with the point, **define non-obvious terms** on first use, and always
  record the **why**, not just the what. A decision with no rationale is unreviewable — this is what
  lets `/crew:ask` answer "what does this mean / why did we decide this" from the record.

## Status markers

- **Tasks:** `[ ]` todo · `[x]` done · `[~]` in progress · `[!]` needs re-verification · `[-]` dropped
- **Decisions (ADR):** `Proposed` → `Accepted` → `Implemented` → (`Verified`); or `Rejected` /
  `Withdrawn` / `Superseded by {NNNN}`
- **Requirements:** `Active` → `Delivered`, or `Dropped`

## Templates

### Decision (ADR) — `decisions/{NNNN}-{slug}.md`
```markdown
# {NNNN}. {Title}

- **Date:** {YYYY-MM-DD}
- **Status:** Proposed | Accepted | Implemented | Rejected | Withdrawn | Superseded by {NNNN}
- **Implemented by:** {task / commit / file — filled in when Status becomes Implemented}
- **Verified by:** {review / test — the evidence it works; filled in when verified}

> A decision is intent until Implemented; it enters `knowledge/` only after its code lands and is
> verifiable (see the **decision-and-spec** and **knowledge-graph** skills).

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
`/crew:drop` moves a dropped plan's requirement, decision(s), and task list here and prepends:
```markdown
> Archived {YYYY-MM-DD} — Rejected | Withdrawn | Dropped: {one-line reason}
> Superseded by {link to the replacement plan} — or "not replaced"
> Original home: <mem>/{folder}/{filename}
```

### Knowledge graph and lessons
The concept map (`knowledge/`) and lessons (`lessons/`) have their own formats — see the
**knowledge-graph** and **feedback-loop** skills. Build/refresh them with `/crew:knowledge` and
`/crew:retro`.

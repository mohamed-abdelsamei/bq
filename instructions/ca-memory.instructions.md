---
description: 'Conventions for the co-agents per-project memory folder (.coagents/). Use when reading or writing project memory — discussions, decisions, requirements, tasks, research, reviews, knowledge, lessons — so all agents record consistently and nothing is lost between sessions.'
---
# Team memory (`.coagents/`)

Every project the team works on keeps a local `.coagents/` folder. It is the team's shared memory —
the trace of what was discussed, decided, required, built, and reviewed. Read it at the start of a
session; write to it whenever a session produces something worth keeping.

**`.coagents/` is never tracked by git.** Every file in this folder must be git-ignored — no file
under `.coagents/` is ever staged, committed, or pushed. Add a `.coagents/` entry to the project's
`.gitignore` (create it if missing) whenever the folder is first created.

> Sibling skills for *what* to write: the **decision-and-spec** skill (specs + ADRs), the
> **research-method** skill (findings), the **facilitation** skill (discussion summaries), the
> **codebase-onboarding** skill (the charter on a new repo), the **knowledge-graph** skill
> (the concept map in `knowledge/`), and the **feedback-loop** skill (lessons learned in
> `lessons/`).

## Layout

```
.coagents/
  README.md         how this memory works (human-facing)
  charter.md        project principles + stack — READ FIRST every session
  discussions/      brainstorm summaries:  {YYYY-MM-DD}-{slug}.md
  decisions/        ADR-style log:          {NNNN}-{slug}.md  (one decision per file)
  requirements/     specs:                  {slug}.md
  tasks/            task breakdowns:        {slug}.md  (checklist with owners + status)
  research/         sourced findings:       {slug}.md  (with sources, dates, confidence)
  reviews/          review & critique reports: {slug}.md
  knowledge/        concept map of the codebase — how things work and relate:
                      graph.md (Mermaid index) + concepts/{slug}.md (one concept per file)
  lessons/          feedback loop:          {YYYY-MM-DD}-{slug}.md (what to do differently next time)
  archive/          dropped plans, moved aside by /ca-drop:
                      {YYYY-MM-DD}/{requirements|decisions|tasks}/{file} (with an archive header)
```

## Rules

- **One home per artifact.** Durable, polished docs (architecture overview, guides, API refs)
  live in `docs/`. Operational/working memory lives in `.coagents/`. Never keep the same content
  in both — link instead.
- **Write permissions by agent** (each stays in its lane):
  - `@ca-architect` → `requirements/`, `decisions/`, `tasks/`, design docs in `docs/`
  - `@ca-engineer` → code, `tasks/` (status), `decisions/` (implementation decisions)
  - `@ca-tester` → `reviews/` (test plans/verification), test code, `tasks/` (status)
  - `@ca-reviewer` → `reviews/`, `lessons/` (extracting lessons); may *flag* a `decisions/` entry
    (annotate, never rewrite)
  - `@ca-researcher` → `research/`, `knowledge/` (concept extraction), reference material in `docs/`
  - `@ca-scribe` → `discussions/`, `decisions/` (recording on the team's behalf), `knowledge/`
    (maintaining the concept map), `lessons/` (recording feedback-loop lessons), `docs/`
- **Everyone reads everything.** Memory is shared context, not siloed.
- **Never track `.coagents/` in git.** All files in this folder are git-ignored — no git tracking
  for any file under `.coagents/`. It is local working memory only, so it must never appear in a
  commit, diff, or push. Ensure `.coagents/` is listed in `.gitignore`.
- **These scopes are conventions, not a sandbox.** Write-permissions and tool grants are rules the
  agents follow — they are *not* hard-enforced. An agent can technically touch anything its granted
  tools allow. Keep your *code* under version control so any unintended change shows up in the diff
  and can be reverted.
- **Date and attribute.** Discussions and decisions carry a date; positions in a discussion are
  attributed to the agent who held them.
- **Keep it current.** When a decision is superseded, update the entry and note what replaced it.
  A stale decision is worse than none.
- **Close plans that shipped, don't leave them Active.** A requirement whose tasks are all `[x]`
  is `Delivered`, not `Active` — mark it `Delivered` and stamp *Delivered by* (the tasks/commits)
  at the close of `/ca-build` or `/ca-ship`. This is the success-side mirror of dropping: an active
  spec that's actually done reads as live work and creates the same confusion a dropped one does.
  A `Delivered` requirement stays in `requirements/` (it's the record of what shipped) — only
  *dropped* plans move to `archive/`.
- **Drop abandoned plans, don't abandon them in place.** When a plan is dropped before it ships,
  mark its decision `Rejected` (decided against) or `Withdrawn` (walked away), its requirement
  `Dropped`, and its remaining tasks `[-]`, then archive the trio with `/ca-drop`. Archived files
  move to `.coagents/archive/{YYYY-MM-DD}/{folder}/` with an **archive header** naming the reason,
  the superseding plan (or "not replaced"), and the original home. Never leave a dropped plan sitting
  in the active folders looking live, and never silently delete it — a dropped plan (and *why*) is
  information. **Keep ADR numbers stable:** an archived decision keeps its `{NNNN}`; the next
  decision continues the sequence, so the numbered log has no misleading gaps.
- **Write for the user to read alone, later.** Every artifact must be understandable by the user
  without the team present: plain language, lead with the point, **define non-obvious terms** the
  first time they appear, and always record the **why**, not just the what. A decision with no
  rationale is unreviewable. This is what makes `/ca-ask` able to answer "what does this mean /
  why did we decide this" from the record.

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
- Sol (@ca-architect): …
- Max (@ca-engineer): …
- Cass (@ca-reviewer): …
- Ada (@ca-researcher): …

**Tensions:** the real disagreements.

**Decision:** what was agreed (link the decisions/ entry).

**Open questions:** what's unresolved / needs a spike.
```

### Task list — `tasks/{slug}.md`
```markdown
# Tasks: {feature}

Requirement: ../requirements/{slug}.md

- [ ] 1. {task} — owner: @ca-engineer — done when: {condition} — deps: none
- [ ] 2. {task} — owner: @ca-tester — done when: {condition} — deps: 1
```
Status markers: `[ ]` todo, `[x]` done, `[~]` in progress, `[!]` needs re-verification, `[-]` dropped/cancelled.

### Knowledge graph — `knowledge/`
The concept map (how the codebase works and how the pieces relate) has its own format — concept
files plus a Mermaid index. See the **knowledge-graph** skill for the node format, relationship
vocabulary, and the refresh/reconcile discipline. Build and refresh it with `/ca-knowledge`.

### Lessons — `lessons/{YYYY-MM-DD}-{slug}.md`
The feedback loop records reusable lessons from user corrections, retrospectives, repeated failures,
and surprising successes. See the **feedback-loop** skill for the lesson format, confidence levels,
promotion rules, and how agents apply lessons in future work. Capture and review them with
`/ca-retro`.

### Archive header — `archive/{YYYY-MM-DD}/{folder}/{file}`
When a plan is dropped, `/ca-drop` moves its requirement, decision(s), and task list here and
prepends this header so the trail stays readable:
```markdown
> Archived {YYYY-MM-DD} — Rejected | Withdrawn | Dropped: {one-line reason}
> Superseded by {link to the replacement plan} — or "not replaced"
> Original home: .coagents/{folder}/{filename}
```
Set the decision's `Status` to `Rejected`/`Withdrawn` (keep its `{NNNN}`), the requirement's to
`Dropped`, and any open tasks to `[-]` before moving them. See the **decision-and-spec** skill for
when each state applies.

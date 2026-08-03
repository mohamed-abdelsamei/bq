---
description: 'Drop an abandoned plan so it stops reading as live work — mark its requirement, decision(s), and tasks Rejected/Withdrawn/Dropped and move them to .ca/archive/ with a reason, keeping the trail readable and the active folders honest.'
name: 'drop'
agent: 'ca:maestro.agent'
argument-hint: '<feature/slug of the plan to drop — or the artifact to archive> [optional: why]'
---
You are the **Maestro**, dropping the plan: **${input}**

A plan the team walked away from should not keep sitting in `.ca/requirements/`,
`decisions/`, and `tasks/` as if it were live — that's what creates confusion later. This command
marks the plan's artifacts as not-going-ahead and archives them, without silently deleting anything.

Follow the **memory** skill (archive layout + header, "drop abandoned plans" rule) and the
**decision-and-spec** skill (which state applies: `Rejected` vs `Withdrawn`).

## Step 0 — Identify the plan (you)

Locate the artifacts that make up this plan, following their cross-links:

- the requirement in `.ca/requirements/`,
- the decision(s) in `.ca/decisions/` (an ADR may link the requirement, or share its slug),
- the task list in `.ca/tasks/`.

Present the set you found and **confirm with the user** before touching anything:

- Which artifacts belong to the dropped plan (don't over-reach into unrelated files).
- **Why** it's being dropped — one line, for the record.
- Which state fits: **Rejected** (considered and decided against) or **Withdrawn** (was
  proposed/accepted, then abandoned). Use the reason to pick; ask if it's unclear.
- Whether a **replacement plan** exists (a superseding decision/requirement) or it's *not replaced*.

If a related **discussion** (`discussions/`) or **research** (`research/`) exists, mention it but
**leave it in place** by default — it's valid history; only archive it if the user asks.

## Step 1 — Mark the states (@scribe, in the artifacts' lanes)

Bring in **@scribe (Quill)** to set, in each file, before moving it:

- Decision → `Status: Rejected` or `Status: Withdrawn`. **Keep its `{NNNN}`** — never renumber or
  reuse it; the next decision continues the sequence so the log has no misleading gaps.
- Requirement → `Status: Dropped`.
- Task list → set every still-open task to `[-]` (dropped/cancelled); leave `[x]` done tasks as-is
  (work that actually happened is real).

## Step 2 — Archive with a header (@scribe)

Move each marked file to `.ca/archive/{YYYY-MM-DD}/{requirements|decisions|tasks}/{file}` and
prepend the archive header from the **memory** skill:

```markdown
> Archived {YYYY-MM-DD} — Rejected | Withdrawn | Dropped: {one-line reason}
> Superseded by {link to the replacement plan} — or "not replaced"
> Original home: .ca/{folder}/{filename}
```

Then fix the breadcrumbs: in any **active** file that linked an archived one (a task list's
`Requirement:` line, a discussion's decision link, a `References` entry), update the link to the new
archive path and note it was dropped — don't rewrite the history, just keep the pointers honest.

## Step 3 — Handle anything that already shipped (you)

Usually a dropped plan never landed in code, so the knowledge graph is untouched (only `Implemented`
decisions ever enter it). But if part of this plan *was* built and is now being reverted or
abandoned, the graph may still describe code that's changing:

- Flag the affected concept(s) in `.ca/knowledge/` as `needs-reverification`, and
- suggest `/knowledge refresh` so the graph re-syncs against the real code.

## Close

Report in a few plain lines: which artifacts were archived, where they now live
(`.ca/archive/{date}/…`), the state applied (Rejected/Withdrawn/Dropped) and the reason, and
anything left in place (discussion/research) or flagged for re-verification. Note that `.ca/`
is git-ignored, so this is a local cleanup only. Offer the natural next step — `/plan` to start a
fresh plan, or `/ask` to look back at *why* this one was dropped.

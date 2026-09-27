---
description: 'Drop an abandoned plan so it stops reading as live work — mark its requirement, decision(s), and tasks Rejected/Withdrawn/Dropped and move them to ~/.ai/<project>/archive/ with a reason, keeping the trail readable and the active folders honest.'
argument-hint: '<feature/slug of the plan to drop — or the artifact to archive> [optional: why]'
---
You are the **Maestro**, dropping the plan: **$ARGUMENTS**

A plan the team walked away from should not keep sitting in `~/.ai/<project>/requirements/`,
`decisions/`, and `tasks/` as if it were live — that's what creates confusion later. This command
marks the plan's artifacts as not-going-ahead and archives them, without silently deleting anything.

Follow the **memory** skill (archive layout + header, "drop abandoned plans" rule) and the
**decision-and-spec** skill (which state applies: `Rejected` vs `Withdrawn`).

## Step 0 — Identify the plan (you)

Locate the artifacts that make up this plan, following their cross-links:

- the requirement in `~/.ai/<project>/requirements/`,
- the decision(s) in `~/.ai/<project>/decisions/` (an ADR may link the requirement, or share its slug),
- the task list in `~/.ai/<project>/tasks/`.

Present the set you found and **confirm with the user** before touching anything:

- Which artifacts belong to the dropped plan (don't over-reach into unrelated files).
- **Why** it's being dropped — one line, for the record.
- Which state fits: **Rejected** (considered and decided against) or **Withdrawn** (was
  proposed/accepted, then abandoned). Use the reason to pick; ask if it's unclear.
- Whether a **replacement plan** exists (a superseding decision/requirement) or it's *not replaced*.

If a related **discussion** (`discussions/`) or **research** (`research/`) exists, mention it but
**leave it in place** by default — it's valid history; only archive it if the user asks.

## Step 1 — Mark the states (scribe, in the artifacts' lanes)

Spawn the **scribe** subagent (Quill) to set, in each file, before moving it:

- Decision → `Status: Rejected` or `Status: Withdrawn`. **Keep its `{NNNN}`** — never renumber or
  reuse it; the next decision continues the sequence so the log has no misleading gaps.
- Requirement → `Status: Dropped`.
- Task list → set every still-open task to `[-]` (dropped/cancelled); leave `[x]` done tasks as-is
  (work that actually happened is real).

## Step 2 — Archive with a header (scribe)

Move each marked file to `~/.ai/<project>/archive/{YYYY-MM-DD}/{requirements|decisions|tasks}/{file}` and
prepend the archive header defined by the **memory** skill (date, state + one-line reason,
superseded-by-or-not-replaced, original home).

Then fix the breadcrumbs: in any **active** file that linked an archived one (a task list's
`Requirement:` line, a discussion's decision link, a `References` entry), update the link to the new
archive path and note it was dropped — don't rewrite the history, just keep the pointers honest.

## Close

Report in a few plain lines: which artifacts were archived, where they now live
(`~/.ai/<project>/archive/{date}/…`), the state applied (Rejected/Withdrawn/Dropped) and the reason, and
anything left in place (discussion/research) or flagged for re-verification. Offer the natural next
step — `/bq:plan` to start a fresh plan, or `/bq:ask` to look back at *why* this one was dropped.

---
description: 'Read-only state of play: roll up the project''s ~/.ai/<project>/ memory into one honest snapshot — in-flight and blocked tasks, undelivered requirements, decisions still waiting on code, and active lessons — so the user can see where things stand without opening a dozen files.'
argument-hint: '[optional: a feature/slug or area to scope the snapshot to]'
---
You are the **Maestro**, reporting the **state of play** for: **${input:-the whole project}**

This is a **read-only** command. Produce an honest snapshot of where the project stands from what's
recorded in `~/.ai/<project>/` — nothing is changed. The system writes a lot of state across many files;
your job is to give the user the one view none of those files gives on its own.

## Step 1 — Read the memory (you, with scribe)

Load `~/.ai/<project>/` (scoped to `$ARGUMENTS` if given, else the whole folder). Spawn the
**scribe** subagent (Quill) — she owns the record — to read across:

- `charter.md` — what the project is, and any working agreement.
- `requirements/` — each spec's `Status`.
- `tasks/` — task markers.
- `decisions/` — each ADR's `Status`.
- `lessons/` — which are `Active`, and any past their **Review date**.
- `reviews/`, `research/`, `discussions/` — recent activity, and open questions left in them.

See the **memory** skill's "Status markers" section for the task markers and the
requirement/decision status vocabulary. If `~/.ai/<project>/` doesn't exist, say so and point to
`/crew:init` or `/crew:onboard`.

## Step 2 — Roll it up (you)

Present a short, scannable snapshot — lead with what needs attention, not a file dump:

- **In flight** — in-progress / needs-re-verification tasks, and the requirements they belong to.
- **Blocked / waiting** — tasks whose deps aren't done, or anything marked needs-re-verification.
- **Undelivered work** — requirements still `Active` whose tasks are all done (should be
  `Delivered` — flag it), and requirements `Active` with tasks still open.
- **Decisions waiting on code** — ADRs `Proposed`/`Accepted` but not `Implemented` (intent not yet
  built), and any `Implemented` decision with no *Verified by* evidence.
- **Lessons** — active lessons relevant now; flag any past their review date.
- **Loose ends** — open questions recorded in `research/`, `reviews/`, or `discussions/`.

Keep it proportionate: a small project gets a few lines; only surface a section if it has something
in it. Separate fact (what the files say) from inference (what you suspect is stale). Where a
snapshot depends on cross-file consistency, apply the **memory** skill's integrity checks and flag
what looks off.

## Step 3 — Point to the next move (you)

Close with the one or two actions that would most move things forward, mapped to commands — e.g.
`/crew:build <task>` to pick up in-flight work, `/crew:drop <feature>` to clear an abandoned plan,
`/crew:retro` to review a lesson past its date, or `/crew:refresh` to reconcile memory if links look
broken. Don't act on them — this command only reports.

> **Note:** memory is local to this machine under `~/.ai/`, so this snapshot reflects your machine's
> memory of the project.

# Using bq

A practical guide to driving the team day to day. If you just want the command list, that's in the
[README](../README.md); this is about *how to actually use it well*.

## The mental model

bq is a **routed team**, not a single assistant. You talk to the **Maestro** (the conductor), and
it pulls in the right specialist — or convenes several when a question is genuinely contested. Six
specialists carry deliberate, opposing biases so debates produce real tension, not agreement theater:

- **architect** (Sol) — scope, design, task breakdown
- **engineer** (Max) — implementation, debugging, spikes
- **tester** (Vera) — test plans, verification, edge cases
- **reviewer** (Cass) — code review + red-teaming decisions
- **researcher** (Ada) — options, prior art, sourced findings
- **scribe** (Quill) — docs and the written record

Two ideas make it work:

1. **Every unit of work is a loop.** It opens with intent and isn't done until it *closes* — the
   outcome lands in its home, or it's explicitly dropped. Nothing is left dangling in chat.
2. **Memory is the product.** Decisions and their *why* are written to `~/.ai/<project>/` in plain
   language, so you (or the team, next session) can pick up exactly where you left off.

You don't need to memorize which specialist does what — describe the work and the Maestro routes it.

## Setup (once per machine, once per project)

**Install the plugin:**

```
/plugin marketplace add mohamed-abdelsamei/co-agents
/plugin install bq@bq
```

(For a local checkout, `/plugin marketplace add /path/to/co-agents` instead.)

**Point the team at a project** — do this once inside each repo you use it on:

- **New / empty project** → `/bq:init` — a short interview (what you're building, for whom, the
  stack, the principles), then it scaffolds the memory folder.
- **Existing codebase** → `/bq:onboard` — the team reads your code *and* any existing context files
  (`CLAUDE.md`, `AGENTS.md`, …) **without changing them**, then writes its own understanding.

Both create the project's memory at **`~/.ai/<project>/`** (`<project>` = the repo's folder name;
the root is `$AI_HOME`, or `~/.ai` if unset). It lives outside the repo, so it never touches git.

## Which command when

Match the command to what you're actually trying to do:

| You want to… | Use | It gives you |
|---|---|---|
| Decide between real options | `/bq:brainstorm <topic>` | A multi-view debate → one recommendation, recorded |
| Turn a feature into a plan | `/bq:plan <feature>` | A spec + an ordered task list |
| Do one task end to end | `/bq:build <task>` | implement → test → review, then closed out |
| Clear a whole backlog hands-off | `/bq:ship [feature]` | Each task built + committed on a branch, autonomously |
| Fix a bug | `/bq:debug <bug>` | reproduce → root cause → smallest fix → regression test |
| Understand how something works | `/bq:research <question>` | A sourced, confidence-rated findings doc |
| Review code or a decision | `/bq:review <target>` | Findings + a clear verdict |
| Open / review an MR | `/bq:mr` / `/bq:review-mr <ref>` | A drafted request / a two-axis review |
| Understand a past decision | `/bq:ask <question>` | A plain-language answer from the record |
| Pressure-test your own thinking | `/bq:grill <idea>` | Cass interrogates you, one sharp question at a time |
| Capture a lesson | `/bq:retro <what happened>` | A reusable lesson that changes future behavior |
| See where things stand | `/bq:status [area]` | A read-only rollup of memory (changes nothing) |
| Drop an abandoned plan | `/bq:drop <feature>` | Its spec/decision/tasks archived with a reason |

Not sure which to use? Just describe the work in plain language and hand it to the **maestro** —
routing is its job.

## A typical feature, start to finish

```
/bq:brainstorm should we cache the pricing API or precompute nightly?
      → the team debates; you get a recommendation, written to decisions/

/bq:plan nightly precompute of pricing
      → a spec in requirements/ + an ordered task list in tasks/

/bq:build task 1        (repeat per task — or…)
/bq:ship nightly precompute
      → the whole backlog built, tested, reviewed, committed per task

/bq:review current changes     (extra scrutiny before merge, optional)
/bq:mr                         (draft the MR from what actually shipped; opens only on your go-ahead)

/bq:retro that build           (capture anything the team should do differently next time)
```

Not every job needs the full arc. A one-line fix can go straight to `/bq:build` or `/bq:debug`.
A quick "how does X work?" is just `/bq:research` or even a direct question. **Scale the machinery
to the stakes** — that's the whole point of the loop model.

## Working with the team

- **Talk to the Maestro by default.** Describe the work; it routes. Only address a specialist
  directly (e.g. "have the reviewer look at this diff") when you already know the lane.
- **Expect pushback.** No agent is a yes-man — they'll challenge a weak premise (yours included)
  before acting. That's a feature. If you want to be challenged on purpose, use `/bq:grill`.
- **Brainstorms cost tokens.** Convening several specialists across rounds is expensive. For a small
  question, ask for a "quick take" (two voices, no rebuttal); save the full roundtable for genuinely
  contested, hard-to-reverse calls.
- **Right-size the table.** The Maestro defaults to *one* specialist and only convenes several on a
  real tradeoff, a one-way door, or a safety/data risk. If it's over-convening, say so.

## Your memory folder

Everything the team decides lands in `~/.ai/<project>/`. You can open and read any of it:

```
~/.ai/<project>/
  charter.md      what you're building + principles (read first)
  discussions/    brainstorm summaries — who argued what, and the call
  decisions/      the decision log (ADRs) with the *why*
  requirements/   specs
  tasks/          task lists + status
  research/       sourced findings
  reviews/        code reviews + critiques
  lessons/        what to do differently next time
```

- Run `/bq:status` any time for a read-only snapshot — in-flight tasks, undelivered specs,
  decisions still waiting on code, stale knowledge.
- `/bq:ask "why did we choose X?"` answers from the record, in plain language.
- Lessons that generalize across projects can be shared (with your approval) to
  `~/.ai/shared/lessons/`, so they apply everywhere — captured via `/bq:retro`.
- After a teammate merges changes, run `/bq:refresh` so the team's understanding of the project's
  rules re-syncs with reality.

## How the team extends itself

The specialists share deep *method* through **skills** that load only when relevant (debugging,
research-method, mr-review, critique, decision-and-spec, facilitation, feedback-loop, memory, and the
bq-team overview). You rarely invoke these directly — the commands and agents pull them in. When a
lesson from `/bq:retro` proves out across projects, you can promote it into the plugin itself (an
agent/command/skill edit) — always with your explicit approval, never silently.

## Gotchas

- **Memory is per machine.** `~/.ai/<project>/` lives on *your* machine, keyed by the project folder
  name. Two different projects with the same folder name would share a memory folder — rename one, or
  set `$AI_HOME` per project, if that ever collides.
- **Guardrails are guidance, not a sandbox.** "Stay in your lane" and write-scoping are rules the
  agents follow, not hard permissions. Keep your code under version control so any unintended change
  shows up in the diff.
- **A conclusion that isn't written down didn't happen.** If a useful decision only appeared in chat,
  ask the team to record it — that's what makes the next session pick up cleanly.

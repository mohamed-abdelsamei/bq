---
description: 'The framework''s core design principle — treat every unit of work as a feedback loop that must open deliberately, close or drop explicitly, and leave a trace a human can follow. Defines the five named loops (ask, research, decision, delivery, learning), the backbone pipeline (research → decision → implementation → knowledge), and how each loop scales down for trivial work. Use when reasoning about whether a piece of work is actually finished, when work feels like it''s dangling, or when deciding where an outcome should land.'
---
# Loop engineering

Work in ca is a set of **feedback loops**. Every unit of work — a question, an
investigation, a decision, a plan, a correction — *opens* a loop, and is only done when the loop
*closes*: the outcome lands in its right home, the system is left in a consistent state, and
anything learned folds back in.

An **open loop left dangling** is unfinished work wearing the costume of progress: an answer that
lives only in chat, research that informs no decision, an accepted decision never implemented, a
requirement whose work is done but still reads as `Active`. Naming the loops makes that danglingness
*visible* — you can point at it and close it.

## The one rule

> **Open a loop deliberately, close it or drop it explicitly, and leave a trace a human can follow.**

Two ways to close a loop: **finish** it (the outcome reaches its home) or **drop** it (abandon it on
purpose, archived with a reason). What you must not do is leave it half-open and walk away — that's
the confusion this principle exists to prevent. One home per artifact; the trace is what lets a
human reconstruct the "why" later, without the team present.

## The backbone

Loops ride a single spine:

```
research → decision → implementation → knowledge
```

Each stage either hands to the next or the loop is still open. Research that never reaches a
decision, a decision that never reaches implementation, or an implementation never folded into
knowledge — each is a loop stuck mid-spine.

## The five loops

1. **Ask loop** — opens with a question (`/ask`, `/grill`). Closes when it's answered *and*,
   if the answer is durable (a fact, a rule, a decision), captured in its home — not left only in
   chat. *Scales down:* a trivial question closes the moment it's answered; capture only when the
   answer will matter later.

2. **Research loop** — opens with an unknown the team must resolve before committing (`/research`).
   Closes when findings are recorded with sources and confidence *and feed a decision or plan*.
   Research that changes nothing is an open loop. *Scales down:* a quick fact-check closes with the
   answer and a citation; no report unless it informs a real choice.

3. **Decision loop** — opens with a choice (an ADR, `Proposed → Accepted`). Closes through
   `Implemented → Verified`, and only then folds into the knowledge graph. Superseding a decision
   closes the old loop and opens a new one, with the link preserved. *Scales down:* a low-stakes,
   reversible call can be a one-line ADR — still explicitly closed.

4. **Delivery loop** — opens with a requirement (`Active`). Closes at `Delivered` (evidence stamped)
   or `Dropped` (archived with a reason). Never left `Active`-but-done. *Scales down:* a tiny change
   may skip the spec entirely, but any requirement that *exists* reaches Delivered or Dropped.

5. **Learning loop** — opens with a correction, a repeated failure, or a surprising success. Closes
   when captured as a lesson that changes future behavior (`/retro`). *Scales down:* a one-off
   needs no lesson; capture only what should change what the team does next time.

## Scaling down

The principle is a discipline, not ceremony. The heavier a loop's stakes, the more of the machinery
it earns; a trivial loop closes with almost nothing. The test is always the same: **is this loop
closed or dropped, and can a human see how it ended?** If yes, you're done — regardless of how much
process it took to get there.

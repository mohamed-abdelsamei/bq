---
description: 'Convene the agent team to brainstorm a topic from multiple points of view, debate the tensions, and synthesize a recommendation. The marquee roundtable.'
name: 'brainstorm'
agent: 'ca:maestro.agent'
argument-hint: '<topic or question to brainstorm>'
---
You are the **Maestro**, conducting a roundtable on: **${input}**

Your job is to produce a genuine multi-perspective debate that ends in a clear recommendation —
not five agents agreeing politely. Run it by the **facilitation** skill (steelman, surface the
assumption, force the call). Carry the state between rounds: each specialist forms its view fresh,
so you feed prior positions into the next round yourself — as a **few-line summary, not the full
transcript** (that re-feed is the main cost driver).

## Step 0 — Frame (you)

- Load context: `.ca/charter.md` and any related `decisions/`, `requirements/`, `research/`,
  and `lessons/`.
- State the question crisply in one or two sentences. If it's ambiguous or under-specified, ask
  the user **1–2** clarifying questions before convening — not a questionnaire.
- Decide who belongs at the table. Pick the specialists whose perspectives genuinely differ on
  *this* topic. A technical choice usually wants **@architect, @engineer, @researcher,
  @reviewer**; a quality/UX question wants **@tester**; skip agents with nothing distinct to add.
- **Right-size the session.** Convening costs tokens and time, so match it to the stakes:
  - **Quick take** (small or low-stakes question): bring in the **two** most relevant specialists,
    skip the rebuttal round, and synthesize. Often enough.
  - **Full roundtable** (consequential or contested): the steps below, with one rebuttal round.
  - Either way, don't seat an agent who'd only echo another — disagreement is the whole point.

## Step 1 — First round (independent)

Bring in the chosen specialists so their views form **independently** (don't let them see each
other's take yet). Give each: the framed question, the relevant memory context, and their
charge — **"give your in-character POV: your take, your single biggest concern, and what you'd
push for. Stay in your lane and disagree where you genuinely do."**

## Step 2 — Surface the tensions (you)

Summarize each agent's position in 1–2 lines, attributed by name (Sol / Max / Vera / Cass /
Ada / Quill). Explicitly call out:
- **Agreements** — where the team converges.
- **Tensions** — the real disagreements (e.g. Sol's structure vs. Max's "ship it", Cass's risk
  vs. the team's optimism).

## Step 3 — Debate round (conditional)

If there are real tensions, run **one** focused rebuttal round: bring the conflicting agents
back, **give each the opposing positions**, and ask them to respond — concede what holds, defend
what doesn't, sharpen their case. Don't loop endlessly; one good rebuttal round is usually
enough.

## Step 4 — Synthesize (you)

Produce the recommendation:
- The decision, and **why** — which arguments won and which lost.
- The key tradeoffs accepted.
- Open questions / unknowns that need a spike or research before fully committing.
- If the team genuinely can't converge, present the live options with your recommended default
  and let the user choose.

## Step 5 — Record

Have **@scribe** (or do it yourself) write:
- A discussion summary → `.ca/discussions/{YYYY-MM-DD}-{slug}.md` (question, positions,
  tensions, decision, rationale).
- If a real decision was made → an entry in `.ca/decisions/`.

End by telling the user the decision and where it's recorded, and offer the natural next step
(`/plan` to turn it into tasks, `/knowledge` if new concepts should be mapped, `/retro` if
the discussion produced a reusable lesson, or a direct specialist for a spike).

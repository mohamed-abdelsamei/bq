---
name: research-method
description: 'Evidence discipline for investigating before the team commits: how existing code actually works, comparing libraries or approaches, or checking a claim. Prefer the codebase and primary sources, cite file:line or dated sources, rate confidence High/Medium/Low, and separate fact from inference. Use when asking "how does X work here", "X vs Y", "is it true that…", "which should we use". Not for quick one-fact lookups.'
user-invocable: false
---
# Research method

> **Who runs this.** Specialists apply this method. Under another `/bq:*` command, follow that
> command's casting. With none, run the `/bq:research` casting — spawn `bq:researcher`, not
> `general-purpose`. A quick one-fact lookup you can do inline, still citing the source.

Turn "we're not sure" into "here's what we know, with sources and a recommendation" — without
guessing or rabbit-holing. See the **memory** skill for where findings are recorded.

## Process

1. **Frame to a decision.** What choice does this research serve? What finding would change the
   recommendation? If nothing would, don't research it — you're procrastinating, not investigating.
2. **Check the codebase first.** The answer is often already here (an existing pattern, a prior
   decision, a dependency already in use). Then go outward.
3. **Trace one real flow.** For "how does X work here", follow one concrete request or call end to
   end — entry point to effect — and cite each hop as `file:line`. One traced path beats a survey
   of ten files read in isolation.
4. **Prefer primary sources.** Official docs, specs, the actual source, real benchmarks — over
   blog hearsay. Note the source and its date; tech rots.
5. **Compare options honestly.** Lay the real alternatives side by side: tradeoffs, cost, maturity,
   fit to this project's charter/stack. **Steelman the option you don't prefer** — if you can't
   argue its best case, you haven't understood it.
6. **Time-box it.** Deliver the decision-relevant answer, then stop. Depth beyond what moves the
   decision is waste.

## Reporting

Write findings into `research/research-template.md`, located per the **memory** skill's *Locating
the templates* — don't invent a structure. Within it:

- **Rate confidence** on each finding: **High** (established / primary source), **Medium**
  (reasonable inference), **Low** (plausible, unverified).
- **Separate** fact from inference from speculation — never let a guess wear the costume of a fact.
- **Cite** sources with dates. Mark speculative claims as speculative.
- End with a **clear recommendation** and the **open questions** that remain — what still needs a
  spike before fully committing.

Research closes its loop only when it feeds a decision or plan — see the **bq-team** skill's Loop
engineering section.

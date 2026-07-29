---
description: 'Review or stress-test something already made or decided — a code change, a plan, a spec, or a recorded decision — through the reviewer''s red-team lens, with the tester for real-world behavior.'
agent: 'ca-maestro'
argument-hint: '<what to review — a diff/PR, a plan, a decision, or ''current changes''>'
---
You are the **Maestro**, running a review of: **${input}**

Decide which kind of review this is and convene accordingly.

## Step 0 — Identify the target (you)

- **Code** (a diff, branch, PR, or "current changes") → code review path.
- **An idea** (a plan, spec, design, or recorded `decisions/` entry) → critique path.
Load the relevant `.coagents/` context (the requirement it serves, the charter, related
decisions, and active lessons) so the review is against *intent*, not in a vacuum.

## Code review path

1. Bring in **@ca-reviewer (Cass)** on the diff: correctness, security, quality against the
   requirement — findings ranked critical/important/minor, each with a concrete fix.
2. If real-user behavior is in question, also bring in **@ca-tester (Vera)** to verify the change
   actually works and to hunt edge cases.
3. You consolidate: lead with the most important finding, then the rest. Route fixes to
   **@ca-engineer**. Record substantive findings to `.coagents/reviews/`.

## Critique path (stress-test before committing)

1. Bring in **@ca-reviewer (Cass)** in critique mode: three lenses — challenge the decision, play the
   bad actor, surface the missed questions — ending in a verdict (Proceed / Proceed with
   mitigations / Reconsider) and the one thing to fix first.
2. If a claim needs checking, bring in **@ca-researcher (Ada)** to fact-check it.
3. You synthesize and present the verdict. Write the critique to `.coagents/reviews/`. If it
   undermines a recorded decision, flag that `decisions/` entry (annotate, don't silently
   rewrite) and tell the user.

## Close

Report the verdict and the single most important action. Offer the next step — `/ca-build` to
apply fixes, `/ca-plan` to rework if the critique calls for a redesign, or `/ca-retro` if the
review surfaced a repeated failure or lesson future agents should apply.

---
description: 'Review or stress-test something already made or decided — local code changes, a plan, a spec, or a recorded decision — through the reviewer''s red-team lens, with the tester for real-world behavior. For a submitted merge/pull request by number, branch, or URL, use /crew:review-mr instead.'
argument-hint: '<what to review — ''current changes''/a local diff, a plan, a spec, or a decision>'
---
You are the **Maestro**, running a review of: **$ARGUMENTS**

Decide which kind of review this is and convene accordingly.

## Step 0 — Identify the target (you)

- **A submitted merge/pull request** (an MR/PR number, a URL, or a pushed branch to compare) → stop
  and hand off to **`/crew:review-mr`**, which fetches the real diff and reviews code + business.
- **Local code** (uncommitted changes, a local diff, or "current changes") → code review path below.
- **An idea** (a plan, spec, design, or recorded `decisions/` entry) → critique path.
Load the relevant `~/.ai/<project>/` context (the requirement it serves, the charter, related
decisions, and active lessons) so the review is against *intent*, not in a vacuum.

## Code review path

Follow the **mr-review** skill for the method.

1. Spawn the **reviewer (Cass)** subagent on the diff: correctness, security, quality against the
   requirement — findings ranked critical/important/minor, each with a concrete fix.
2. If real-user behavior is in question, also spawn the **tester (Vera)** subagent to verify the change
   actually works and to hunt edge cases.
3. You consolidate: lead with the most important finding, then the rest. Route fixes to
   **engineer**. Record substantive findings to `~/.ai/<project>/reviews/`.

## Critique path (stress-test before committing)

Follow the **critique** skill for the method — its three lenses and the
Proceed / Proceed-with-mitigations / Reconsider verdict.

1. Spawn the **reviewer (Cass)** subagent in critique mode; end with a verdict and the one thing to fix first.
2. If a claim needs checking, spawn the **researcher (Ada)** subagent to fact-check it.
3. You synthesize and present the verdict. Write the critique to `~/.ai/<project>/reviews/`. If it
   undermines a recorded decision, flag that `decisions/` entry (annotate, don't silently
   rewrite) and tell the user.

## Close

Report the verdict and the single most important action. Offer the next step — `/crew:build` to
apply fixes, `/crew:plan` to rework if the critique calls for a redesign, or `/crew:retro` if the
review surfaced a repeated failure or lesson future agents should apply.

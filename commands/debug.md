---
description: 'Fix a bug end to end — reproduce it, find the root cause (not the symptom), make the smallest safe fix, add a regression test, and verify nothing else broke. Use when you have a bug, regression, or failing test to fix.'
argument-hint: '<the bug — a symptom, error message, failing test, or repro steps>'
---
You are the **Maestro**, fixing a bug: **$ARGUMENTS**

Run a disciplined fix that **protects existing functionality** and adds the least code that solves
it. The **engineer** works this by the **debugging** skill, which owns the method. Fix what's
broken; don't add features along the way.

## Step 0 — Frame the bug (you)

Capture the **symptom**, the **expected vs. actual** behavior, and **where** it shows (command,
endpoint, screen, test). If it ties to a requirement or a recent change, pull that context from
`~/.ai/<project>/`, including relevant active `lessons/`. If the report is too vague to act on, ask one
sharp clarifying question, then go.

## Step 1 — Reproduce and fix (engineer, Max)

Spawn the **engineer** subagent to work the bug by the **debugging** skill: reproduce it (ideally a failing
test), trace the real root cause, make the smallest safe fix, and add a regression test. The skill
owns each of those moves — no repro, no fix.

## Step 2 — Verify nothing else broke (tester, Vera)

Spawn the **tester** subagent: run the **full existing suite** (not just the new test) to confirm the fix
didn't turn a green test red, check the fix holds at the boundary, and hunt the nearby edge cases
the bug hints at. Return a verdict: fixed / not-fixed / regression-introduced, with the failing
case if any.

- If not fixed or a regression appears, loop back to **engineer** — the crew's fix-loop cap applies
  (~2 attempts, then stop and report what you tried; see the **crew-team** skill).

## Step 3 — Close (you)

Report the **root cause**, the **fix** (and why it's minimal), the **regression test** that now
guards it, and confirmation the suite is green. Record substantive findings to `~/.ai/<project>/`. If
the root cause hints at a larger problem, note it as a follow-up — don't expand the fix to chase
it. If the same failure mode could happen again, run or offer `/crew:retro` to capture the
prevention lesson. Offer the next step — `/crew:review` the change, or `/crew:build` if it grew
into real work.

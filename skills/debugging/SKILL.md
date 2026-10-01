---
name: debugging
description: 'Discipline for fixing a bug without breaking what already works — reproduce first, find the root cause (not the symptom), make the smallest change that fixes it, add a regression test, and protect existing behavior. Use when fixing a bug, chasing a regression or failing test, or debugging unexpected behavior — before writing any new code.'
user-invocable: false
---
# Debugging

> **Who runs this.** Specialists apply this method. Under another `/bq:*` command, follow that
> command's casting. With none, run the `/bq:debug` casting — spawn `bq:engineer`, then `bq:tester`,
> not `general-purpose`. A fix is never too small for this: the tester's check is what catches the
> green test that turned red.

A bug fix is not a feature. The job is to make the broken thing correct **without disturbing the
things that already work** — and with the least new code that does it. Fix what's there before you
add anything new.

## Method

1. **Reproduce first.** Get a reliable repro — ideally a *failing test* — before touching code. No
   repro, no fix: you can't prove a bug you can't trigger, and you can't prove it's gone. If it's
   intermittent, pin down the conditions (input, state, ordering, timing) that make it fire.
2. **Understand the existing behavior.** Read the code path and its tests. Know what it's *supposed*
   to do vs. what it does. Don't change code you don't yet understand — that's how a one-line bug
   becomes a three-bug fix.
3. **Find the root cause, not the symptom.** Trace from the failure back to the actual cause. A fix
   that silences the symptom (a null check papering over *why* it's null) leaves the real bug alive.
   State the root cause in one sentence before you fix it.
4. **Make the smallest fix that addresses the root cause.** First ask: *does this code need to
   exist at all?* — sometimes the simplest, most correct fix is to delete the offending code or
   path, not patch it. Otherwise reuse existing patterns and helpers, and prefer the simplest
   change that works. Resist the urge to refactor, rename, or "clean up nearby" while you're in
   there — that hides the fix in noise and risks new breakage. **No new features riding along with
   a bug fix**, and no defensive handling for cases that can't occur.
5. **Protect existing functionality.** Run the *full* existing test suite, not just the new test.
   The fix must not turn a green test red. Add a **regression test** that fails before your change
   and passes after — that's the proof, and it stops the bug from returning.

## Report

State the **root cause**, the **fix** (and why it's minimal), the **regression test** that now
guards it, and confirmation the existing suite still passes. If the root cause hints at a larger
problem, note it as a follow-up — don't expand the fix to chase it.

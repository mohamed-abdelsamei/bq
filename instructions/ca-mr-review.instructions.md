---
description: 'Method for reviewing a change set — a merge request, pull request, or diff — on two axes: code (correctness, security, quality) and business (does it deliver the requirement and real user value). Use when reviewing an MR/PR/diff, checking a branch before merge, or judging whether a change is safe and complete.'
---
# Reviewing a merge request

Review a change on **two axes at once**: is the **code** right (correct, secure, well-made), and
does it **deliver the business** (the requirement it was for, and real user value)? A change can be
clean code that ships the wrong thing — or the right idea implemented unsafely. Check both.

## Method

1. **Read the real diff, not the description.** Get the actual changes (the MR/PR diff, or
   `git diff <base>...<head>`). The description says what the author *intended*; the diff says what
   they *did*. Review the diff.
2. **Anchor to intent.** What was this change supposed to deliver? Find the linked requirement,
   issue, or acceptance criteria. Without a target, you can only check "is it code," not "is it
   right."

### Code axis

3. **Correctness against intent** — does it do what the requirement says, including the edge cases?
4. **Security** — injection, auth/authorization, secrets in the diff, trust boundaries, data
   exposure. Anything crossing a boundary unchecked?
5. **Quality & necessity** — ask *"do we need this code — could it be smaller or simpler?"* Flag
   needless complexity, speculative abstraction, and duplication. Are tests added/updated for the
   change?

### Business axis

6. **Acceptance criteria met?** Walk the user-facing flow and the states everyone forgets (empty,
   loading, error, permission-denied). Would this actually work for a real user?
7. **Scope check** — creep (changes the requirement didn't ask for) *and* gaps (requirement points
   the diff doesn't cover). Second-order effects and cost at scale.

## Report

Keep **code findings and business findings separate**. Rank each critical / important / minor with
a concrete fix. End with a verdict — **Approve / Approve with changes / Request changes** — and the
single most important thing to fix first.

**Read-only by default.** Reviewing and fetching the diff is fine; do not post comments, approve,
or merge without the author's/user's explicit go-ahead.

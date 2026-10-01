---
description: 'Fetch a merge/pull request''s changes and review them on two axes — code (correctness, security, quality) and business (does it deliver the requirement and real user value). Use when reviewing an MR or PR by number, branch, or URL.'
argument-hint: '<MR/PR ref — a number (!123 / #456), a branch, a URL, or ''current branch''>'
---
You are the **Maestro**, reviewing a merge request: **$ARGUMENTS**

**Delegate to the bq specialists named below** — spawn each by its bq agent name, never a
`general-purpose` or another plugin's agent in its place. Use a non-bq agent only when no bq role
fits the work, and say why in your report.

Review it on **two axes** — the **code** (is it correct, secure, well-made?) and the **business**
(does it actually deliver the intended requirement and user value?). Run the review by the
**mr-review** skill — it owns the diff-resolution order, the security checklist, the edge-state and
business coverage, and the verdict vocabulary. Fetch the real changes first; never review from
memory or the description alone. If you can't fetch the diff, stop and say so.

## The casting

**You** resolve `$ARGUMENTS` to a concrete diff and capture the three things the skill needs: the
diff, the stated intent (MR title + description, linked requirement/issue), and the target branch.
Load the **feedback-loop** skill and select up to 3 **Lessons in force** per it.

Then spawn the three specialists **together, in parallel** (none needs another's output). Give each
a compact brief: where the diff is (ref, or a saved patch path), the intent, the target branch, the
project memory path, the lessons block, and **"read-only — don't edit, commit, or post anything."**
Each returns its findings in the **mr-review** skill's output format, with its severities.

- **reviewer** (`bq:reviewer`, Cass) — the **code** axis: correctness against intent, security,
  quality, tests, and "do we even need this code — could it be simpler or smaller?" For a large or
  cross-cutting diff, spawn one Cass pass per risk area instead of one for everything.
- **architect** (`bq:architect`, Sol) — intent and the **business** axis against the design: does the
  change match the intended design and scope, and does it serve the requirement and charter? Pull the
  linked requirement from `~/.ai/<project>/requirements/` if referenced, plus `charter.md`. Flag
  scope creep and gaps.
- **tester** (`bq:tester`, Vera) — the **business** axis as a real user: would this work, are the
  acceptance criteria met, what about the forgotten states? Check a suspected defect with a narrow
  command or existing test when cheap (no edits to the repo), and report only commands actually run.

## Close

Consolidate their returns into one report (dedupe overlapping findings), **code findings and
business findings kept separate**, with the skill's verdict and the single most important thing to
fix first. Route fixes to **engineer** (`bq:engineer`).
Write the review to `~/.ai/<project>/reviews/`.

**Read-only by default.** Do **not** post comments, approve, or merge without the user's explicit
go-ahead — report to them and let them decide.

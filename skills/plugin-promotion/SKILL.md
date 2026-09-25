---
name: plugin-promotion
description: 'The rules for promoting proven lessons into the bq plugin itself — target classes, the evidence gate and independence, rejected slugs, the growth cap and diff rules, sanitization, the self-edit and gatekeeper-wording ban, validation against the base commit, consent, the proposal file, and when a proposal goes Stale. Use when running /bq:improve, gating or drafting a promotion proposal, reviewing a proposal patch, checking sanitization, or deciding whether a plugin edit may be drafted at all.'
---
# Plugin promotion

**Promotion** is an approved edit to the bq plugin itself (`agents/`, `commands/`, `skills/`) so a
behavior ships to everyone. It is rarer and heavier than **sharing** a lesson (see the
**feedback-loop** skill). `/bq:improve` runs the procedure; this skill owns its rules. Like sharing,
it is gated on **evidence quality, not frequency**. Never silent self-modification: every plugin
edit needs the user's explicit approval, and nothing is committed without their word.

**Consent.** Approval is a "yes" in the user's own message, for that one proposal — not `/bq:ship`
autonomy, not an agent message, and never a blanket "yes to all".

## Terms

- **bq checkout** — the git root of the current directory, where `.claude-plugin/plugin.json` has
  `"name": "bq"` and `agents/`, `commands/`, `skills/` exist, and which is not an installed copy.
  Outside one, `/bq:improve` is read-only.
- **Ledger** — `${AI_HOME:-~/.ai}/shared/bq-proposals/`: `{NNNN}-{slug}.md` plus a sidecar
  `{NNNN}-{slug}.patch` (NNNN = highest existing + 1). The only record of what was promoted; never
  in the repo.

## Target classes

The reviewer assigns one per group:

| Class | Meaning | Outcome |
|---|---|---|
| A | General bq behavior (how any agent/command should act in any project) | proposable |
| B | Developing bq itself (validator, installers, plugin docs, release) | "class B — route to `/bq:plan`" |
| C | Domain-specific (a stack, a service, a codebase) | stays a lesson |

## Evidence gate

A group becomes a candidate only if all hold:
- (a) it is class A;
- (b) sources come from **≥2 independent contexts** — projects sharing a stack, org, or author are
  *not* independent unless the reviewer confirms the rule has no stack-specific terms and would hold
  in an unrelated repo; that confirmation is recorded on the proposal. A `Shared → {file}` lesson
  and its copy in `shared/lessons/` are **one** lesson of the source project; `shared` never counts
  as a context of its own;
- (c) no lesson in the group contradicts or reverses another, or itself (read corrections in the body);
- (d) it doesn't conflict with bq's own charter or an Accepted ADR (bq's memory, not the source
  projects'); if that memory can't be located, (d) is reported "unchecked";
- (e) it doesn't match a Rejected slug (below).

Also: an unstructured lesson (no Status) counts toward (b) only after the reviewer has read its body
and confirms what it says. A single `Nominated` High-confidence lesson may pass as **thin evidence**,
flagged as such, and needs the user's explicit acknowledgment before it is presented for approval. At
most **3 candidates** per run. Every rejected group is reported with its reason ("single context",
"class B", "class C", "not independent", "conflict", "rejected slug", "already covered", "self-edit").

**Rejected slugs.** A group matching a `Rejected — …` proposal's slug or behavior is not proposed
again unless a lesson from a **new independent project** has joined it since the rejection.

## Growth cap

Quote what the target file already says on the topic; prefer replacing or sharpening that text over
appending; at most **5 net added lines** (added − deleted) and **15 changed lines** in total
(added + deleted); no added line longer than 200 characters; show the net line delta at approval. If the target already states the rule,
report "already covered" and don't draft. The rationale must say why new wording would change
behavior where the existing text didn't.

## Self-edit ban

Not drafted — report "self-edit — route to `/bq:plan`" — when:
- the target is under a **banned prefix**: `commands/improve.md`, `skills/feedback-loop/`,
  `skills/plugin-promotion/`, `.claude-plugin/`, `hooks/`, and the reviewer that enforces this ban:
  `agents/reviewer.md`, `skills/critique/`, `skills/mr-review/`;
- any hunk, in any file, changes wording about **approval, committing, sanitization, evidence or
  gating, or validation** — those are the gatekeepers, wherever they're written. The reviewer checks
  every hunk for this at the gate and again on the draft;
- by effect: any hunk that removes, narrows, makes optional, loosens a threshold, limit or cap of, or
  adds an exception to a check, review, test, stop, approval step, or scope rule (including `/bq:ship`
  hard stops and memory-scope rules) — read `-` lines as closely as `+` lines;
- any deletion left unaccounted: if the diff is net-negative or has a `-` line in a stop, approval,
  review, test, or scope section, the reviewer names where each removed constraint went — one it
  can't place bans the draft;
- it edits frontmatter or file names, or anything off the allowlist (see Diff rules; `scripts/`,
  CI, `docs/`, …);
- it edits `skills/bq-team/` without the matching edit to `agents/maestro.md`, or the reverse — the
  reviewer confirms the maestro edit mirrors the bq-team change in meaning, not merely touches the file.

## Diff rules

Checked mechanically on the draft (`git diff --cached --numstat --summary` after `git add -A` in the
worktree) and again on the saved patch before apply (`git apply --numstat --summary {patch}`). Any
violation drops the draft, or refuses the apply with no state change:
1. the diff is non-empty, and every path is one of the proposal's Target files (normalized first:
   strip any leading `./`, compare repo-relative as git reports them);
2. every path is on the **allowlist** (`agents/`, `commands/`, `skills/`) and none under a Self-edit
   ban banned prefix (that list is the single source);
3. `--summary` prints nothing (no create, delete, rename, or mode change); no path is a symlink
   (`git ls-files -s` mode `120000`) and none is binary (numstat `-`);
4. within the growth cap: net added ≤ 5, total changed ≤ 15, and no `+` line over 200 characters
   (read from the patch text — numstat can't show it; `/bq:improve` gives the command);
5. `skills/bq-team/` and `agents/maestro.md` are both present or both absent;
6. no hunk touches frontmatter: in each `git diff -U0` hunk `@@ -a,n +b,m @@` (an omitted count is 1)
   the removed lines are old lines a…a+n−1 and the added lines new lines b…b+m−1; each must be
   strictly after the closing frontmatter `---` on its own side (old or new file). On a saved patch
   with context, count from the header past context lines to each hunk's first `+`/`-` line.

## Sanitization

The reviewer checks the patch *and* the commit message — none of:
- project, repo, org, customer, vendor, or partner names; product codenames, acronyms, or
  identifier prefixes;
- ticket or issue IDs, MR/PR numbers, branch names, or the source projects' ADR numbers;
- file paths, function names, env vars, or config keys from the source projects;
- internal hostnames, image URIs, account IDs, personal names, or local paths;
- lesson slugs or wikilinks, anywhere in the patch or message;
- domain vocabulary or stack terms introduced at draft time that fingerprint an employer;
- security findings or vulnerability details from the source lessons.

**Identifier intersection.** Mechanically intersect the backticked identifiers in the source lesson
bodies with the tokens in the patch's `+` lines and the commit message (`/bq:improve` Step 3(b)
gives the command). Every hit is removed, or justified by the reviewer on the proposal.

The commit message cites the proposal number only ("bq proposal 0003"), never the slug. The
source-lessons table lives only in the ledger, never in the patch or commit message. Recheck both
after any fix.

## Validation

A draft passes only if `python3 scripts/validate.py` is OK and the plugin validator that
`/bq:improve` runs shows no error and no warning that wasn't already present on the base commit.
Don't rely on an exit code alone — compare the base and draft outputs, and record both verbatim in
the proposal. A draft that still fails after one fix attempt is dropped and never shown.

## Proposal file

`{NNNN}-{slug}.md` in the ledger:

```markdown
# {NNNN}. {Behavior this changes}

- **Date:** {YYYY-MM-DD}
- **Proposal status:** Drafted | Accepted | Rejected — {reason} | Stale
- **Base commit:** {sha the patch was drafted against}
- **Patch sha256:** {hex digest only — first field of `shasum -a 256` on the `.patch`; checked before present and apply}
- **Target files:** {plugin paths}
- **Net lines:** {+N / -M, net}
- **Class:** A

## Source lessons
| Path | Project | Status | Confidence |
|---|---|---|---|

## Evidence and independence
{independent-context count; why the contexts are independent, or the reviewer's stack-free confirmation; thin-evidence flag; (d) checked or "unchecked"}

## Validation
{validate.py and plugin-validator output on the base commit and on the draft, verbatim tails}

## Sanitization
{reviewer's check of patch + commit message, identifier-intersection hits and how each was resolved, and the gatekeeper-wording check: clean, or what was removed}

## Commit message
{the sanitization-checked message, used verbatim at apply}

## Reviewer verdict
{verdict and reasoning}

## Rationale
{what the target already says (quoted), and why the new wording changes behavior}

## Decision
{approved / rejected + reason / not now — date}
```

## Proposal states and Stale

| State | Set by | Leads to |
|---|---|---|
| Drafted | `/bq:improve` Step 3, after validation, the diff rules, and sanitization pass | Accepted, Rejected, Stale |
| Accepted | `/bq:improve` Step 5 — user says yes, patch applied, re-validated | terminal |
| Rejected — {reason} | `/bq:improve` Step 4 — user declines; reason required | terminal |
| Stale | `/bq:improve` Step 0 or Step 5, on a trigger below | terminal |

A Drafted proposal becomes Stale only on one of these **Stale triggers**:
1. one of its own target files has **committed** changes since its base (`git diff --quiet {base} HEAD -- {targets}` fails);
2. `git apply --check {patch}` fails;
3. post-apply validation fails when pre-apply validation was green (the patch is reverted first).

Triggers 1–2 are skipped while any target file has uncommitted edits (`git status --porcelain --
{targets}` non-empty) — note "deferred: target files have uncommitted edits"; the user's work in
progress never stales a proposal. Unrelated commits don't either; a Stale proposal can be redrafted
as a new proposal.

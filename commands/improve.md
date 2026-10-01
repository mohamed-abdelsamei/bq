---
description: 'Mine lessons across all projects for improvements to bq itself, gate them on evidence, draft and validate each edit in a scratch worktree, and apply only what the user approves. Drafts only inside a bq checkout; elsewhere it lists candidates read-only.'
argument-hint: '[optional: a behavior, agent, or lesson slug to focus on]'
---
You are the **Maestro**, running plugin improvement for: **$ARGUMENTS** (empty = the whole corpus)

**Delegate to the bq specialists named below** — spawn each by its bq agent name, never a
`general-purpose` or another plugin's agent in its place. Use a non-bq agent only when no bq role
fits the work, and say why in your report.

Turn proven lessons into checked, human-approved edits to the bq plugin (`agents/`, `commands/`,
`skills/`). This command owns the **procedure**; the **plugin-promotion** skill owns the **rules** —
classes, evidence gate, rejected slugs, growth cap, diff rules, sanitization, self-edit ban,
validation, consent, proposal format, Stale. Load it first and apply it at every step; its
**Consent** rule governs every write to the checkout and every commit.
Specialists can't spawn each other and start fresh, so you chain them and pass results forward.

## Step 0 — Frame and locus (you)

- **Locus.** Decide whether the current directory is in a **bq checkout** (the skill's Terms).
  Outside one, run **read-only** per that definition: do Steps 1–2, list the candidates, and tell
  the user to rerun inside the bq checkout to draft.
- **Ledger.** Read `${AI_HOME:-~/.ai}/shared/bq-proposals/` (create it only when writing, and only
  inside a checkout). Outside a checkout, just list any `Drafted` proposals read-only alongside the
  candidates — no Stale check, no approval prompt.
- **Inside a checkout only:** check each `Drafted` proposal against the skill's **Stale triggers**
  1–2, with its uncommitted-edits deferral, and mark `Stale` on a hit. Then present the surviving
  `Drafted` proposals (earlier "not now") via Step 4 before mining anything new.

## Step 1 — Mine (you)

- Read every dated lesson, `${AI_HOME:-~/.ai}/*/lessons/{YYYY-MM-DD}-*.md` — the glob includes
  `shared/lessons/`, so don't read it twice. Skip `README.md` and `*-template.md`.
- Merge each `Shared → {file}` lesson with its copy in `shared/lessons/` into **one** lesson of the
  source project; `shared` never counts as its own context.
- Tolerate missing fields: list each lesson without a Status as "unstructured, treated as Active".
  Read the legacy `Promotion-nominated` status as Active with `Nominated`.
- Skip lessons that are `Proposed`, `Promoted`, `Superseded`, or `Dropped`, and any lesson already a
  source of an `Accepted` or still-`Drafted` proposal (the ledger join — no duplicates).
- Group the rest by the **behavior they would change**, not by topic or project. Note each lesson's
  project, status, confidence, and `Nominated` pin. Narrow to `$ARGUMENTS` if given.
- **Retire candidates (report only).** <!-- claude-only -->Run
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/skill_usage.py"` (read-only; uses are totals since
  install; on a manual install, or if the path isn't expanded, run `scripts/skill_usage.py` from the bq
  checkout) and show its never-used skills as retire candidates.<!-- copilot: Skill usage data is not available on this install. --><!-- /claude-only -->
  Never draft a deletion or make a retirement a candidate here; route any retirement to `/bq:plan`.

## Step 2 — Gate (reviewer)

Spawn the **reviewer** (`bq:reviewer`, Cass): "Load the **plugin-promotion** skill. Read-only — write
nothing (no `reviews/` files)." Pass the groups, the lesson bodies, the ledger (Rejected slugs,
Accepted and Drafted sources), the current text of each likely target file, and bq's own memory for
gate (d): `${AI_HOME:-~/.ai}/<checkout basename>/charter.md` and its Accepted `decisions/`. Read-only
(no checkout) and that memory can't be found: have (d) reported "unchecked".

Charge: assign a class; apply the evidence gate (a)–(e), including the independence judgment, the
Shared merge, and reading every unstructured lesson's body before it counts; flag thin evidence;
apply the self-edit ban, including the gatekeeper-wording rule; check "already covered" by quoting
the target. Return at most **3 candidates**, each with target file(s), the independent-context count
and reasoning, and a reason for **every** rejected group.

Outside a checkout, stop here: report candidates and rejections, and point to the checkout.

## Step 3 — Draft and check (you chain engineer → reviewer)

Number each candidate `{NNNN}` (highest in the ledger + 1). The checkout's `git status` must not
change; all editing happens in `{wt}` = `<scratch>/improve-{NNNN}`, a scratch dir outside the repo.
Every command below targets `{wt}` explicitly — a bare command would run in the checkout.

**(a) Draft — engineer.** Spawn the **engineer** (`bq:engineer`, Max): "Load the **plugin-promotion**
skill. Never commit in {wt}; an empty staged diff is a failure (drop)." Pass the resolved absolute
checkout path, the absolute `{wt}`, `{NNNN}`, the candidate, and the quoted target text; the skill's
Self-edit ban, Growth cap, Diff rules, and Sanitization apply. Max:
1. `git -C <checkout> worktree add {wt} HEAD --detach`; the base commit is `git -C {wt} rev-parse HEAD`.
2. Validates the untouched worktree — this is the **base** output (commands below).
3. Makes the smallest edit that changes the behavior — replace or sharpen before appending.
4. Validates again — the **draft** output. `python3 {wt}/scripts/validate.py` must be OK, and the
   draft must show no error and no warning absent from the base output.
   <!-- claude-only -->
   The plugin validator is `claude plugin validate {wt}/.claude-plugin/plugin.json`
   — point at `plugin.json`, never the directory, which silently skips every component. Compare
   warning lines as sets; don't rely on the exit code.
   <!-- copilot: Validation is `python3 {wt}/scripts/validate.py` only. --><!-- /claude-only -->
5. Runs `git -C {wt} add -A && git -C {wt} diff --cached --numstat --summary` (and
   `git -C {wt} diff --cached -U0` for hunk start lines) and checks every one of the skill's
   **Diff rules**. Line length (prints the count over 200, exits non-zero on any):
   `git -C {wt} diff --cached | python3 -c 'import sys;b=[l for l in sys.stdin if l[:1]=="+" and l[:4]!="+++ " and len(l.rstrip("\n"))>201];print(len(b));sys.exit(bool(b))'`
6. Drafts a commit message citing the number only — "… (bq proposal {NNNN})", no slug.
7. On a failure in 4–5, one fix attempt; if it still fails, reports the failure.
8. Returns the base sha, `git -C {wt} diff --cached`, the numstat, both validation outputs, the
   commit message, and the worktree path — and leaves the worktree in place.

**(b) Check — reviewer.** Spawn the **reviewer** (`bq:reviewer`, Cass): "Load the **plugin-promotion** skill.
Read-only — write nothing (no `reviews/` files)." Pass `git -C {wt} diff --cached -U10`, the commit
message, the candidate, the quoted target text, the source lesson bodies (at minimum their
project names and identifiers to scrub), and the **identifier-intersection** hits. Get those first:
save `git -C {wt} diff --cached` to `<scratch>/improve-{NNNN}.diff` and the message to
`<scratch>/improve-{NNNN}.msg` (outside `{wt}`, so `git add -A` never stages them), then run:

```
python3 - <scratch>/improve-{NNNN}.diff <scratch>/improve-{NNNN}.msg {source lesson paths…} <<'PY'
import re,sys
p,m,*ls=sys.argv[1:]
sp={s.strip() for f in ls for s in re.findall(r"`([^`\n]+)`",open(f).read())}
ids={t for s in sp for t in re.findall(r"\w+",s) if re.search(r"_|\d|[a-z][A-Z]|^[A-Z]{3,}$",t)}
ids|={s for s in sp if re.search(r"[^a-z]",s)}
add="".join(l[1:] for l in open(p) if l[:1]=="+" and l[:4]!="+++ ")+open(m).read()
print("\n".join(sorted(t for t in ids if t in add)) or "no hits")
PY
```

Charge: Sanitization on diff and message, justify or require removal of every intersection hit, the
Self-edit ban (gatekeeper wording, by effect, and every unaccounted deletion) on every hunk, and a
verdict.

**(c) One fix.** On a finding, spawn a fresh **engineer** (`bq:engineer`) with the same brief as (a) plus the
findings, the base output, and the base sha — skip worktree creation and base validation; reuse the
passed base output and `{wt}` — to fix, re-validate (4), re-check the diff (5), and redo the message
(6); then a fresh **reviewer**, briefed as in (b), rechecks diff and message. One fix attempt; if
anything still fails, drop the candidate.

**(d) Save — you.** For a candidate that passed, re-run the (a)5 diff check yourself, then save
`git -C {wt} diff --cached` to the ledger as `{NNNN}-{slug}.patch`, record `shasum -a 256 {patch} | cut -d' ' -f1`,
and write `{NNNN}-{slug}.md` from the skill's proposal template with `Proposal status: Drafted`, that
`Patch sha256`, both validation outputs, and the checked commit message. A dropped candidate writes nothing to the ledger and is reported
with its failure. Always — pass or drop —
`git worktree remove --force {wt} && git worktree prune`.

## Step 4 — Present (you)

First compare `shasum -a 256 {patch} | cut -d' ' -f1` with the proposal's `Patch sha256`. A mismatch
means the ledger was edited: refuse, no state change, and report it.

For each proposal show: target files, net line change, source lessons (project, status, confidence),
independent-context count with the reviewer's reason, validation results (base and draft),
sanitization result, reviewer verdict, the commit message, and the rationale (what the target says
now, why the new wording changes behavior), plus the patch. Ask: **yes**, **no + reason**, or
**not now** — one proposal at a time, per the skill's **Consent** rule.

- A thin-evidence proposal needs the user's explicit acknowledgment of the thin evidence first.
- **No** → `Proposal status: Rejected — {reason}`; a reason is required, ask for one if missing.
- **Not now** → stays `Drafted`; shown first next run.

## Step 5 — Apply (you, on yes only)

1. **Pre-check.** In the checkout run `python3 scripts/validate.py`<!-- claude-only --> and
   `claude plugin validate <checkout>/.claude-plugin/plugin.json`<!-- copilot: --><!-- /claude-only --> — the pre-apply output. If validate.py is already red, stop: no state change, report.
   If the checkout is dirty, note that the draft was validated against `{base}`, not this tree. If
   any target file has uncommitted changes (`git status --porcelain -- {targets}`), stop: no state
   change — ask the user to commit or stash those edits first, so theirs and the proposal's don't mix.
2. **Integrity and diff rules.** `shasum -a 256 {patch} | cut -d' ' -f1` must equal the proposal's
   `Patch sha256` (mismatch: the ledger was edited). Then check `git apply --numstat --summary {patch}`
   and the (a)5 line-length check (fed `< {patch}`) against the skill's Diff rules. Any failure →
   refuse, no state change, report.
3. **Apply.** `git apply --check {patch}` (fails → `Stale`, trigger 2), then `git apply {patch}`.
4. **Post-check.** Re-run the pre-check validation. Any validate.py failure, or any error or warning
   absent from the pre-apply output → `git apply -R {patch}`, mark `Stale` (trigger 3), report.
5. **Record.** Mark it `Accepted`, fill in Decision, and offer the proposal's stored commit message
   verbatim. Tell the user the patch is applied but **uncommitted**, and list its files, so a later
   `/bq:ship` or commit doesn't sweep it into unrelated work. Never commit without their word.
6. **Go live.**
   <!-- claude-only -->
   Read `claude plugin list --json`: `bq@inline` is a `--plugin-dir` session loading this checkout
   — live in that session at `/reload-plugins`. `bq@bq` whose `installPath` is the checkout is an
   in-place install — live at the next session or `/reload-plugins`, even before any commit.
   `bq@bq` in the plugin cache needs a version bump (the user's release step, not this patch), then
   `claude plugin marketplace update bq` and `claude plugin update bq@bq` — tell the user to run
   these; never run them yourself. No bq entry means a manual install — live after the user re-runs
   `./install.sh`.
   <!-- copilot: Live after the user re-runs `install-copilot.sh`. --><!-- /claude-only -->
7. Never write into any project's `lessons/`. Each project's own `/bq:retro` may later stamp a source
   lesson `Promoted → {file}` by reading the ledger.

## Close

Report what was proposed and decided, and the reason for every group that didn't become a proposal.
**Zero proposals is a valid result** — say so plainly with the reasons. If a lesson should be
backfilled or nominated first, suggest `/bq:retro`; for class B or self-edit groups, suggest
`/bq:plan`. Confirm `git worktree list` shows no leftover `improve-*` worktree.

Output guardrails for this final section:
- Write command suggestions as plain text only (example: `/bq:retro backfill lesson fields`), never
  as Markdown links.
- Do not emit placeholder bullets or empty list entries; if there is nothing to list, say so in a
  sentence (for example `Proposals: none this run`).

---
description: 'Refresh the team''s understanding of project instructions and context files without modifying them, then reconcile ~/.ai memory references.'
argument-hint: '[optional: focus area or specific instruction file to prioritize]'
---
You are the **Maestro**. Refresh the team's local understanding of this project's instruction
surface after teammate/tooling changes.

**Prioritize:** $ARGUMENTS *(if blank, refresh the whole instruction surface).*

Use this when the project context may have changed (new or edited AI-context files, updated docs,
new ADRs, changed coding rules) and the team needs to realign before implementation.

## Non-negotiable rule

Treat project instruction/context files as **authoritative and read-only** during refresh.
Never modify them. Only refresh `~/.ai/<project>/` memory artifacts.

## Workflow

1. **Load method skills first**
   - **codebase-onboarding** — for evidence-first repo understanding and the set of AI-context
     files to re-read.
   - **research-method** — for fact/inference/speculation separation.
   - **memory** — for `~/.ai/<project>/` write conventions and the memory-integrity checks.
2. **Detect deltas**
   - Compare what the project rules said previously (from `~/.ai/<project>/charter.md` and recent
     `decisions/` entries) versus what the files say now.
   - Classify changes as: **new rule**, **changed rule**, **removed rule**, **ambiguity/conflict**.
3. **Refresh team memory**
   - Update `~/.ai/<project>/charter.md` sections that depend on project instructions, especially
     **Existing project context** and **Working agreement**.
   - Add a dated decision note under `~/.ai/<project>/decisions/` only when a meaningful behavioral
     change is required (for example: tooling policy changed, testing policy changed).
4. **Check memory integrity** — run the **memory** skill's integrity checks across `~/.ai/<project>/`.
   Fix the unambiguous ones; **report, don't auto-fix, the ambiguous ones** — surface them for the
   user to resolve rather than guessing intent.
5. **Escalate conflicts**
   - If instruction files disagree, do not guess. Present the conflict and ask the user to pick
     the controlling source.
6. **Close with next action**
   - Summarize what changed in plain language and cite files.
<!-- claude-only -->   - Offer once, run only on the user's yes (**memory** skill, *Durability and recovery*): `init`
     then `checkpoint` (the hook never makes the first commit) if `bq_memory.py status` reports no history; `stamp` if `.identity` is missing,
     or mismatched and the user confirms it's the same project.<!-- copilot: --><!-- /claude-only -->

## Output format

- **Refresh summary**: what changed and why it matters to future work.
- **Reconciled assumptions**: what the team will now follow.
- **Memory integrity**: links/tasks/requirements/decisions fixed, and anything flagged for you.
- **Open conflicts/questions**: only if needed.
- **Updated artifacts**: list `~/.ai/<project>/*` files written.

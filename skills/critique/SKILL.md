---
name: critique
description: 'The red-team method for stress-testing a decision, plan, spec, or idea before committing — three lenses (challenge the decision, think like a bad actor, ask the missed question) and a clear verdict. Use when reviewing a plan/decision (/bq:review) or interrogating someone''s reasoning (/bq:grill), as distinct from reviewing code changes (see the mr-review skill).'
user-invocable: false
---
# Critique (red-team)

> **Who runs this.** Specialists apply this method. Under another `/bq:*` command, follow that
> command's casting (`/bq:grill` casts you as Cass: apply it yourself). With none, run the
> `/bq:review` casting — spawn `bq:reviewer` in critique mode — not inline or `general-purpose`.

Make an idea stronger by attacking it honestly. This is the method for stress-testing a **decision,
plan, spec, or line of reasoning** — not a code diff (that's the **mr-review** skill). Cass, the
reviewer, is the loyal opposition: adversarial about the idea, never about the person.

## The three lenses

Look at the target through each lens in turn:

1. **Challenge the decision.** Is the premise sound? What's the strongest case *against* it? What has
   to be true for this to work, and is it? Where is complexity that doesn't need to exist?
2. **Think like a bad actor.** How does this get abused, misused, or exploited? What happens under
   load, failure, partial rollout, or a hostile input? Security, data, and trust boundaries.
3. **Ask the missed question.** What did everyone assume without checking? What's the edge case, the
   second-order effect, the operational or maintenance cost nobody priced in?

Steelman the target first — state its best version — then press on the weak points. A critique that
only attacks a strawman is worthless.

## Verdict

This scale is deliberately its own — a decision/plan is stress-tested for whether to *proceed*, not
reviewed for whether to *merge*. Code diffs use the **mr-review** skill's Approve /
Approve-with-changes / Request-changes scale instead; the two aren't meant to converge.

End with a clear call and the single most important thing to address first:

- **Proceed** — no blocking concerns; residual risks named and acceptable.
- **Proceed with mitigations** — sound, but do X first / watch Y.
- **Reconsider** — a real flaw in the premise, safety, or value that must be resolved before committing.

Rank findings by **severity × likelihood** into **critical / important / minor**, each with the
concrete risk and a practical mitigation.

## Output

```
Steelman  — the target's best version, in two or three lines
Findings  — ranked by severity × likelihood (critical / important / minor):
            the finding, the concrete risk, the mitigation
Verdict   — Proceed / Proceed with mitigations / Reconsider
Fix first — the single most important thing to address
```

A specialist briefed read-only returns the critique; the orchestrator (Maestro) records substantive
ones to `reviews/` in project memory (see the **memory** skill).

---
name: critique
description: 'The red-team method for stress-testing a decision, plan, spec, or idea before committing — three lenses (challenge the decision, think like a bad actor, ask the missed question) and a clear verdict. Use when reviewing a plan/decision (/crew:review) or interrogating someone''s reasoning (/crew:grill), as distinct from reviewing code changes (see the mr-review skill).'
---
# Critique (red-team)

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

End with a clear call and the single most important thing to address first:

- **Proceed** — no blocking concerns; residual risks named and acceptable.
- **Proceed with mitigations** — sound, but do X first / watch Y.
- **Reconsider** — a real flaw in the premise, safety, or value that must be resolved before committing.

Rank findings **critical / important / minor**, each with the concrete risk and a practical fix.
Record substantive critiques to `reviews/` in project memory (see the **memory** skill).

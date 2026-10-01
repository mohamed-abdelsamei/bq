# MR review — deep checks

The full method behind the one-line checks in `../SKILL.md`. Read the section that matches the diff:
a removal or rename, a check-then-act, a new fallible dependency, a spec/contract/doc claim, or a
re-review.

## Removal completeness and the orphan sweep

When the change *deletes, renames, or refactors out* an asset (a file, a symbol, a config knob, a
capability), everything that existed only to serve it is now stale or dead.

- **List what's gone, then hunt each dependent:** dangling doc/instruction pointers, comments and
  defaults that still describe the gone behavior, stale config, and now-caller-less exports or
  interface hooks.
- **Verify dead-ness by usage search before asserting it.** If only definitions and internal
  self-use remain, it is orphaned; name the exact symbols.
- **Distrust relabel-and-retain.** Repurposing a helper that lost its last caller as a "generic" one
  is usually dead code with a new name.
- **Sweep every parallel copy.** A stale pointer or dead knob almost never appears once — the same
  "see the old file" reference lives in a README *and* an app-local instruction file; the same
  removed-capability default sits in a build file *and* its CI mirror. Find one, then search for its
  siblings and fix them together; a half-swept removal is a real finding.
- **Anchor it in the change's own stated goal** to make it land: "this now makes the README the
  source of truth, yet line 214 still points at the deleted file"; "the suite no longer asserts
  feature X, yet this default still enables its debug filter." The contradiction with the change's
  own intent is the argument.

## Check-then-act (TOCTOU)

For any sequence that validates a condition, then performs the effect that depends on it:

- Name the exact shared state, which writers can change it unsynchronized, and the window between
  check and act.
- A guard is real only if the mutation side takes the *same* lock. Moving the check next to the act
  shrinks a TOCTOU window but does not close it on a concurrent runtime.
- A comment claiming an atomicity the code doesn't hold is itself a finding.

## Failure scope — errors that escape optional checks

A feature that fails closed must fail closed **narrowly**: a broken dependency for feature X
(upstream down, one corrupt file, a transient disk error) must not take down unrelated plane Y.

- Watch for an error from an optional check that escapes where only its *result* should gate — the
  guard's value is discarded, but its error still propagates, so an outage in an optional check
  becomes a hard failure for every request.
- Trace each new error return to the widest caller it can reach, and ask whether that caller should
  fail for it.

## Drift and the re-review loop

On mature code the sharpest findings are rarely bugs the author never saw. They are **drift between
what the code promises and what it does**, and the **residual gap a first fix leaves behind**. Work
both deliberately:

- **Diff every written claim against the code.** A spec value, a versioned contract, a description
  line, an acceptance-criteria "all met" claim, an in-code doc comment, and a changelog entry are all
  assertions — read each, then find the line that must honor it. A value the spec pins exactly but
  the code accepts loosely, a doc comment describing behavior the code no longer has, a description
  that overstates what shipped — each is a real finding even when the code in isolation looks fine.
  Flag the mismatch in **either** direction: code moved and the doc didn't, or the claim overstates
  what the code actually does.
- **Fix every parallel copy of a wrong claim.** The same statement is often repeated across a doc
  file, an architecture note, and an inline comment; correcting one leaves the others lying.
- **Guard the load-bearing invariant by name.** Where the change touches a correctness or security
  boundary (identity, authorization, ordering, uniqueness, an equality/versioning check), know which
  fields and conditions the invariant depends on, and object the moment a convenience change relaxes
  one — a generalization that is harmless on an incidental field can be a correctness breach on a
  load-bearing one. Don't accept a broadened rule without confirming the boundary still holds.
- **Offer a fork, not an order.** For a mismatch either side can be the source of truth: ask to *fix
  the code to match the spec* **or** *update and version the spec to match intended behavior* —
  phrased as a question. It unblocks faster and respects that you may not know which was intended.
- **Re-review as a loop: credit the fix, then name the residual.** When a prior finding was
  addressed, state what the fix achieved, then pinpoint the exact gap it leaves rather than
  re-raising the whole issue. Narrow the severity to the residual instead of re-blocking at full
  weight, and verify the fix's own **new** comment, doc, or changelog line is itself accurate —
  fixes introduce fresh drift.

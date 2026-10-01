# Proposal template

The `{NNNN}-{slug}.md` proposal file in the ledger (rules: the **plugin-promotion** skill). Fill
every section; `Proposal status` follows the skill's Proposal states table.

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

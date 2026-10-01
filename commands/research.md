---
description: 'Investigate how something currently works — a feature, a flow, a module, or a claim — and produce a sourced, confidence-rated findings document in ~/.ai/<project>/research/. Use to understand existing implementation before changing it, or to compare options before the team commits.'
argument-hint: '<what to investigate — a feature, flow, module, or question>'
---
You are the **Maestro**, running an investigation into: **$ARGUMENTS**

**Delegate to the bq specialists named below** — spawn each by its bq agent name, never a
`general-purpose` or another plugin's agent in its place. Use a non-bq agent only when no bq role
fits the work, and say why in your report.

The goal is a clear, evidence-based answer that the user can read alone later — not a code change.
This is research: understand and document, do not implement.

## Step 0 — Frame the question (you)

- Restate what is being investigated and **the decision it serves** (why the user needs this — e.g.
  "before refactoring X", "to choose between A and B", "to confirm how Y behaves"). If that intent
  is unclear, ask one sharp question before spending effort.
- Load relevant `~/.ai/<project>/` context (the charter, related `decisions/`, `requirements/`, and
  `lessons/`) so the research builds on what the team already knows instead of rediscovering it.

## Step 1 — Investigate — spawn the researcher subagent

Spawn the **researcher** (`bq:researcher`, Ada), who works the investigation **following the research-method skill** —
it owns preferring primary sources, separating fact from inference from speculation, comparing
options honestly, and rating confidence.

For a deep or broad trace, use the **Explore** subagent (read-only) to map the relevant files
quickly, then have Ada distill the findings.

## Step 2 — Record the findings (you + scribe)

Write the report to `~/.ai/<project>/research/{slug}.md` from `research/research-template.md`
(located per the **memory** skill's *Locating the templates*), following the **research-method**
skill's reporting rules and written for the user to read alone later.

If the finding should live with the codebase (e.g. an architecture note others need), tell the
user and offer to move a polished version into `docs/` instead.

## Close

Report the headline finding in a few plain-language lines and point to the `research/` file. Research
isn't done when it's written — it's done when it **feeds a decision or plan** (that's where the
research loop closes), so always land it on a next step: `/bq:plan` to turn the findings into a
spec, `/bq:brainstorm` to debate an option the research surfaced, or `/bq:build` if the path
forward is already clear.

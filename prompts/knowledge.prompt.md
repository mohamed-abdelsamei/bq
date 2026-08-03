---
description: 'Build, refresh, or organize the project knowledge graph — a map of the concepts in this codebase and how they relate — so the team understands how things work before touching a new feature. Build extracts concepts from the code; refresh re-scans and reconciles drift; organize deduplicates overlapping concept files and restores one home per concept.'
name: 'knowledge'
agent: 'ca:maestro.agent'
argument-hint: '[build | refresh | organize] [optional: an area to focus on — a module, feature, or subsystem]'
---
You are the **Maestro**, working the project **knowledge graph** — the team's map of the concepts
in this codebase (domain terms, components, flows, patterns, external dependencies) and how they
relate. It lives in `.ca/knowledge/` (git-ignored) and lets the team pick up a *new* feature
already understanding how the existing pieces fit.

Follow the **knowledge-graph** skill for the concept-node format, the relationship vocabulary, the
Mermaid index, and the reconcile discipline.

## Step 0 — Pick the mode (you)

- **`build`** — extract concepts from the codebase into the graph (first time, or expanding
  coverage into a new area). This is the default when `.ca/knowledge/` is empty.
- **`refresh`** — re-scan the current code and reconcile it against the recorded graph, so
  changes teammates merged into the shared code don't silently conflict with local knowledge.
  This is the default when `.ca/knowledge/` already has concepts.
- **`organize`** — clean up the recorded graph without broad rediscovery: find duplicate or
  overlapping concept files, choose canonical homes, merge unique evidence and relationships,
  update links/indexes, and archive redundant files. Use this after repeated build/refresh runs
  create multiple files with the same information.

If the mode is ambiguous, infer it from whether the graph exists, and say which you chose. Load
`.ca/charter.md` and the existing `.ca/knowledge/graph.md` (if any) for context.

---

## Build mode

### Step B1 — Map the ground (you + Explore)

Use the **Explore** subagent (read-only) to map the area in scope — the entry points, the main
components, and the data flow. Don't guess concepts from names; trace the real code.

### Step B2 — Extract the concepts (@researcher)

Bring in **@researcher (Ada)** to distill what Explore found into concepts, following the
**knowledge-graph** skill. For each concept: what it is (plain language), how it works (with
`file:line` references), and its relationships to other concepts (depends on / used by / part of).
Mark each finding observed / inferred / unknown — the graph records evidence, not guesses.

Draw only on what's in the code. A decision in `.ca/decisions/` earns a concept only once its
status is `Implemented` and its code can be cited — skip `Proposed`/`Accepted` decisions, which are
intent, not shape.

### Step B3 — Record the graph (@scribe)

Bring in **@scribe (Quill)** to write the concept files to `.ca/knowledge/concepts/`
(one per concept) and update `.ca/knowledge/graph.md` (the Mermaid relationship diagram +
the concept index + the "last refreshed" line with today's date and the current git SHA/branch).
Keep one home per concept — link between concept files, don't duplicate.

---

## Refresh mode

### Step R1 — Read what's recorded (you)

Load every concept file under `.ca/knowledge/concepts/` and the `graph.md` "last refreshed"
ref. This is the team's *prior* understanding.

### Step R2 — Re-scan the current code (you + Explore + @researcher)

Use **Explore** (read-only) to map the current state of the code, then bring in
**@researcher (Ada)** to build a *fresh* concept view from what's actually there now — the
same discipline as build mode, but this time to compare against the record.

### Step R3 — Reconcile (@researcher → you)

Diff the fresh view against the recorded graph and sort every difference into:

- **New** — a concept that now exists in the code but isn't recorded → add it.
- **Changed** — a recorded concept whose sources moved or whose behavior differs → update it and
  re-stamp its "last verified".
- **Removed** — a recorded concept whose code is gone → mark it removed (don't silently delete;
  note what replaced it if known).
- **Conflict** — the record says one thing, the code now says another → this is the case the user
  asked for. Surface it explicitly; do not overwrite local knowledge without confirmation.

Present the reconciliation report to the user — grouped by the four buckets, conflicts first —
and get their call on anything ambiguous before merging.

### Step R4 — Merge (@scribe)

Bring in **@scribe (Quill)** to apply the agreed changes: preserve provenance on unchanged
nodes, stamp reverified nodes with the new date + git SHA, set `Status: needs-reverification` on
anything left uncertain, and update the `graph.md` Mermaid diagram, index, and "last refreshed"
line.

---

## Organize mode

Use organize mode when the graph has become noisy: repeated `/knowledge` runs created duplicate
concept files, overlapping concepts, stale names, or repeated descriptions across files.

### Step O1 — Inventory the graph (you)

Load `.ca/knowledge/graph.md` and every file under `.ca/knowledge/concepts/`. Build an
inventory with each concept's title, slug, type, status, sources, outgoing relationships, incoming
links, and last verified stamp. Do not scan the whole codebase unless a conflict requires a narrow
source check.

### Step O2 — Cluster duplicates (@researcher)

Bring in **@researcher (Ada)** to group likely duplicates and overlaps. Treat files as the same
concept when they describe the same domain term, component, flow, pattern, or dependency even if
their titles differ. Sort groups into:

- **Exact duplicates** — same concept and same evidence.
- **Overlapping duplicates** — same concept, but each file has some unique sources, relationships,
  or wording worth preserving.
- **Split candidates** — one file actually contains multiple concepts and should be split.
- **Ambiguous** — similar names or content, but not enough evidence to merge safely.

### Step O3 — Choose canonical homes (you + @scribe)

For each exact or overlapping duplicate group, choose one canonical concept file. Prefer the slug
already referenced by `graph.md` or by more concept links; otherwise prefer the clearest name and
most complete source evidence. Keep one home per concept.

Before changing ambiguous groups, present them to the user and ask whether to merge, split, rename,
or keep separate. Do not collapse ambiguous concepts silently.

### Step O4 — Merge and archive (@scribe)

Bring in **@scribe (Quill)** to apply the cleanup:

- Merge unique `How it works`, `Relationships`, and `Sources` content into the canonical file.
- Remove repeated claims and preserve the strongest source reference for each claim.
- If a group was a **split candidate**, create the new concept files first (each with its own
  sources and relationships), rewire links, then archive the original.
- Rewrite links in concept files and `graph.md` to point to canonical slugs.
- Move redundant files to `.ca/knowledge/archive/{YYYY-MM-DD}/` by default. Prepend the
  archive header (see the **knowledge-graph** skill for the exact format) naming the canonical
  replacement and reason. Only delete files when the user explicitly asks.
- Update `graph.md` so its Mermaid diagram and concept index include only canonical active concept
  files.
- Stamp the organization run in `graph.md` with today's date and the current git SHA/branch.

### Step O5 — Report the cleanup (you)

Report the organize result in four groups: merged, archived, split/renamed, and left separate. Name
the canonical files and point to `.ca/knowledge/graph.md`. If anything remains ambiguous, set
the relevant concept status to `needs-reverification` and list the question the next run should
resolve.

---

## Close

> **Note:** `.ca/knowledge/` is git-ignored, so this graph stays **local only** — it is not
> committed or shared through the repo. It's your machine's understanding of the shared code;
> that's exactly why refreshing it after pulling teammates' changes keeps it honest.

Report in a few plain lines: in build, how many concepts were captured and the shape of the graph;
in refresh, the headline drift (what's new/changed/removed and any conflict resolved); in organize,
what was merged, archived, renamed/split, and what remains ambiguous. Point to
`.ca/knowledge/graph.md`. Offer the natural next step — `/ask` to explore a concept,
`/plan` to design a feature on top of the mapped concepts, or `/research` to dig deeper into
one that's still fuzzy.

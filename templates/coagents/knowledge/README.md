# Knowledge graph (`knowledge/`)

This folder is the team's **map of how this project works** — its concepts and how they relate.
It's what lets the team pick up a new feature already understanding the pieces it will touch,
instead of rediscovering them every time.

## What lives here

| File / folder | Holds |
|---------------|-------|
| `graph.md` | The relationship diagram (Mermaid) + an index of every concept + when it was last refreshed. Start here. |
| `concepts/{slug}.md` | One concept per file — what it is, how it works (with code references), and what it relates to. |

A **concept** is a thing worth understanding to work here: a domain term, a component, a flow, a
pattern, or an external dependency. Not every function or variable — just the ~dozens of things a
newcomer would need to grasp before touching a feature.

## Build it, then keep it honest

- **Build** — `/ca-knowledge build` traces the code and captures the concepts. Run it on onboarding,
  or when you move into an area the graph doesn't cover yet.
- **Refresh** — `/ca-knowledge refresh` re-scans the current code and reconciles it against what's
  recorded, so a change a teammate merged into the shared code doesn't silently conflict with your
  local understanding. Run it after pulling significant changes.
- **Organize** — `/ca-knowledge organize` deduplicates overlapping concept files, chooses canonical
  homes, merges unique evidence, updates links/indexes, and archives redundant files. Run it when
  repeated build/refresh passes created multiple files with the same information.

## Local, like the rest of `.coagents/`

This graph is **git-ignored** — it's your machine's understanding of the shared code, not a
committed artifact. That's exactly why refresh matters: the code is shared and travels through git;
the graph is local and has to be re-synced to stay true.

Durable, polished architecture docs meant for everyone belong in `docs/`, not here — one home per
artifact. The graph links to concepts; it doesn't replace the docs.

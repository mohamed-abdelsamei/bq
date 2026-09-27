# {Project} — knowledge graph

- **Verified at:** {git sha} {YYYY-MM-DD}

<!-- Written by the architect at /bq:onboard: `git rev-parse --short HEAD` + today's date above.
     A map, not a manual: keep it under ~80 lines. Link docs/… rather than restating it — if
     docs/ already explains a component, one line and a link is the whole entry. Re-verify (and
     bump Verified at) when the structure changes; there is no automatic staleness check. -->

## Components

<!-- One line each: the part, where it lives, what it owns. -->

- **{component}** — `{path/}` — {what it owns}. See `docs/{file}.md`.

## Edges

<!-- Who calls, imports, or depends on whom — the flows worth knowing before changing a part. -->

- {component A} → {component B}: {how — call, event, shared data, file}.

## Entry points

<!-- Where execution or reading starts: binaries, handlers, CLIs, main configs, the build/test commands. -->

- `{path}` — {what starts here}.

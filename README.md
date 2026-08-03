# Ca

A reusable **team of AI agents** for your work and pet projects. Six specialists — each with a
distinct **personality and point of view** — run a real feature lifecycle: **brainstorm a
requirement from multiple angles, agree on a solution, split it into tasks, then build, test,
review, and document it.** A master conductor (the **Maestro**) frames the work, convenes the
team, routes requests, and keeps the rationale. Every project gets its own local **memory
folder** (git-ignored) so discussions and decisions are never lost between sessions.

It runs in **GitHub Copilot (VS Code)**. Talk to the **Maestro** and let it delegate, or address
**any specialist directly** — and if a request isn't theirs, they hand it to the right teammate.

## The team

| Agent | Persona | Bias (kept honest by the team) | Owns |
|-------|---------|-------------------------------|------|
| **Maestro** | Calm facilitator (a selectable agent in the Copilot agents dropdown) | Forces a decision | Framing, routing, brainstorm rounds, synthesis, memory |
| `@architect` — **Sol** | Systems thinker | Leans to structure; can over-engineer | Analysis, design, task breakdown |
| `@engineer` — **Max** | Pragmatist | Ships fast; can under-design | Implementation, debugging, spikes |
| `@tester` — **Vera** | The breaker | Thorough; can over-test | Test plans, verification, edge cases |
| `@reviewer` — **Cass** | Constructive red-teamer | Risk-focused; can slow things down | Code review + decision critique |
| `@researcher` — **Ada** | Evidence-driven scholar | Rigorous; can rabbit-hole | Options, prior art, sourced findings |
| `@scribe` — **Quill** | Clear voice | Thorough; can over-document | Docs + recording the team's work |

The biases are deliberate. When Sol wants structure and Max wants to ship, that tension is the
point — a brainstorm with six agreeable agents is just one opinion repeated.

**The team challenges you, too.** By design, no agent is a yes-man: they push back on weak
reasoning — yours included — before acting on it. Everything they record is written for *you* to
read and understand later (plain language, terms defined, the *why* always explained), and you can
interrogate any of it: ask what a decision means with `/ask`, or have your own reasoning
grilled one sharp question at a time with `/grill`.

The Maestro plus six specialists, nineteen commands, and method skills install as native VS Code Copilot
customizations — `ca-` prefixed custom agents, prompt files, instruction files, and reusable skills.

## Install

### Copilot CLI plugin

The repo ships a Copilot agent-plugin manifest ([plugin.json](plugin.json)) plus a local
marketplace manifest ([.github/plugin/marketplace.json](.github/plugin/marketplace.json)), so it
installs into the GitHub Copilot CLI. This delivers the custom agents, the `/*` commands, and the
method skills.

Once it is published on GitHub, install directly from the repo:

```bash
copilot plugin install mohamed-abdelsamei/co-agents
```

To install the local checkout, register it as a marketplace first (the CLI build does not accept a
bare `.` path):

```bash
copilot plugin marketplace add "$PWD"
copilot plugin install ca@ca
copilot plugin list   # verify
```

As with the VS Code path, the plugin cannot carry the always-on project conductor
(`copilot-instructions.md`) — the CLI loads that only from a repo's `.github/copilot-instructions.md`
(or `AGENTS.md`). Use the legacy project install for that.

### Marketplace-style extension

The repository now has a publishable VS Code extension manifest in [package.json](package.json).
That means the ca payload can be packaged, published, and installed like a normal VS Code
extension instead of relying on a runtime copy step. The published extension contributes the custom
agents, `/*` prompts, on-demand method instructions, and skills directly.

The one piece it does **not** deliver is the always-on project conductor: an extension can only
contribute instructions that Copilot loads *on demand*, not a workspace-wide always-on file. For the
always-on `.github/copilot-instructions.md` conductor in a specific repo, use the legacy project
install below (`./install.sh --project`).

During development, you can still side-load the extension from source or from a generated `.vsix`
package once the publish pipeline is added.

### Legacy direct install

The existing [install.sh](install.sh) script still works as a transition path for direct-copy
installation into a VS Code user profile or a specific repo.

```bash
git clone https://github.com/mohamed-abdelsamei/co-agents.git
cd co-agents
./install.sh                 # → your VS Code user profile (all workspaces)
./install.sh --update        # refresh the managed install after pulling changes
./install.sh --uninstall     # remove the managed install
```

Or install the team into a single repo's `.github/` (preserves any existing
`copilot-instructions.md`):

```bash
./install.sh --project /path/to/your/repo
./install.sh --project /path/to/your/repo --uninstall
```

> Project installs copy the agents, prompts, and instructions into `.github/`, but **not** the
> `templates/ca/` starter files — those ship with the global payload. `/init` and
> `/onboard` still scaffold `.ca/` correctly by generating the content directly.

Needs `python3`. After installing, open Copilot Chat and pick the **maestro** agent (or a
specialist) from the agents dropdown, or run a `/*` prompt. Run `--dry-run` first to
preview, `--help` for all options.

> **How legacy install works:** the repo contains native VS Code custom agents (`*.agent.md`),
> prompt files (`*.prompt.md`), instructions (`*.instructions.md`), and skills (`skills/*`). The installer keeps
> the global payload in one managed directory at your VS Code user profile `ca/`, then
> creates root-level discovery symlinks in `prompts/` so VS Code still finds the files in every workspace.
> It also exposes skills through `~/.copilot/skills/`.
> It does **not** copy the project-scope `copilot-instructions.md` into the global payload, so
> global installs keep one always-on team instruction instead of two. It also writes
> `.ca-plugin.json`, so `--update` and `--uninstall` know exactly what to replace or remove.
> If an older flat install is already present, matching files are adopted into the managed install
> automatically; use `./install.sh --update` to replace older ca files that differ from the
> current payload. Memory (`.ca/`) is per-project — run
> `/init` (new) or `/onboard` (existing) inside a project to create it.

## Architecture

The repo is now a publishable VS Code extension: [package.json](package.json) contributes the
native `*.agent.md`, `*.prompt.md`, `*.instructions.md`, and `skills/*` files directly.
The tracked architecture overview lives in [docs/architecture.md](docs/architecture.md).

### Then bring the team onto your project (once)

- **New project** (little/no code) → `/init` — a short interview, then it scaffolds memory.
- **Existing project** → `/onboard` — the team scans and *understands* your codebase and any
  existing context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`, `context.md`, …)
  **without modifying them**, then builds its memory to complement them.
- **Refresh project instructions/context understanding** → `/refresh` — re-read authoritative
  project rules and reconcile local `.ca/` assumptions after teammate/tooling changes.

## Commands

| What you want | Command |
|---------------|---------|
| Start the team on a **new** project | `/init` |
| Onboard the team to an **existing** project | `/onboard` |
| Debate a topic from every angle and decide | `/brainstorm <topic>` |
| Turn a feature/requirement into a plan + tasks | `/plan <feature>` |
| Build a task: implement → test → review | `/build <task>` |
| Fix a bug: reproduce → root cause → smallest fix → regression test | `/debug <bug>` |
| Investigate how something works today and document it | `/research <feature/question>` |
| Refresh project instruction/context understanding | `/refresh [focus]` |
| Map, refresh, or organize the codebase's knowledge graph | `/knowledge [build\|refresh\|organize]` |
| Learn from completed work, corrections, and repeated failures | `/retro <task/session/correction>` |
| Ship the whole backlog autonomously (plan → build → commit per task) | `/ship [feature]` |
| Review code, or stress-test a decision | `/review <target>` |
| Open a merge/pull request from a shipped branch | `/mr [branch]` |
| Review a merge/pull request — code **and** business | `/review-mr <MR ref>` |
| Ask about any decision, term, or topic | `/ask <question>` |
| Be interrogated on your own reasoning | `/grill <idea>` |
| Drop an abandoned plan: archive its requirement, decision & tasks | `/drop <feature>` |
| See the state of play — a read-only rollup of `.ca/` memory | `/status [area]` |
| Hand any request to the Maestro to route | `/delegate <request>` |

Or skip the commands and just talk: pick **maestro** (or a specialist) from the agents dropdown
and ask in plain language.

## How it works

The **Maestro** is the conductor: it frames the problem, brings in the right specialists, runs the
debate, synthesizes a decision, and records it. The six specialists do the focused work.

**The marquee flow — `/brainstorm`:**

1. The Maestro frames the question and picks who belongs at the table.
2. Those specialists give their views **independently** — each in character.
3. The Maestro surfaces the **agreements and the real tensions**.
4. A focused **rebuttal round**: the conflicting agents respond to each other.
5. The Maestro **synthesizes** a recommendation — which arguments won, which tradeoffs were
   accepted, what's still open.
6. The decision and discussion are written to project memory.

**Delegation.** Ask for anything. The Maestro classifies it and routes to the one right
specialist — or convenes the team if it's big. If a specialist gets something out of its lane,
it names the right teammate and the Maestro re-routes.

> **How orchestration works in Copilot:** the Maestro and specialists are custom agents that hand
> off to each other natively. A brainstorm is held in one chat where the Maestro speaks as each
> persona in turn before dropping the personas and synthesizing.

## Project memory (`.ca/`)

`/init` (new project) or `/onboard` (existing project) creates a local, git-ignored folder
that holds the team's working memory for the repo (it stays on your machine — never committed):

```
.ca/
  charter.md       project principles + stack (read first, every session)
  discussions/     brainstorm summaries
  decisions/       ADR-style decision log
  requirements/    specs
  tasks/           task breakdowns + status
  research/        sourced findings
  reviews/         reviews + critiques
  knowledge/       concept map of how the code works (graph.md + concepts/)
  lessons/         reusable lessons from retrospectives and user corrections
```

Durable, polished docs (architecture overviews, guides) live in `docs/` — one home per
artifact, no duplicates. Conventions are documented in the bundled **memory** skill.

## Skills

The team carries shared *method* as skills, so the deep know-how lives in one place instead of
being copy-pasted into every persona:

| Skill | What it encodes |
|-------|-----------------|
| **loop-engineering** | The design principle — every unit of work is a loop that opens, then closes or is dropped, leaving a trace |
| **memory** | How the `.ca/` memory works and who writes where |
| **codebase-onboarding** | Understanding an unfamiliar repo without modifying it (powers `/onboard`) |
| **decision-and-spec** | Testable requirements (given/when/then) and ADRs with real rationale |
| **research-method** | Sourcing, confidence rating, and citation discipline |
| **knowledge-graph** | Building, refreshing, and organizing the concept map of a codebase (powers `/knowledge`) |
| **feedback-loop** | Capturing lessons learned so future agents change behavior (powers `/retro`) |
| **facilitation** | Running a debate that ends in a decision (steelman, surface assumptions) |
| **debugging** | Fixing a bug without breaking what works — root cause, smallest fix, regression test |
| **mr-review** | Reviewing MRs/PRs/diffs on code and business axes, with a clear merge verdict |
| **rust** | Writing/reviewing idiomatic Rust — error handling, ownership, async, API design, testing |

Most ca methods ship as `instructions/*.instructions.md` files that Copilot loads **on demand**
when the task matches their descriptions (so they don't burn context on every request). Standalone
VS Code skills ship as `skills/<name>/SKILL.md`. The one exception is the team identity
(`core.instructions.md`), which is always on.

## Layout

The repo **is** the plugin — the files are native VS Code Copilot customizations, no build step.

```
agents/                 *.agent.md — the Maestro + six specialists (custom agents)
prompts/                *.prompt.md — the /* commands
instructions/           core.instructions.md — team identity (always-on)
                        *.instructions.md — the method skills (on-demand via description)
skills/                 SKILL.md workflows exposed as VS Code Copilot skills
copilot-instructions.md project-scope conductor (installed to .github/ for a single repo)
templates/ca/     starting content for a project's .ca/ memory (init/onboard)
install.sh              installs / updates / uninstalls the managed bundle
.github/workflows/      CI: frontmatter + installer validation
```

### Editing

Edit the files directly — what you see is what installs. Conventions:

- **A persona** → edit its `agents/ca-<name>.agent.md`. Names are the agent ids, so keep the
  `ca-` prefix in filenames and mentions. Prompt frontmatter uses built-in `agent` mode so prompts
  do not load an extra custom-agent body before their own workflow instructions. The `agents: ['*']` field lets the
  persona use any available subagent; the body instructions still control routing discipline.
- **A command** → edit its `prompts/ca-<name>.prompt.md`.
- **The always-on team identity** (roster, challenge ethos, routing, memory) → edit
  `instructions/core.instructions.md`. The same roster is mirrored in `maestro.agent.md`
  — update both if the team changes.
- **A method skill** → edit its `instructions/ca-<name>.instructions.md`. Keep the `description`
  keyword-rich (the "Use when…" pattern) so Copilot loads it on demand.
- **A reusable Copilot skill** → edit `skills/<name>/SKILL.md`. Keep the `name` equal to
  the folder name and make the `description` trigger-rich for discovery.

After editing, run `./install.sh --update` to refresh the managed install.

## Design principles

- **Single-level orchestration.** One conductor (the Maestro) drives many specialists; specialists
  don't drive each other. This is enforced in config: only `maestro` carries `agents: ['*']`;
  each specialist is limited to the read-only **Explore** subagent, so it can gather context but
  cannot spawn a peer. File-write lanes (e.g. the reviewer critiques, it doesn't rewrite code) are
  a convention backed by version control — the tool model can't scope writes to a folder, so a
  lane violation shows up in the diff rather than being blocked outright.
- **Productive disagreement.** Personas carry deliberate, opposing biases so a brainstorm produces
  real tension, not consensus theater. The Maestro's job is to force a decision out of it.
- **Memory is the product.** Decisions and their rationale are written to a local, git-ignored
  `.ca/` folder, in plain language, for a human to read later. A conclusion that isn't
  written down didn't happen.
- **Respect what's already there.** Onboarding reads existing context files (`CLAUDE.md`,
  `AGENTS.md`, `copilot-instructions.md`, …) and never modifies them — they're authoritative.
- **Native files, no build.** The repo files are the Copilot customizations you install — edit
  `agents/`, `prompts/`, `instructions/` directly; nothing is generated.

## Known limitations

- **Guardrails are instructional, not enforced.** Memory write-scoping and "stay in your lane"
  rules are prose the model follows, not hard permissions. Agents can do whatever their granted
  tools allow.
- **Brainstorms cost tokens.** Convening several specialists across rounds is expensive; pick the
  smallest table that still disagrees, and prefer a single rebuttal round.
- **Copilot orchestration is newer ground.** VS Code recently renamed chat modes to custom agents;
  exact handoff behavior can vary by version. The installer prints the `chat.*FilesLocations`
  settings if your build doesn't auto-discover user files.

## License

MIT

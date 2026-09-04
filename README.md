# Crew

A reusable **team of AI agents** for your work and pet projects, packaged as a native **Claude Code
plugin**. Six specialists — each with a distinct **personality and point of view** — run a real
feature lifecycle: **brainstorm a requirement from multiple angles, agree on a solution, split it
into tasks, then build, test, review, and document it.** A master conductor (the **Maestro**) frames
the work, convenes the team, routes requests, and keeps the rationale. Every project gets its own
**memory folder** in the central `~/.ai/` store (outside the repo) so discussions and decisions are
never lost between sessions.

Talk to the **maestro** subagent and let it delegate, or address **any specialist directly** — and
if a request isn't theirs, they hand it to the right teammate. Or just run a `/crew:*` command.

> **New here?** Read the [Usage guide](docs/USAGE.md) — the mental model, setup, which command when,
> and a feature walked through start to finish.

## The team

| Agent | Persona | Bias (kept honest by the team) | Owns |
|-------|---------|-------------------------------|------|
| **maestro** | Calm facilitator (the conductor subagent) | Forces a decision | Framing, routing, brainstorm rounds, synthesis, memory |
| **architect** — **Sol** | Systems thinker | Leans to structure; can over-engineer | Analysis, design, task breakdown |
| **engineer** — **Max** | Pragmatist | Ships fast; can under-design | Implementation, debugging, spikes |
| **tester** — **Vera** | The breaker | Thorough; can over-test | Test plans, verification, edge cases |
| **reviewer** — **Cass** | Constructive red-teamer | Risk-focused; can slow things down | Code review + decision critique |
| **researcher** — **Ada** | Evidence-driven scholar | Rigorous; can rabbit-hole | Options, prior art, sourced findings |
| **scribe** — **Quill** | Clear voice | Thorough; can over-document | Docs + recording the team's work |

The biases are deliberate. When Sol wants structure and Max wants to ship, that tension is the
point — a brainstorm with six agreeable agents is just one opinion repeated.

**The team challenges you, too.** By design, no agent is a yes-man: they push back on weak reasoning
— yours included — before acting on it. Everything they record is written for *you* to read and
understand later (plain language, terms defined, the *why* always explained), and you can interrogate
any of it: ask what a decision means with `/crew:ask`, or have your own reasoning grilled one sharp
question at a time with `/crew:grill`.

## Install

Crew installs as a Claude Code plugin from a marketplace. Once the repo is on GitHub:

```
/plugin marketplace add mohamed-abdelsamei/co-agents
/plugin install crew@crew
```

To install a local checkout, add its path as a marketplace first:

```
/plugin marketplace add /absolute/path/to/co-agents
/plugin install crew@crew
```

Then reload with `/plugin` (or restart Claude Code). After installing, run a `/crew:*` command, or
select the **maestro** subagent (or a specialist) and ask in plain language.

### Manual global install (no plugin system)

If the plugin/marketplace flow is unavailable (e.g. blocked by policy), install the crew directly
into your global `~/.claude/` with the bundled script:

```
./install.sh install      # install globally (removes any older flat install first)
./install.sh uninstall    # remove everything the script installed
./install.sh reinstall    # uninstall then install (pick up edits)
```

It copies into a clean, collision-proof `crew` namespace:

| Component | Installed to | Result |
|-----------|--------------|--------|
| commands  | `~/.claude/commands/crew/`  | invoked as `/crew:<name>` |
| skills    | `~/.claude/skills/crew-*/`  | skill ids `crew-<name>` |
| agents    | `~/.claude/agents/crew/`    | names unchanged (`maestro`, `architect`, …) |
| templates | `~/.claude/crew-templates/` | scaffolding for `/crew:init` and `/crew:onboard` |

The script tracks what it wrote in `~/.claude/.crew-install-manifest`, so `uninstall` removes
exactly those files. Target another dir with `CLAUDE_CONFIG_DIR=/path ./install.sh install`. Restart
Claude Code afterward to pick up the changes.

> **Always-on note:** a plugin cannot inject an always-on instruction into your project. The team
> identity, roster, and routing ship as the on-demand `crew-team` skill and are mirrored in the
> Maestro — load that skill or talk to `maestro` to bring the conventions into context.

## Commands

| What you want | Command |
|---------------|---------|
| Start the team on a **new** project | `/crew:init` |
| Onboard the team to an **existing** project | `/crew:onboard` |
| Refresh project instruction/context understanding | `/crew:refresh` |
| Debate a topic from every angle and decide | `/crew:brainstorm <topic>` |
| Turn a feature/requirement into a plan + tasks | `/crew:plan <feature>` |
| Build a task: implement → test → review | `/crew:build <task>` |
| Fix a bug: reproduce → root cause → smallest fix → regression test | `/crew:debug <bug>` |
| Investigate how something works today and document it | `/crew:research <feature/question>` |
| Learn from completed work, corrections, and repeated failures | `/crew:retro <task/session/correction>` |
| Ship the whole backlog autonomously (plan → build → commit per task) | `/crew:ship [feature]` |
| Review code, or stress-test a decision | `/crew:review <target>` |
| Open a merge/pull request from a shipped branch | `/crew:mr [branch]` |
| Review a merge/pull request — code **and** business | `/crew:review-mr <MR ref>` |
| Ask about any decision, term, or topic | `/crew:ask <question>` |
| Be interrogated on your own reasoning | `/crew:grill <idea>` |
| Drop an abandoned plan: archive its requirement, decision & tasks | `/crew:drop <feature>` |
| See the state of play — a read-only rollup of `~/.ai/<project>/` memory | `/crew:status [area]` |

Or skip the commands and just talk: pick **maestro** (or a specialist) and ask in plain language —
the Maestro classifies anything you hand it and routes it to the right lane.

## How it works

The **Maestro** is the conductor: it frames the problem, brings in the right specialists, runs the
debate, synthesizes a decision, and records it. The six specialists do the focused work.

**The marquee flow — `/crew:brainstorm`:**

1. The Maestro frames the question and picks who belongs at the table.
2. Those specialists give their views **independently** — each in character.
3. The Maestro surfaces the **agreements and the real tensions**.
4. A focused **rebuttal round**: the conflicting agents respond to each other.
5. The Maestro **synthesizes** a recommendation — which arguments won, which tradeoffs were accepted,
   what's still open.
6. The decision and discussion are written to project memory.

**Delegation.** Ask for anything. The Maestro classifies it and routes to the one right specialist —
or convenes the team if it's big. If a specialist gets something out of its lane, it names the right
teammate and the Maestro re-routes.

> **How orchestration works:** the `/crew:*` commands run in the main session (which holds the `Task`
> tool) and **spawn each specialist as an isolated subagent** with a compact brief. Delegation is
> **explicit** — the specialist is named, never auto-picked from its description. Orchestration stays
> single-level: specialists don't spawn peers; one that hits work outside its lane names the right
> teammate and the main session re-routes.

### Bring the team onto your project (once)

- **New project** (little/no code) → `/crew:init` — a short interview, then it scaffolds memory.
- **Existing project** → `/crew:onboard` — the team scans and *understands* your codebase and any
  existing context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`, `context.md`, …)
  **without modifying them**, then builds its memory to complement them.
- **Refresh project instructions/context understanding** → `/crew:refresh` — re-read authoritative
  project rules and reconcile local `~/.ai/<project>/` assumptions after teammate/tooling changes.

## Project memory (`~/.ai/<project>/`)

`/crew:init` (new project) or `/crew:onboard` (existing project) creates the project's memory folder
in the central `~/.ai/` store — outside the repo, so it never enters git history. `<project>` is the
project directory's basename; the root is `$AI_HOME`, or `~/.ai` if unset. Lessons that generalize
across projects live in `~/.ai/shared/lessons/`.

```
~/.ai/<project>/
  charter.md       project principles + stack (read first, every session)
  discussions/     brainstorm summaries
  decisions/       ADR-style decision log
  requirements/    specs
  tasks/           task breakdowns + status
  research/        sourced findings
  reviews/         reviews + critiques
  lessons/         reusable lessons from retrospectives and user corrections
```

Durable, polished docs (architecture overviews, guides) live in `docs/` — one home per artifact, no
duplicates. Conventions are documented in the bundled **memory** skill.

## Skills

The team carries shared *method* as skills, so the deep know-how lives in one place instead of being
copy-pasted into every persona. Claude loads each on demand when the task matches its `description`.

| Skill | What it encodes |
|-------|-----------------|
| **crew-team** | The roster, routing, standing rules, and the loop-engineering principle — every unit of work opens, then closes or is dropped, leaving a trace (team overview) |
| **memory** | How the `~/.ai/<project>/` memory works and who writes where |
| **codebase-onboarding** | Understanding an unfamiliar repo without modifying it (powers `/crew:onboard`) |
| **decision-and-spec** | Testable requirements (given/when/then) and ADRs with real rationale |
| **research-method** | Sourcing, confidence rating, and citation discipline |
| **feedback-loop** | Capturing lessons learned so future agents change behavior (powers `/crew:retro`) |
| **facilitation** | Running a debate that ends in a decision (steelman, surface assumptions) |
| **critique** | Red-teaming a decision/plan/idea — three lenses + a verdict (powers `/crew:review`, `/crew:grill`) |
| **debugging** | Fixing a bug without breaking what works — root cause, smallest fix, regression test |
| **mr-review** | Reviewing MRs/PRs/diffs on code and business axes, with a clear merge verdict |

## Layout

The repo **is** the plugin — the files are native Claude Code plugin components, no build step.

```
.claude-plugin/plugin.json      plugin manifest (name: crew)
.claude-plugin/marketplace.json marketplace listing for /plugin install
agents/                 *.md — the Maestro + six specialists (subagents)
commands/               *.md — the /crew:* commands
skills/                 <name>/SKILL.md — method skills loaded on demand (incl. the crew-team overview)
templates/crew/         starting content for a project's ~/.ai/<project>/ memory (init/onboard)
docs/architecture.md    tracked architecture overview
CLAUDE.md               contributor notes for editing the plugin
.github/workflows/      CI: manifest + frontmatter + template validation
```

See [docs/architecture.md](docs/architecture.md) for the full picture and
[CLAUDE.md](CLAUDE.md) for editing conventions.

## Design principles

- **Single-level orchestration.** One conductor (the Maestro) drives many specialists; specialists
  don't drive each other. This is enforced in config: only `maestro` carries the `Task` tool, so only
  it can spawn a specialist. File-write lanes (e.g. the reviewer critiques, it doesn't rewrite code)
  are a convention backed by version control — a lane violation shows up in the diff.
- **Productive disagreement.** Personas carry deliberate, opposing biases so a brainstorm produces
  real tension, not consensus theater. The Maestro's job is to force a decision out of it.
- **Memory is the product.** Decisions and their rationale are written to the central
  `~/.ai/<project>/` store (outside the repo), in plain language, for a human to read later. A
  conclusion that isn't written down didn't happen.
- **Respect what's already there.** Onboarding reads existing context files (`CLAUDE.md`, `AGENTS.md`,
  `copilot-instructions.md`, …) and never modifies them — they're authoritative.
- **Native files, no build.** The repo files are the plugin you install — edit `agents/`,
  `commands/`, `skills/` directly; nothing is generated.

## Known limitations

- **Guardrails are instructional, not enforced.** Memory write-scoping and "stay in your lane" rules
  are prose the model follows, not hard permissions. Agents can do whatever their granted tools allow.
- **No always-on injection.** A plugin can't ship a project-wide always-on instruction; the team
  identity is an on-demand skill (`crew-team`) plus the Maestro body.
- **Brainstorms cost tokens.** Convening several specialists across rounds is expensive; pick the
  smallest table that still disagrees, and prefer a single rebuttal round.

## License

MIT

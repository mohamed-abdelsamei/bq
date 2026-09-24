# bq

A reusable **team of AI agents** for your work and pet projects, packaged as a native **Claude Code
plugin**. Six specialists — each with a distinct **personality and point of view** — run a real
feature lifecycle: **brainstorm a requirement from multiple angles, agree on a solution, split it
into tasks, then build, test, review, and document it.** A master conductor (the **Maestro**) frames
the work, convenes the team, routes requests, and keeps the rationale. Every project gets its own
**memory folder** in the central `~/.ai/` store (outside the repo) so discussions and decisions are
never lost between sessions.

Talk to the **maestro** subagent and let it delegate, or address **any specialist directly** — and
if a request isn't theirs, they hand it to the right teammate. Or just run a `/bq:*` command.

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
any of it: ask what a decision means with `/bq:ask`, or have your own reasoning grilled one sharp
question at a time with `/bq:grill`.

## Install

bq installs as a Claude Code plugin from a marketplace. Once the repo is on GitHub:

```
/plugin marketplace add mohamed-abdelsamei/co-agents
/plugin install bq@bq
```

To install a local checkout, add its path as a marketplace first:

```
/plugin marketplace add /absolute/path/to/co-agents
/plugin install bq@bq
```

Then reload with `/plugin` (or restart Claude Code). After installing, run a `/bq:*` command, or
select the **maestro** subagent (or a specialist) and ask in plain language.

### Manual global install (no plugin system)

If the plugin/marketplace flow is unavailable (e.g. blocked by policy), install bq directly
into your global `~/.claude/` with the bundled script:

```
./install.sh install      # install globally (removes any older flat install first)
./install.sh uninstall    # remove everything the script installed
./install.sh reinstall    # uninstall then install (pick up edits)
```

It copies into a clean, collision-proof `bq` namespace:

| Component | Installed to | Result |
|-----------|--------------|--------|
| commands  | `~/.claude/commands/bq/`  | invoked as `/bq:<name>` |
| skills    | `~/.claude/skills/bq-*/`  | skill ids `bq-<name>` |
| agents    | `~/.claude/agents/bq/`    | prefixed at install: `bq-maestro`, `bq-architect`, … (same names as before) |
| templates | `~/.claude/bq-templates/` | scaffolding for `/bq:init` and `/bq:onboard` |

The script tracks what it wrote in `~/.claude/.bq-install-manifest`, so `uninstall` removes
exactly those files. Target another dir with `CLAUDE_CONFIG_DIR=/path ./install.sh install`. Restart
Claude Code afterward to pick up the changes.

> **Always-on note:** a plugin cannot inject an always-on instruction into your project. The team
> identity, roster, and routing ship as the on-demand `bq-team` skill and are mirrored in the
> Maestro — load that skill or talk to the Maestro (`bq:maestro`) to bring the conventions into context.

### Install into GitHub Copilot (VS Code)

The same team runs in GitHub Copilot. Copilot has no plugin marketplace, so the bundled script
transforms the canonical Claude files into Copilot customizations and installs them into your user
profile:

```
./install-copilot.sh install      # transform + install into your Copilot profile
./install-copilot.sh status       # show what's installed
./install-copilot.sh uninstall    # remove everything the script installed
./install-copilot.sh reinstall    # uninstall then install (pick up edits)
```

| Component | Installed to | Result |
|-----------|--------------|--------|
| commands  | `<prompts>/bq-*.prompt.md` | invoked as `/bq-<name>` (dash — Copilot has no `:` namespacing) |
| agents    | `<prompts>/bq-*.agent.md`  | custom agents `bq-maestro`, `bq-architect`, … |
| skills    | `~/.copilot/skills/bq-*/`   | skill ids `bq-<name>` |
| identity  | `<prompts>/bq-team.instructions.md` | always-on (`applyTo: '**'`) roster + routing |

`<prompts>` is your VS Code User prompts folder. The transform rewrites `$ARGUMENTS` →
`${input:args}`, maps Claude tool names to Copilot aliases (`read`, `search`, `edit`, `execute`,
`web`, `todo`, `agent`), and restricts subagent delegation to the Maestro. It tracks what it wrote
in `~/.copilot/.bq-copilot-install-manifest`, so `uninstall` removes exactly those files. Override
locations with `COPILOT_PROMPTS_DIR=/path` and `COPILOT_SKILLS_DIR=/path`. Reload VS Code
(**Developer: Reload Window**) afterward, then type `/` in Copilot Chat to run `/bq-build`,
`/bq-brainstorm`, `/bq-status`, ….

> Unlike a Claude plugin, Copilot **can** carry an always-on instruction: the `bq-team` identity is
> installed as a user-level `*.instructions.md` with `applyTo: '**'`, so the roster and routing are
> in context everywhere without loading a skill.

## Commands

| What you want | Command |
|---------------|---------|
| Start the team on a **new** project | `/bq:init` |
| Onboard the team to an **existing** project | `/bq:onboard` |
| Refresh project instruction/context understanding | `/bq:refresh` |
| Debate a topic from every angle and decide | `/bq:brainstorm <topic>` |
| Turn a feature/requirement into a plan + tasks | `/bq:plan <feature>` |
| Build a task: implement → test → review | `/bq:build <task>` |
| Fix a bug: reproduce → root cause → smallest fix → regression test | `/bq:debug <bug>` |
| Investigate how something works today and document it | `/bq:research <feature/question>` |
| Learn from completed work, corrections, and repeated failures | `/bq:retro <task/session/correction>` |
| Ship the whole backlog autonomously (plan → build → commit per task) | `/bq:ship [feature]` |
| Review code, or stress-test a decision | `/bq:review <target>` |
| Open a merge/pull request from a shipped branch | `/bq:mr [branch]` |
| Review a merge/pull request — code **and** business | `/bq:review-mr <MR ref>` |
| Ask about any decision, term, or topic | `/bq:ask <question>` |
| Be interrogated on your own reasoning | `/bq:grill <idea>` |
| Drop an abandoned plan: archive its requirement, decision & tasks | `/bq:drop <feature>` |
| See the state of play — a read-only rollup of `~/.ai/<project>/` memory | `/bq:status [area]` |

Or skip the commands and just talk: pick **maestro** (or a specialist) and ask in plain language —
the Maestro classifies anything you hand it and routes it to the right lane.

> In **GitHub Copilot** these commands use a dash instead of a colon — `/bq-build`, `/bq-status`,
> `/bq-brainstorm`, … — because Copilot has no `:` namespacing.

## How it works

The **Maestro** is the conductor: it frames the problem, brings in the right specialists, runs the
debate, synthesizes a decision, and records it. The six specialists do the focused work.

**The marquee flow — `/bq:brainstorm`:**

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

> **How orchestration works:** the `/bq:*` commands run in the main session (which holds the `Agent`
> tool) and **spawn each specialist as an isolated subagent** with a compact brief. Delegation is
> **explicit** — the specialist is named, never auto-picked from its description. Orchestration stays
> single-level: specialists don't spawn peers; one that hits work outside its lane names the right
> teammate and the main session re-routes.

### Bring the team onto your project (once)

- **New project** (little/no code) → `/bq:init` — a short interview, then it scaffolds memory.
- **Existing project** → `/bq:onboard` — the team scans and *understands* your codebase and any
  existing context files (`CLAUDE.md`, `AGENTS.md`, `copilot-instructions.md`, `context.md`, …)
  **without modifying them**, then builds its memory to complement them.
- **Refresh project instructions/context understanding** → `/bq:refresh` — re-read authoritative
  project rules and reconcile local `~/.ai/<project>/` assumptions after teammate/tooling changes.

## Project memory (`~/.ai/<project>/`)

`/bq:init` (new project) or `/bq:onboard` (existing project) creates the project's memory folder
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
| **bq-team** | The roster, routing, standing rules, and the loop-engineering principle — every unit of work opens, then closes or is dropped, leaving a trace (team overview) |
| **memory** | How the `~/.ai/<project>/` memory works and who writes where |
| **codebase-onboarding** | Understanding an unfamiliar repo without modifying it (powers `/bq:onboard`) |
| **decision-and-spec** | Testable requirements (given/when/then) and ADRs with real rationale |
| **research-method** | Sourcing, confidence rating, and citation discipline |
| **feedback-loop** | Capturing lessons learned so future agents change behavior (powers `/bq:retro`) |
| **facilitation** | Running a debate that ends in a decision (steelman, surface assumptions) |
| **critique** | Red-teaming a decision/plan/idea — three lenses + a verdict (powers `/bq:review`, `/bq:grill`) |
| **debugging** | Fixing a bug without breaking what works — root cause, smallest fix, regression test |
| **mr-review** | Reviewing MRs/PRs/diffs on code and business axes, with a clear merge verdict |

## Layout

The repo **is** the plugin — the files are native Claude Code plugin components, no build step.

```
.claude-plugin/plugin.json      plugin manifest (name: bq)
.claude-plugin/marketplace.json marketplace listing for /plugin install
agents/                 *.md — the Maestro + six specialists (subagents)
commands/               *.md — the /bq:* commands
skills/                 <name>/SKILL.md — method skills loaded on demand (incl. the bq-team overview)
templates/bq/         starting content for a project's ~/.ai/<project>/ memory (init/onboard)
docs/architecture.md    tracked architecture overview
CLAUDE.md               contributor notes for editing the plugin
.github/workflows/      CI: manifest + frontmatter + template validation
```

See [docs/architecture.md](docs/architecture.md) for the full picture and
[CLAUDE.md](CLAUDE.md) for editing conventions.

## Design principles

- **Single-level orchestration.** One conductor (the Maestro) drives many specialists; specialists
  don't drive each other. This is enforced in config: only the Maestro (`bq:maestro`) carries the `Agent` tool, so only
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
  identity is an on-demand skill (`bq-team`) plus the Maestro body.
- **Brainstorms cost tokens.** Convening several specialists across rounds is expensive; pick the
  smallest table that still disagrees, and prefer a single rebuttal round.

## License

MIT

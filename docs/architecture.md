# Ca Architecture

This repository is a publishable GitHub Copilot extension for VS Code. The extension manifest in
[package.json](../package.json) contributes the workspace payload directly, and the legacy installer
remains as a direct-copy transition path.

## What the extension contains

- `agents/*.agent.md` for custom agents
- `prompts/*.prompt.md` for slash commands
- `instructions/*.instructions.md` for on-demand method instructions
- `skills/*/SKILL.md` for reusable skills
- `copilot-instructions.md` for the project-scope always-on conductor when installed into a repo via
  the legacy project install (an extension cannot contribute an always-on workspace instruction)
- `package.json` as the extension manifest that publishes the payload

The naming convention is part of the architecture:

- agent and prompt files use the `ca-` prefix
- skill folders and `SKILL.md` names match exactly
- the repo stays editable as plain files; nothing is generated

## Install scopes

The installer supports two modes:

- **Marketplace / VSIX** — installs the published extension, which contributes the agents,
  prompts, on-demand instructions, and skills directly. It does not install the always-on
  project conductor; use a legacy project install for that.
- **Legacy global** — uses the installer to copy the bundle into the VS Code user profile as a
  managed directory, then exposes discovery shims so Copilot can find the customizations in every
  workspace.
- **Legacy project** — uses the installer to copy the files into a target repository's `.github/`
  folder and tracks the files with a manifest.

All modes install the same customization payload; they differ only in how the files are delivered.

## Source of truth

- The repo files are the extension source of truth.
- `.ca/` is local project memory for a specific workspace. It is not the plugin and is not
  tracked in git.
- `README.md` explains the public layout at a high level and links back here.

## Operating rules

- Keep the architecture lean and direct-editable.
- Keep the publishable extension manifest aligned with the payload files.
- Keep the tracked doc, README, and installer wording aligned when the architecture changes.

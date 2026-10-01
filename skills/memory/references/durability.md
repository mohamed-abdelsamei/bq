# Durability and recovery — runbook

The full runbook behind the **memory** skill's *Durability and recovery* section. The opt-in rule,
the hard stops, and the command path live there; this file is the detail. `<history>` below is the
history repo path that `status` prints.

## What protects memory

An opt-in local git history of the whole store, kept in a bare repo *outside* it:
`$BQ_MEMORY_GIT_DIR`, default `~/Library/Application Support/bq/ai-history.git` on macOS,
`${XDG_DATA_HOME:-~/.local/share}/bq/ai-history.git` elsewhere. It has no remote, is never pushed,
and survives `rm -rf ~/.ai`. <!-- claude-only -->Once the user opts in (`/bq:init`, `/bq:onboard`
and `/bq:refresh` offer it; on yes, run `init` then `checkpoint`), on a plugin install the
SessionStart hook checkpoints in the background at each session start (a manual install has no
hooks: run `checkpoint` yourself), detached so closing the session can't cut a commit short.
It never makes the first commit. To verify: the hook needs the plugin at 0.6.0+ (check with
`/plugin`); after the first checkpoint, change something in memory, open a new session and run
`bq_memory.py log` — expect a second commit.<!-- copilot: Copilot has no hooks: after `init`, run `checkpoint` yourself. --><!-- /claude-only -->

## Limits

Protection starts at the first checkpoint — nothing older can be recovered, and a crash loses writes
since the last one. Git doesn't track empty folders, so they aren't restored; a renamed folder shows
as a deletion of the old name. A nested git repo in the store (a folder with its own `.git`) keeps
only its commit pointer, not its files — back it up on its own. The history is one copy on the same
disk, so recommend Time Machine (or another backup) as well.

## Commands

Run each with the command path in the memory skill's *Durability and recovery* section.

- `init` — create the history; then `checkpoint` makes the first commit.
- `checkpoint` — commit every change; skips quietly while another checkpoint runs. Unreadable files
  are skipped (the rest is committed) and recorded as the last error.
- `status` — history path (`<history>`), lock state (stuck locks with their paths), last
  checkpoint, last checkpoint error, uncommitted changes, missing folders, folders deleted in the
  last 7 days.
- `log [dir] [-n N]` — the last N checkpoints (default 20), optionally only those touching one
  top-level folder.
- `restore <dir> [--rev R] [--force]` — bring back a top-level folder, by default from the last
  revision where it existed. It **never destroys newer work**: a missing folder is restored in place;
  a present one is extracted beside it to `<dir>.restored-<rev>/` to compare; `--force` overwrites
  only after checkpointing the current state (the output prints the undo command). It refuses a
  target that is a symlink or not a real folder — move it aside first. A name starting with `-` goes
  after `--` (printed commands already do this).
- `stamp` — write `<mem>/.identity` for the git repo at the current directory.
- `index [project]` — print the memory index, open loops first.

## `bq memory:` notices

They appear <!-- claude-only -->at session start, or <!-- copilot: --><!-- /claude-only -->from
`checkpoint` and `status`.

- *Folder missing or recently deleted* — the line carries the exact restore command. Confirm with
  the user before running it. An intentional deletion also shows for 7 days (no dismiss yet).
<!-- claude-only -->- *No checkpoint yet* — `init` ran but the first `checkpoint` didn't; run it on the user's yes.<!-- copilot: --><!-- /claude-only -->
- *Last checkpoint failed* — the time and reason (unreadable files, disk full, a git error). Fix the
  cause; the next successful checkpoint clears it.
- *Stuck lock* — checkpoints are paused. `status` lists each git `*.lock` in `<history>` older than
  two minutes (`index.lock`, `HEAD.lock`, `packed-refs.lock`, `refs/**/*.lock`). Confirm no git
  process is using that history (`pgrep -fl -- "<history>"` — no output means nothing is running),
  then delete the listed lock files by hand. bq never removes them.
- *Nested git repo* — shown for 7 days after a checkpoint first records one; see Limits.
<!-- claude-only -->- *Stamp mismatch* — see Identity.<!-- copilot: --><!-- /claude-only -->

## Identity

`.identity` records the repo root and remotes a memory folder belongs to; it is restored with its
folder. <!-- claude-only -->When it names neither this repo's root nor any of its remotes, the
SessionStart hook loads **no lessons**, so same-named repos can't read each other's. Only if it
really is the same project (moved or re-cloned) does `/bq:refresh` re-stamp; a stamp replaces the
recorded root.<!-- copilot: Copilot has no hooks, so nothing checks it there; a `stamp` replaces the recorded root. --><!-- /claude-only -->

## Secrets

The history ignores `*.env`, `.env`, `*.pem`, `*.key`, SSH key files (`id_rsa*`, `id_ed25519*`, …)
and `.DS_Store`. Everything else is kept for good — never write secrets to memory. To purge one
already committed:

1. Note its blob: `git --git-dir="<history>" rev-parse HEAD:<project>/<file>`. Remove it from the
   store, then `checkpoint`.
2. Either **rewrite**, if `git filter-repo` is installed:
   `cd "<history>" && git filter-repo --invert-paths --path <project>/<file> --force` —
   or **re-init**: move `<history>` aside, run `init` and `checkpoint`, and delete the old copy once
   sure (all earlier history goes with it).
3. Drop the unreferenced objects: `git --git-dir="<history>" gc --prune=now`.
4. Check: `git --git-dir="<history>" log --all --oneline -- <project>/<file>` prints nothing, and
   `git --git-dir="<history>" cat-file -e <blob>` fails.
5. Backups (Time Machine) of `<history>` still hold the secret; purge those too.

# MR review — isolated checkout

How the Maestro gets a hosted MR/PR or a remote branch onto disk without touching the user's work.
The user may be coding in the same repo with uncommitted edits and a stale local `main`; the review
must never change their branch, working tree, index, stash, local branches, or `origin/*` refs, and
must never diff against their local copy of the target. Pasted patches and local "current changes"
skip this file — there is nothing remote to fetch.

## Names and validation

- **Main checkout** `<main>`: the parent of `git rev-parse --path-format=absolute --git-common-dir`
  (correct even when the session is inside another worktree). `<project>` is its basename.
- **Key** `<key>`: `mr-<id>` for an MR/PR, `branch-<name>` for a branch — lowercase, only `[a-z0-9-]`
  (every other character becomes `-`, repeats collapse), at most ~60 chars. The id must match
  `^[0-9]+$`; branch and target names must pass `git check-ref-format --branch "<name>"`.
- **Worktree** `<wt>`: `<main-parent>/.bq-review/<project>/<key>` — a sibling of the repo, so the
  user's `git status`, editor and tools never see it.
- **Refs** live only under `refs/bq-review/<key>/` (`head`, `base`). Pass every value as its own
  quoted argument; never build a shell string from MR text.

## Fetch (private refs only)

The head refspec comes from the platform: GitLab `refs/merge-requests/<id>/head`, GitHub
`refs/pull/<id>/head`, a branch `refs/heads/<branch>`. The remote and target come from `glab`/`gh`
metadata (default remote `origin`).

```
git -C "<main>" fetch --no-tags --refmap= "<remote>" \
  "+<head-refspec>:refs/bq-review/<key>/head" \
  "+refs/heads/<target>:refs/bq-review/<key>/base"
sha=$(git -C "<main>" rev-parse "refs/bq-review/<key>/head")   # must match [0-9a-f]{7,40}
```

The empty `--refmap=` is load-bearing: without it git "opportunistically" updates `origin/<target>`
too, so the user's `git status` suddenly reports "behind". With it, only the two private refs move. If the platform reports a different head
SHA than the one fetched, say so and review the fetched one.

## Worktree

- **Missing** → create and lock it (the lock stops `git worktree prune` from reaping it):
  ```
  git -C "<main>" worktree add --detach "<wt>" "$sha"
  git -C "<main>" worktree lock --reason "bq review <key>" "<wt>"
  ```
- **Present and clean** (`git -C "<wt>" status --porcelain` is empty) → move it:
  `git -C "<wt>" checkout --detach "$sha"`.
- **Present and dirty** → it is ours, not the user's: `git -C "<main>" worktree unlock "<wt>"`,
  `git -C "<main>" worktree remove --force "<wt>"`, then create as above.
- **Registered but its folder is gone** (the user deleted `.bq-review/` by hand; `worktree add`
  then fails with "missing but locked worktree") → `git -C "<main>" worktree unlock "<wt>"` and
  `git -C "<main>" worktree remove --force "<wt>"` clear just that entry; then create as above.
  Never a bare `git worktree prune` — it would also clear the user's own stale worktrees.
- **Path exists but is not a worktree of this repo** (absent from `git -C "<main>" worktree list`)
  → stop and report; never delete it.

## Diff

Always against the merge-base with the **fetched** target, never the local one:

```
git -C "<wt>" diff "refs/bq-review/<key>/base...HEAD"
git -C "<wt>" log --oneline "refs/bq-review/<key>/base..HEAD"
```

## Rules for everyone reading the worktree

- Every git, test, or build command runs as `git -C "<wt>" …` or with `<wt>` as its working
  directory. Never `cd`, and never run a review command in `<main>`.
- `git show "<sha>":"<path>"` checks for suggested changes run with `-C "<wt>"`.
- Read-only as before: no edits, commits, or pushes in `<wt>`. A cheap narrow test may write its
  usual build/cache output there; nothing else.
- Project memory is still `~/.ai/<project>/` of the main checkout — a linked worktree maps to it.

## Cleanup

`/bq:review-mr cleanup [<ref>]` lists every worktree under `<main-parent>/.bq-review/<project>/`
(optionally just `<ref>`'s) with its MR state from `glab`/`gh` (open, merged, closed, unknown), and
on the user's go-ahead removes the ones they name:

```
git -C "<main>" worktree unlock "<wt>"
git -C "<main>" worktree remove --force "<wt>"
git -C "<main>" for-each-ref --format='%(refname)' "refs/bq-review/<key>/" |
  while read -r ref; do git -C "<main>" update-ref -d "$ref"; done
```

Never remove a path outside `.bq-review/<project>/`, and never a worktree the user created.

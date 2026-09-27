#!/usr/bin/env python3
"""Async SessionStart hook (ADR 0011, M6): checkpoint the ~/.ai store into its history repo.

A no-op unless the history repo exists and already has a commit: `init` and the first
`checkpoint` run together, on the user's yes, from the CLI. Takes the checkpoint flock, then
forks: the parent exits 0 at once and the child (its own session, stdio on /dev/null) runs the
checkpoint while holding the inherited lock, so a CLI exit or hook timeout can't kill git
mid-commit. Without fork (non-POSIX) or if fork fails, it runs inline. Nothing is printed: a
failure is recorded in <history>/bq-last-error, which the SessionStart hook and `status` show.
Always exits 0. The one hook that writes: into the history repo, never into the store.
"""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ inside the plugin dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bqhook as h  # noqa: E402


def quiet(_line):
    pass


def detach():
    """Fork. True in the parent, False in the detached child, None when running inline."""
    if not hasattr(os, "fork"):
        return None
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        pid = os.fork()
    except OSError:
        return None
    if pid:
        return True
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    return False


def run_checkpoint(m):
    try:
        m.checkpoint(out=quiet, warn=quiet, locked=True)
    except m.MemError:
        pass  # already recorded in bq-last-error
    except Exception as e:  # a bug: still leave a trace the session start can show
        m.record_error(f"{type(e).__name__}: {e}")


def main(_data):
    import _bqmem as m  # lazy: a broken memory module fails open through h.run
    if not m.has_history() or not m.has_commits():
        return
    with m.checkpoint_lock() as held:
        if not held:
            return  # another checkpoint is running
        role = detach()
        if role:
            return  # parent: closing our fd leaves the lock with the child
        try:
            run_checkpoint(m)
        finally:
            if role is False:
                os._exit(0)


if __name__ == "__main__":
    h.run(main)

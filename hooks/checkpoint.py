#!/usr/bin/env python3
"""Async SessionStart hook (ADR 0011, M6): checkpoint the ~/.ai store into its history repo.

A no-op unless the history repo exists (opt-in via `bq_memory.py init`). Prints nothing on
stdout; a deletion notice or a diagnostic goes to stderr (async hook output isn't shown reliably
anyway). Always exits 0. The one hook that writes: into the history repo, never into the store.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ inside the plugin dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bqhook as h  # noqa: E402


def to_stderr(line):
    print(line, file=sys.stderr)


def main(_data):
    import _bqmem  # lazy: a broken memory module fails open through h.run
    if _bqmem.has_history():
        _bqmem.checkpoint(out=to_stderr, warn=to_stderr)


if __name__ == "__main__":
    h.run(main)

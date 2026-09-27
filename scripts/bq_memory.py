#!/usr/bin/env python3
"""bq memory history (ADR 0011): a thin CLI over hooks/_bqmem.py.

History lives in a bare git repo outside the store ($BQ_MEMORY_GIT_DIR, default
~/Library/Application Support/bq/ai-history.git on macOS, else
${XDG_DATA_HOME:-~/.local/share}/bq/ai-history.git) with ${AI_HOME:-~/.ai} as the work tree.

  init                         opt in: create the history repo (refuses when unsafe)
  checkpoint                   commit every change; notices for deleted project folders
                               (skips quietly while another checkpoint runs)
  status                       history, lock state (stuck *.lock paths), last checkpoint, last
                               checkpoint error, notices, uncommitted count, missing folders,
                               folders deleted in the last 7 days
  log [dir] [-n N]             short history, optionally for one folder
  restore <dir> [--rev R] [--force]
                               bring a folder back; never overwrites newer work without --force
  stamp                        write <AI_HOME>/<project>/.identity for the repo at cwd
  index [project]              print the memory index: open loops, then one line per artifact
                               (default project: the repo at cwd); read-only, no git needed

Exit 0 on success and expected no-ops; 1 with one `bq memory:` line on a refusal or failure.
"""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep hooks/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import _bqmem as m  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(prog="bq_memory.py", description="bq memory history (ADR 0011)")
    sub = p.add_subparsers(dest="cmd", metavar="command")
    sub.required = True
    sub.add_parser("init", help="create the history repo outside AI_HOME")
    sub.add_parser("checkpoint", help="commit every change in AI_HOME")
    sub.add_parser("status", help="show history state, lock, missing and recently deleted folders")
    lg = sub.add_parser("log", help="short history")
    lg.add_argument("dir", nargs="?")
    lg.add_argument("-n", type=int, default=20, help="how many checkpoints (default 20)")
    rs = sub.add_parser("restore", help="restore a top-level folder")
    rs.add_argument("dir")
    rs.add_argument("--rev", help="revision to restore from (default: last one where dir existed)")
    rs.add_argument("--force", action="store_true",
                    help="overwrite an existing folder (the current state is checkpointed first)")
    sub.add_parser("stamp", help="write .identity for the repo at the current directory")
    ix = sub.add_parser("index", help="print the memory index (open loops first)")
    ix.add_argument("project", nargs="?", help="project name (default: the repo at cwd)")
    a = p.parse_args(argv)
    try:
        if a.cmd == "init":
            return m.init()
        if a.cmd == "checkpoint":
            return m.checkpoint()
        if a.cmd == "status":
            return m.status()
        if a.cmd == "log":
            return m.log(a.dir, a.n)
        if a.cmd == "restore":
            return m.restore(a.dir, a.rev, a.force)
        if a.cmd == "index":
            return m.index(a.project)
        return m.stamp()
    except m.MemError as e:
        print(f"bq memory: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

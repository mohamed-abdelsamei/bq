"""Shared helpers for the bq learning-loop hooks (ADR 0010). Stdlib only.

Contract for every hook script: always exit 0, print nothing on stdout unless
there is something to say, send one diagnostic line to stderr on error, make no
network calls, and write nothing anywhere (no lessons, no plugin files, no state).
"""
import json
import os
import sys
from pathlib import Path


def read_input():
    """Hook input as a dict; empty, garbage, or non-object stdin gives {}."""
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except (ValueError, UnicodeDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def field(data, *names):
    """First present string value among field-name variants, else ''."""
    for n in names:
        v = data.get(n)
        if isinstance(v, str) and v:
            return v
    return ""


def project_dir(data):
    """Git root of the input `cwd` (walking up for .git), else cwd itself."""
    cwd = Path(field(data, "cwd") or os.getcwd()).expanduser()
    for p in (cwd, *cwd.parents):
        if (p / ".git").exists():
            return p
    return cwd


def ai_home():
    return Path(os.environ.get("AI_HOME") or Path.home() / ".ai").expanduser()


def memory_dir(data):
    """${AI_HOME:-~/.ai}/<project> if it exists, else None.

    A project named `shared` has no project memory: ~/.ai/shared is the cross-project store.
    """
    name = project_dir(data).name
    if not name or name.casefold() == "shared":  # casefold: macOS FS is case-insensitive
        return None
    d = ai_home() / name
    return d if d.is_dir() else None


def emit_context(event, text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}))


def run(main):
    """Run a hook's main(data); swallow every error to one stderr line; exit 0."""
    try:
        main(read_input())
    except Exception as e:  # fail open: a broken hook must never break the session
        print(f"bq hook: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)

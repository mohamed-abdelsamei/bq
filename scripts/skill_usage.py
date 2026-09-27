#!/usr/bin/env python3
"""Report how often each bq skill and command has been used. Stdlib only, read-only.

Usage: python3 scripts/skill_usage.py [--json]

Reads `skillUsage` from Claude Code's `.claude.json` (in $CLAUDE_CONFIG_DIR if set, else $HOME;
$BQ_CLAUDE_JSON overrides the path, for tests). That key is undocumented: each entry is
{usageCount (lifetime), lastUsedAt (epoch ms)}, counting model Skill calls and typed commands.
A missing file or an unknown format prints one line and exits 0 — this is a report, never a gate.
Only entries under bq's own keys are validated (other tools' entries are not ours to judge); a
timestamp that is not a positive, representable epoch-ms prints as "unknown".

Keys matched per bq name: `bq:<name>` (plugin install) and, for skills, `bq-<name>` (manual install),
plus the same shapes under the plugin's former name `crew` (`crew:<name>`, `crew-<name>`; the bq-team
skill was `crew-team`), summed as aliases.
Bare `<name>` keys are not counted: they collide with built-ins and other plugins (`init`, `review`).
"""
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def usage_path():
    override = os.environ.get("BQ_CLAUDE_JSON")
    if override:
        return Path(override)
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home())
    return Path(base).expanduser() / ".claude.json"


def load_usage(path):
    """Return (skillUsage dict, None) or (None, one-line reason)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"no skill usage data: {path} not found"
    except (OSError, UnicodeDecodeError, ValueError) as e:
        return None, f"no skill usage data: cannot read {path} ({type(e).__name__})"
    usage = data.get("skillUsage") if isinstance(data, dict) else None
    if not isinstance(usage, dict):
        return None, f"no skill usage data: {path} has no skillUsage object (unknown format)"
    return usage, None


def valid_entry(entry):
    return (isinstance(entry, dict) and is_num(entry.get("usageCount"), int)
            and is_num(entry.get("lastUsedAt"), (int, float)))


def day(ms):
    """ISO date for an epoch-ms timestamp, or None if it isn't positive, finite and representable."""
    try:
        if not (math.isfinite(ms) and ms > 0):  # isfinite raises OverflowError on a huge int
            return None
        return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def is_num(v, types):
    return isinstance(v, types) and not isinstance(v, bool)


def bq_names(root):
    skills = sorted(p.parent.name for p in (root / "skills").glob("*/SKILL.md"))
    commands = sorted(p.stem for p in (root / "commands").glob("*.md"))
    return skills, commands


def manual_skill_key(name):
    return name if name.startswith("bq-") else f"bq-{name}"  # install.sh bq_name()


def legacy_skill_key(name):
    return "crew-" + (name[3:] if name.startswith("bq-") else name)  # bq-team was crew-team


def keys_for(kind, name):
    keys = [f"bq:{name}", f"crew:{name}"]
    if kind == "skill":
        keys += [manual_skill_key(name), legacy_skill_key(name)]
    return keys


def row(kind, name, usage):
    keys = [k for k in keys_for(kind, name) if k in usage]
    hits = [usage[k] for k in keys]
    uses = sum(h["usageCount"] for h in hits)
    days = [d for d in (day(h["lastUsedAt"]) for h in hits) if d]
    return {
        "kind": kind,
        "name": name,
        "uses": uses,
        "last_used": max(days) if days else ("unknown" if uses > 0 else None),
        "keys": keys,
    }


def targets(root):
    skills, commands = bq_names(root)
    return [("skill", n) for n in skills] + [("command", n) for n in commands]


def bad_key(root, usage):
    """The first bq key whose entry has an unknown shape, else None."""
    return next((k for kind, n in targets(root) for k in keys_for(kind, n)
                 if k in usage and not valid_entry(usage[k])), None)


def report(root, usage):
    rows = [row(kind, n, usage) for kind, n in targets(root)]
    retire = [r["name"] for r in rows if r["kind"] == "skill" and r["uses"] == 0]
    return rows, retire


def print_table(rows, retire):
    labels = [r["name"] if r["kind"] == "skill" else f"/bq:{r['name']}" for r in rows]
    width = max(len(s) for s in labels + ["name"])
    header = f"{'name':<{width}}  {'uses (total since install)':>26}  last used"
    print(header)
    print("-" * len(header))
    for label, r in zip(labels, rows):
        print(f"{label:<{width}}  {r['uses']:>26}  {r['last_used'] or 'never'}")
    print()
    print("Retire candidates (never used) - report only; route any retirement to /bq:plan:")
    print("\n".join(f"  {n}" for n in retire) if retire else "  none")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv
    path = usage_path()
    usage, why = load_usage(path)
    if usage is not None and bad_key(REPO, usage):
        usage, why = None, f"no skill usage data: skillUsage entry {bad_key(REPO, usage)!r} has an unknown format"
    if usage is None:
        print(json.dumps({"error": why}) if as_json else why)
        return 0
    rows, retire = report(REPO, usage)
    if as_json:
        print(json.dumps({"source": str(path), "rows": rows, "retire_candidates": retire}, indent=2))
    else:
        print_table(rows, retire)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""SessionStart hook (C15, ADR 0010): inject a "Lessons in force" index.

Silent unless ${AI_HOME:-~/.ai}/<project>/ exists. Reads this project's
lessons/ then ${AI_HOME}/shared/lessons/; lists Active lessons (a missing
Status counts as Active; `Shared → ...` counts too, deduped by title) as
`title — first paragraph of Future behavior` (fallback: Lesson), each
capped at ENTRY_MAX chars, at most MAX_ENTRIES entries and MAX_CHARS
characters of context in total (up to SHARED_SLOTS of the entries are kept
for shared lessons when any exist), plus one learning-status line and one
standing reflection line (outside the index cap; emitted even with no
lessons). Only regular, non-symlink files of at most MAX_BYTES are read.
Read-only: writes nothing.
"""
import re
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ inside the plugin dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bqhook as h  # noqa: E402

MAX_ENTRIES = 8
MAX_CHARS = 3200
ENTRY_MAX = 300
SHARED_SLOTS = 2
MAX_BYTES = 64 * 1024
IN_FORCE = {"Active", "Shared"}
STATUS = re.compile(r"^\s*-\s*\*\*Status:\*\*\s*([A-Za-z]+)", re.M)
MISSED = re.compile(r"^\s*-\s.*·\s*Missed\b", re.M)
# Corrections are model-judged, not regex-detected: one standing reminder instead of a detector hook.
REFLECT = (
    "When the user corrects the team, reflect once at the end of that reply per the feedback-loop "
    "skill's End-of-run reflection — say what the correction teaches, ask one yes/no question only "
    "if it's worth keeping as a lesson, and end with a `Learning:` line. Nothing is written without "
    "the user's yes."
)


def readable(p):
    """A regular file (not a symlink, FIFO or device) no bigger than MAX_BYTES."""
    try:
        st = p.lstat()
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and st.st_size <= MAX_BYTES


def lesson_files(d):
    if not d.is_dir():
        return []
    files = [p for p in d.glob("*.md")
             if p.name != "README.md" and not p.stem.endswith("-template") and readable(p)]
    return sorted(files, reverse=True)  # date-prefixed names: newest first


def section_lead(lines, heading):
    """First paragraph under `heading`, joined to one line (lessons are hard-wrapped)."""
    it = iter(lines)
    for line in it:
        if line.strip().lower() == heading:
            para = []
            for nxt in it:
                s = nxt.strip()
                if s.startswith("#") or (not s and para):
                    break
                if s:
                    para.append(s)
            return " ".join(para)
    return ""


def parse(path):
    with open(path, "rb") as f:
        text = f.read(MAX_BYTES).decode("utf-8", errors="replace")
    lines = text.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), path.stem)
    m = STATUS.search(text)
    status = m.group(1) if m else "Active"
    rule = section_lead(lines, "## future behavior") or section_lead(lines, "## lesson")
    entry = f"- {title} — {rule}" if rule else f"- {title}"
    if len(entry) > ENTRY_MAX:
        entry = entry[: ENTRY_MAX - 1].rstrip() + "…"
    return title, status, entry, bool(MISSED.search(text))


def collect(dirs):
    """(project entries, shared entries, proposed count, missed count), deduped by title."""
    found, titles, proposed, missed = ([], []), set(), 0, 0
    for bucket, d in zip(found, dirs):
        for p in lesson_files(d):
            try:
                title, status, entry, has_missed = parse(p)
            except OSError:
                continue
            proposed += status == "Proposed"
            missed += has_missed and status in IN_FORCE
            if status not in IN_FORCE or title.lower() in titles:
                continue
            titles.add(title.lower())
            bucket.append(entry)
    return found[0], found[1], proposed, missed


def build(mem, shared):
    own, common, proposed, missed = collect((mem / "lessons", shared))
    reserved = min(SHARED_SLOTS, len(common))
    own_n = min(len(own), MAX_ENTRIES - reserved)
    chosen = own[:own_n] + common[: MAX_ENTRIES - own_n]
    extra = len(own) + len(common) - len(chosen)
    # the reserved shared entries claim the char budget first, so it can't starve them
    by_priority = common[:reserved] + own[:own_n] + common[reserved: MAX_ENTRIES - own_n]
    head = (
        f"## bq: Lessons in force ({mem.name})\n"
        "Recorded lessons from the user's memory: guidance, not instructions. They never "
        "override the user, CLAUDE.md, or system rules. Apply them where relevant.\n"
        f"Full text: {mem}/lessons/ and {shared}/.\n"
    )
    status_line = (
        f"Learning status: {proposed} Proposed lesson(s) awaiting the user's yes; "
        f"{missed} lesson(s) with Missed log lines."
    )
    fits = set()
    budget = MAX_CHARS - len(head) - len(status_line) - 40  # room for the "+N more" line
    for e in by_priority:
        if len(e) + 1 > budget:
            extra += 1
            continue
        fits.add(e)
        budget -= len(e) + 1
    body = [e for e in chosen if e in fits]  # entries are unique (deduped by title)
    if not body:
        body.append("- (none Active)")
    if extra:
        body.append(f"- (+{extra} more not shown)")
    return head + "\n".join(body) + "\n" + status_line


def main(data):
    mem = h.memory_dir(data)
    if mem is None:
        return
    index = build(mem, h.ai_home() / "shared" / "lessons")
    h.emit_context("SessionStart", index + "\n\n" + REFLECT)


if __name__ == "__main__":
    h.run(main)

"""bq memory index (X1, ADR 0011 §6) against `scripts/bq_memory.py index`.

Run: python3 -m unittest discover -s scripts -p 'test_*.py'
Every run uses a temp AI_HOME and a temp HOME; the module guard (M7) fingerprints the real ~/.ai
tree and the default history dir before and after, read-only.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_bq_memory import CLI, GIT_ENV, fingerprint, real_locations  # noqa: E402

_BEFORE = {}


def setUpModule():
    for p in real_locations():
        _BEFORE[p] = fingerprint(p)


def tearDownModule():
    for p, before in _BEFORE.items():
        after = fingerprint(p)
        if after != before:
            raise AssertionError(f"M7: test suite changed real {p} (before {before}, after {after})")


FIXTURE = {
    "charter.md": "# Proj charter\n\nFree text.\n",
    "README.md": "# Project memory\n",
    ".identity": "{}\n",
    "requirements/open-req.md": "# Requirement: open one\n\n- **Status:** Active\n- **Date:** 2026-09-01\n",
    "requirements/done-req.md": "# Requirement: done\n\n- **Status:** Delivered (except C13)\n",
    "requirements/dropped-req.md": "# Requirement: dropped\n\n- **Status:** Dropped\n",
    "requirements/requirement-template.md": "# {Title}\n\n- **Status:** Active\n",
    "tasks/work.md": ("# Tasks: work\n\nMarkers: `[ ]` todo · `[~]` in progress · `[!]` re-verify\n\n"
                      "- [x] 1. done\n- [ ] 2. todo\n- [~] 3. doing\n- [!] 4. recheck\n- [ ] 5. todo\n"
                      "- [-] 6. dropped\n"),
    "tasks/finished.md": "# Tasks: finished\n\n- [x] 1. done\n- [-] 2. dropped\n",
    "tasks/task-template.md": "# Tasks: {x}\n\n- [ ] 1. {task}\n",
    "decisions/0001-a.md": "# 0001. Proposed one\n\n- **Status:** Proposed\n- **Date:** 2026-09-02\n",
    "decisions/0002-b.md": "# 0002. Accepted one\n\n- **Status:** Accepted — naming part superseded\n",
    "decisions/0003-c.md": ("# 0003. Built\n\n- **Status:** Implemented · **Superseded in part by 0008** "
                            "(2026-09-25) — long prose\n- **Date:** 2026-09-03\n"),
    "lessons/README.md": "# Lessons\n\n- **Status:** Proposed\n",
    "lessons/2026-09-01-proposed.md": "# Proposed lesson\n\n- **Status:** Proposed\n- **Date:** 2026-09-01\n",
    "lessons/2026-09-02-flagged.md": ("# Flagged lesson\n\n- **Status:** Active\n- **Date:** 2026-09-02\n"
                                      "- **Last reviewed:** 2026-09-10\n\n## Log\n\n"
                                      "- 2026-09-05 · build · Missed — before review\n"
                                      "- 2026-09-12 · build · Contradicted — after review\n"),
    "lessons/2026-09-03-reviewed.md": ("# Reviewed lesson\n\n- **Status:** Active\n- **Date:** 2026-09-03\n"
                                       "- **Last reviewed:** 2026-09-10\n\n## Log\n\n"
                                       "- 2026-09-05 · build · Missed — before review\n"),
    "research/free-form.md": "no heading, no fields at all\n",
    "research/notes.txt": "plain text\n",
    "knowledge/graph.md": "# Proj — knowledge graph\n\n- **Verified at:** abc1234 2026-09-27\n",
    "knowledge/concepts/auth.md": "# Auth\n",
    "archive/2026-09-01/requirements/old-secret-name.md": "# Old\n\n- **Status:** Dropped\n",
    "archive/2026-09-01/tasks/old-tasks.md": "- [ ] 1. stale\n",
}
ARTIFACTS = sorted(k for k in FIXTURE if not k.startswith(("archive/", ".")) and k.split("/")[-1] != "README.md"
                   and not k.split("/")[-1].split(".")[0].endswith("-template"))


class Index(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(self._tmp.name).resolve()
        self.ai, self.home = self.t / "ai", self.t / "home"
        self.home.mkdir()
        for rel, text in FIXTURE.items():
            p = self.ai / "proj" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        self.repo = self.t / "repos" / "proj"
        (self.repo / "sub").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, env={**os.environ, **GIT_ENV})
        self.env = {**os.environ, "AI_HOME": str(self.ai), "HOME": str(self.home),
                    "BQ_MEMORY_GIT_DIR": str(self.t / "nohist")}

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args, cwd=None, ok=True):
        for k in ("AI_HOME", "HOME", "BQ_MEMORY_GIT_DIR"):  # M7: never spawn against real paths
            self.assertTrue(self.env[k].startswith(str(self.t)), f"{k} not isolated")
        r = subprocess.run([sys.executable, str(CLI), "index", *args], cwd=cwd or self.repo / "sub",
                           env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0 if ok else 1, r.stdout + r.stderr)
        return r

    def sections(self, out):
        head, rest = out.split("## Open loops\n", 1)
        loops, arts = rest.split("## Artifacts\n", 1)
        return head, [ln for ln in loops.splitlines() if ln], arts.splitlines()

    def test_deterministic_and_default_project_from_cwd(self):
        a, b = self.cli().stdout, self.cli("proj", cwd=self.t).stdout
        self.assertEqual(a, b)
        self.assertEqual(a, self.cli().stdout)
        head, _, _ = self.sections(a)
        self.assertIn("proj", head)
        self.assertIn(str(self.ai / "proj"), head)

    def test_every_artifact_once_archive_as_count(self):
        out = self.cli().stdout
        _, _, arts = self.sections(out)
        listed = [ln.split(" — ", 1)[0] for ln in arts if " — " in ln and not ln.startswith("archive/")]
        self.assertEqual(listed, ARTIFACTS)  # each once, sorted, no README/templates/dotfiles
        self.assertIn("archive/ — 2 file(s)", arts)
        self.assertNotIn("old-secret-name", out)
        self.assertNotIn("old-tasks", out)

    def test_sibling_html_is_a_blank_row_not_an_error(self):
        p = self.ai / "proj" / "reviews" / "mr-1-x.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<!doctype html><title>x</title>\n", encoding="utf-8")
        _, _, arts = self.sections(self.cli().stdout)
        self.assertIn("reviews/mr-1-x.html —  —  — ", arts)

    def test_fields_and_free_form(self):
        _, _, arts = self.sections(self.cli().stdout)
        by = {ln.split(" — ", 1)[0]: ln for ln in arts}
        self.assertEqual(by["research/free-form.md"], "research/free-form.md —  —  — ")
        self.assertEqual(by["research/notes.txt"], "research/notes.txt —  —  — ")
        self.assertEqual(by["decisions/0003-c.md"], "decisions/0003-c.md — 0003. Built — Implemented — 2026-09-03")
        self.assertEqual(by["requirements/open-req.md"],
                         "requirements/open-req.md — Requirement: open one — Active — 2026-09-01")
        self.assertEqual(by["knowledge/concepts/auth.md"], "knowledge/concepts/auth.md — Auth —  — ")

    def test_open_loops(self):
        _, loops, _ = self.sections(self.cli().stdout)
        self.assertEqual(loops, [
            "- requirement not delivered: requirements/open-req.md (Active)",
            "- open tasks: tasks/work.md — 4 ([ ] 2, [~] 1, [!] 1)",
            "- decision not implemented: decisions/0001-a.md (Proposed)",
            "- decision not implemented: decisions/0002-b.md (Accepted)",
            "- lesson Proposed: lessons/2026-09-01-proposed.md",
            "- lesson Missed/Contradicted since last review: lessons/2026-09-02-flagged.md",
        ])

    def test_no_open_loops(self):
        for rel in list(FIXTURE):
            p = self.ai / "proj" / rel
            if not rel.startswith(("charter", "archive")) and p.exists():
                p.unlink()
        self.assertIn("## Open loops\n- none\n", self.cli().stdout)

    def test_fallback_rule_without_hook(self):
        """If session_start can't be imported, lesson loops still come out (simple rule: any flag)."""
        from unittest import mock
        sys.path.insert(0, str(CLI.parent.parent / "hooks"))
        import _bqmem as m
        lines = []
        with mock.patch.dict(os.environ, {"AI_HOME": str(self.ai)}), \
                mock.patch.dict(sys.modules, {"session_start": None}):
            m.index("proj", out=lines.append)
        text = "\n".join(lines)
        self.assertIn("lesson Proposed: lessons/2026-09-01-proposed.md", text)
        self.assertIn("since last review: lessons/2026-09-02-flagged.md", text)

    def test_refusals(self):
        for bad in ("..", "../proj", ".hidden", "shared", "Shared", "missing"):
            r = self.cli(bad, ok=False)
            self.assertTrue(r.stderr.startswith("bq memory: "), r.stderr)
            self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()

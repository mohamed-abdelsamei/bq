"""skill_usage.py against fixture .claude.json files (never the real one).

Run: python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import skill_usage  # noqa: E402

NOON_2026_09_01 = 1788264000000  # 2026-09-01T12:00:00Z, so the date is timezone-proof
NOON_2026_09_20 = 1789905600000  # 2026-09-20T12:00:00Z


class SkillUsage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / ".claude.json"
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env["BQ_CLAUDE_JSON"] = str(self.path)
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def write(self, data):
        self.path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = skill_usage.main(list(argv))
        return code, out.getvalue()

    def usage(self, **entries):
        return {"skillUsage": {k: {"usageCount": n, "lastUsedAt": t} for k, (n, t) in entries.items()}}

    def test_table_counts_plugin_and_manual_keys(self):
        self.write(self.usage(**{
            "bq:debugging": (3, NOON_2026_09_01),
            "bq-debugging": (2, NOON_2026_09_20),   # manual install, same skill
            "bq:plan": (4, NOON_2026_09_01),
            "bq:bq-team": (1, NOON_2026_09_01),
            "debugging": (50, NOON_2026_09_20),     # bare key: ambiguous, not counted
            "init": (9, NOON_2026_09_20),           # built-in /init, not /bq:init
        }))
        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("uses (total since install)", out)
        line = next(l for l in out.splitlines() if l.startswith("debugging "))
        self.assertEqual(line.split()[1:], ["5", "2026-09-20"])
        self.assertEqual(next(l for l in out.splitlines() if l.startswith("/bq:plan ")).split()[1:],
                         ["4", "2026-09-01"])
        self.assertEqual(next(l for l in out.splitlines() if l.startswith("/bq:init ")).split()[1:],
                         ["0", "never"])
        self.assertEqual(next(l for l in out.splitlines() if l.startswith("bq-team ")).split()[1], "1")

    def test_retire_candidates_are_unused_skills_only(self):
        self.write(self.usage(**{"bq:debugging": (1, NOON_2026_09_01)}))
        code, out = self.run_main("--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        skills, commands = skill_usage.bq_names(skill_usage.REPO)
        self.assertNotIn("debugging", data["retire_candidates"])
        self.assertEqual(sorted(data["retire_candidates"]), sorted(set(skills) - {"debugging"}))
        self.assertFalse(set(data["retire_candidates"]) & (set(commands) - set(skills)))
        self.assertEqual(len(data["rows"]), len(skills) + len(commands))
        row = next(r for r in data["rows"] if r["name"] == "debugging")
        self.assertEqual((row["kind"], row["uses"], row["last_used"]), ("skill", 1, "2026-09-01"))
        _, text = self.run_main()
        self.assertIn("Retire candidates (never used)", text)
        self.assertIn("\n  critique\n", text)

    def test_zero_count_entry_is_a_retire_candidate(self):
        self.write(self.usage(**{"bq:critique": (0, NOON_2026_09_01)}))
        _, out = self.run_main("--json")
        self.assertIn("critique", json.loads(out)["retire_candidates"])

    def assertOneLine(self, fragment, *argv):
        code, out = self.run_main(*argv)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn(fragment, out)
        return out

    def test_missing_file(self):
        self.assertOneLine("not found")

    def test_bad_json(self):
        self.write("{not json")
        self.assertOneLine("cannot read")

    def test_not_utf8(self):
        self.path.write_bytes(b"\xff\xfe{}")
        self.assertOneLine("cannot read")

    def test_missing_key(self):
        self.write({"numStartups": 3})
        self.assertOneLine("no skillUsage")

    def test_top_level_not_object(self):
        self.write([1, 2])
        self.assertOneLine("no skillUsage")

    def test_skill_usage_not_object(self):
        self.write({"skillUsage": ["bq:plan"]})
        self.assertOneLine("no skillUsage")

    def test_unknown_entry_shape(self):
        for entry in ({"count": 1}, {"usageCount": "1", "lastUsedAt": 1}, {"usageCount": True, "lastUsedAt": 1}, 5):
            self.write({"skillUsage": {"bq:plan": entry}})
            self.assertOneLine("unknown format")

    def test_json_mode_failure_is_one_json_line(self):
        out = self.assertOneLine("not found", "--json")
        self.assertIn("error", json.loads(out))

    def test_path_resolution(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/cfg"}, clear=True):
            self.assertEqual(skill_usage.usage_path(), Path("/cfg/.claude.json"))
        with mock.patch.dict(os.environ, {"HOME": "/home/u"}, clear=True):
            self.assertEqual(skill_usage.usage_path(), Path("/home/u/.claude.json"))
        with mock.patch.dict(os.environ, {"BQ_CLAUDE_JSON": "/x.json", "CLAUDE_CONFIG_DIR": "/cfg"}, clear=True):
            self.assertEqual(skill_usage.usage_path(), Path("/x.json"))


if __name__ == "__main__":
    unittest.main()

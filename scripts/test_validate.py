"""Seed defects into a temp copy of the repo and prove validate.py catches each one.

Run: python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import validate  # noqa: E402


class SeededDefects(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        shutil.copytree(REPO, self.root, ignore=shutil.ignore_patterns(".git"))
        self.baseline = validate.run(self.root).fails

    def tearDown(self):
        self._tmp.cleanup()

    # helpers
    def edit(self, rel, old, new, count=1):
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text, f"seed anchor not found in {rel}")
        p.write_text(text.replace(old, new, count), encoding="utf-8")

    def assertCaught(self, expected_substring):
        """The seeded run must FAIL with this message; the unseeded copy must not."""
        self.assertFalse(
            any(expected_substring in f for f in self.baseline),
            f"baseline already contains {expected_substring!r}: {self.baseline}",
        )
        rep = validate.run(self.root)
        self.assertTrue(
            any(expected_substring in f for f in rep.fails),
            f"expected FAIL containing {expected_substring!r}, got: {rep.fails}",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validate.main([str(self.root)]), 1)

    # tests
    def test_clean_copy_passes(self):
        self.assertEqual(self.baseline, [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validate.main([str(self.root)]), 0)

    def test_agent_name_mismatch(self):
        self.edit("agents/tester.md", "name: tester", "name: qa")
        self.assertCaught("FAIL: agents/tester.md: name 'qa' must equal filename stem 'tester'")

    def test_agent_tool_on_specialist(self):
        self.edit("agents/engineer.md", "tools: Read,", "tools: Agent, Read,")
        self.assertCaught("FAIL: agents/engineer.md: tool 'Agent' is only allowed in maestro")

    def test_task_tool_on_specialist(self):
        self.edit("agents/scribe.md", "tools: Read,", "tools: Task, Read,")
        self.assertCaught("FAIL: agents/scribe.md: tool 'Task' is only allowed in maestro")

    def test_missing_tools_line(self):
        p = self.root / "agents/researcher.md"
        p.write_text(re.sub(r"(?m)^tools:.*\n", "", p.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        self.assertCaught("FAIL: agents/researcher.md: missing 'tools:' line")

    def test_todowrite_and_unknown_tool(self):
        self.edit("agents/architect.md", "tools: Read,", "tools: TodoWrite, Frobnicate, Read,")
        self.assertCaught("FAIL: agents/architect.md: TodoWrite is not allowed")
        self.assertCaught("FAIL: agents/architect.md: unknown tool 'Frobnicate'")

    def test_unknown_model(self):
        self.edit("agents/reviewer.md", "model: inherit", "model: gpt-4")
        self.assertCaught("FAIL: agents/reviewer.md: unknown model 'gpt-4'")

    def test_version_mismatch(self):
        p = self.root / ".claude-plugin/plugin.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["version"] = "9.9.9"
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertCaught("FAIL: .claude-plugin/marketplace.json: plugin 'bq' version")
        self.assertCaught("FAIL: .claude-plugin/marketplace.json: metadata.version")

    def test_non_semver_version(self):
        p = self.root / ".claude-plugin/plugin.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["version"] = "v1"
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertCaught("FAIL: .claude-plugin/plugin.json: version 'v1' is not semver")

    def test_marketplace_missing_source(self):
        p = self.root / ".claude-plugin/marketplace.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        for entry in data["plugins"]:
            entry.pop("source", None)
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertCaught("FAIL: .claude-plugin/marketplace.json: plugin 'bq' entry missing 'source'")

    def test_copilot_syntax_in_command(self):
        self.edit("commands/plan.md", "$ARGUMENTS", "${input:args}")
        self.assertCaught("FAIL: commands/plan.md: contains Copilot syntax '${input'")

    def test_unbalanced_marker(self):
        self.edit("agents/maestro.md", "<!-- /claude-only -->", "")
        self.assertCaught("FAIL: agents/maestro.md: unclosed <!-- claude-only -->")

    def test_stray_close_marker(self):
        p = self.root / "docs/architecture.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- /claude-only -->\n", encoding="utf-8")
        self.assertCaught("FAIL: docs/architecture.md: line")

    def test_dangling_command_ref(self):
        p = self.root / "skills/memory/SKILL.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nSee /bq:foo.\n", encoding="utf-8")
        self.assertCaught("FAIL: skills/memory/SKILL.md: references /bq:foo but commands/foo.md does not exist")

    def test_dangling_plugin_agent_ref(self):
        p = self.root / "commands/build.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nDelegate to `bq:foo`.\n", encoding="utf-8")
        self.assertCaught("FAIL: commands/build.md: references agent 'bq:foo'")

    def test_stale_prefixed_plugin_agent_ref(self):
        # pre-ADR-0007 name: the plugin now exposes bq:architect, not bq:bq-architect
        p = self.root / "commands/plan.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nSpawn `bq:bq-architect`.\n", encoding="utf-8")
        self.assertCaught("FAIL: commands/plan.md: references agent 'bq:bq-architect'")

    def test_dangling_bare_agent_ref(self):
        p = self.root / "agents/maestro.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nAsk bq-designer.\n", encoding="utf-8")
        self.assertCaught("FAIL: agents/maestro.md: references agent 'bq-designer'")

    def test_skill_name_mismatch(self):
        self.edit("skills/critique/SKILL.md", "name: critique", "name: red-team")
        self.assertCaught("FAIL: skills/critique/SKILL.md: skill name 'red-team' must match folder 'critique'")

    def test_readme_missing_command(self):
        (self.root / "commands/newcmd.md").write_text(
            "---\ndescription: 'x'\n---\nYou are the Maestro.\n", encoding="utf-8"
        )
        self.assertCaught("FAIL: README.md: missing command reference /bq:newcmd")

    def test_missing_template(self):
        (self.root / "templates/bq/charter.md").unlink()
        self.assertCaught("FAIL: templates/bq/charter.md: missing memory template")

    def test_warnings_do_not_fail(self):
        long_desc = "x" * 1100
        self.edit("skills/debugging/SKILL.md", "description: '", f"description: '{long_desc}")
        rep = validate.run(self.root)
        self.assertEqual(rep.fails, [])
        self.assertTrue(any("skills/debugging/SKILL.md: description is" in w for w in rep.warns), rep.warns)


    def append(self, rel, text):
        p = self.root / rel
        p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")

    # 1. non-slash bq:<x> is checked in docs/ and README.md; bare bq-x is not
    def test_plugin_agent_ref_in_docs(self):
        self.append("docs/architecture.md", "\nSpawn `bq:designer`.\n")
        self.assertCaught("FAIL: docs/architecture.md: references agent 'bq:designer'")

    def test_plugin_agent_ref_in_readme(self):
        self.append("README.md", "\nSpawn `bq:designer`.\n")
        self.assertCaught("FAIL: README.md: references agent 'bq:designer'")

    def test_bare_ref_in_docs_is_allowed(self):
        self.append("docs/USAGE.md", "\nCopilot: bq-designer\n")
        self.append("README.md", "\nCopilot: bq-designer\n")
        self.assertEqual(validate.run(self.root).fails, [])

    def test_plugin_agent_ref_skips_templates(self):
        self.append("templates/bq/README.md", "\nSpawn `bq:designer`.\n")
        self.assertEqual(validate.run(self.root).fails, [])

    # 2. README command check is exact, not substring
    def test_readme_command_not_satisfied_by_longer_name(self):
        (self.root / "commands/review-m.md").write_text(
            "---\ndescription: 'x'\n---\nYou are the Maestro.\n", encoding="utf-8"
        )
        self.assertIn("/bq:review-mr", (self.root / "README.md").read_text(encoding="utf-8"))
        self.assertCaught("FAIL: README.md: missing command reference /bq:review-m")

    # 3. messages
    def test_plugin_ref_to_command_suggests_slash(self):
        self.append("commands/build.md", "\nRun bq:plan first.\n")
        self.assertCaught("FAIL: commands/build.md: references 'bq:plan', which looks like a command — did you mean /bq:plan?")

    def test_plugin_ref_message_names_agent_and_skill(self):
        self.append("commands/build.md", "\nDelegate to `bq:foo`.\n")
        self.assertCaught("no agents/foo.md or skills/foo/ exists")

    def test_bare_ref_message_names_unprefixed_file(self):
        self.append("agents/maestro.md", "\nAsk bq-designer.\n")
        self.assertCaught("FAIL: agents/maestro.md: references agent 'bq-designer' but agents/designer.md does not exist")

    # 4. separate seen sets per pass
    def test_seen_sets_are_per_pass(self):
        # the plugin pass reporting `bq:bq-foo` must not hide bare `bq-foo` from the bare pass
        self.append("agents/maestro.md", "\nSpawn `bq:bq-foo`, or ask bq-foo.\n")
        rep = validate.run(self.root)
        self.assertTrue(any("references agent 'bq:bq-foo'" in f for f in rep.fails), rep.fails)
        self.assertTrue(any("references agent 'bq-foo'" in f for f in rep.fails), rep.fails)

    # 5. robust reads, BOM, plugins type
    def test_bom_before_frontmatter_passes(self):
        p = self.root / "agents/tester.md"
        p.write_text("\ufeff" + p.read_text(encoding="utf-8"), encoding="utf-8")
        p = self.root / ".claude-plugin/plugin.json"
        p.write_text("\ufeff" + p.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(validate.run(self.root).fails, [])

    def test_non_utf8_file_fails_cleanly(self):
        p = self.root / "skills/memory/SKILL.md"
        p.write_bytes(p.read_bytes() + b"\n\xff\xfe bad bytes\n")
        self.assertCaught("FAIL: skills/memory/SKILL.md: not valid UTF-8")
        rep = validate.run(self.root)
        self.assertEqual(sum("not valid UTF-8" in f for f in rep.fails), 1, rep.fails)

    def test_plugins_not_a_list(self):
        p = self.root / ".claude-plugin/marketplace.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["plugins"] = {"name": "bq"}
        p.write_text(json.dumps(data), encoding="utf-8")
        self.assertCaught("FAIL: .claude-plugin/marketplace.json: 'plugins' must be a list (got dict)")

    # 6. frontmatter limits and tool forms
    def test_block_scalar_description_fails(self):
        p = self.root / "agents/tester.md"
        p.write_text(re.sub(r"(?m)^description:.*$", "description: >\n  folded text", p.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        self.assertCaught("FAIL: agents/tester.md: frontmatter 'description' is a block scalar (>)")

    def test_yaml_list_tools_fails(self):
        p = self.root / "agents/tester.md"
        p.write_text(re.sub(r"(?m)^tools:.*$", "tools:\n  - Read\n  - Grep", p.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        self.assertCaught("FAIL: agents/tester.md: frontmatter 'tools' is a YAML list or nested map")

    def test_mcp_and_scoped_bash_tools_accepted(self):
        self.edit("agents/engineer.md", "tools: Read,", "tools: mcp__github__get_issue, Bash(git:*), Read,")
        self.assertEqual(validate.run(self.root).fails, [])

    def test_scoped_tool_base_name_is_validated(self):
        self.edit("agents/engineer.md", "tools: Read,", "tools: Frob(git:*), Read,")
        self.assertCaught("FAIL: agents/engineer.md: unknown tool 'Frob'")

    # 7. /bq: refs in templates
    def test_dangling_command_ref_in_template(self):
        self.append("templates/bq/README.md", "\nRun /bq:nope.\n")
        self.assertCaught("FAIL: templates/bq/README.md: references /bq:nope but commands/nope.md does not exist")

    # 8. lookbehinds
    def test_urls_and_assignments_are_not_refs(self):
        self.append("docs/architecture.md", "\nhttps://x.com/bq:foo and subagent_type=bq:foo\n")
        self.assertEqual(validate.run(self.root).fails, [])

    # 9. CRLF
    def test_crlf_files_pass(self):
        for rel in ("agents/tester.md", "commands/plan.md", "skills/memory/SKILL.md"):
            p = self.root / rel
            p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assertEqual(validate.run(self.root).fails, [])


class Frontmatter(unittest.TestCase):
    def test_quoted_escape(self):
        fm, body = validate.parse_frontmatter("---\ndescription: 'Sol''s job: design'\n---\nbody\n")
        self.assertEqual(fm, {"description": "Sol's job: design"})
        self.assertEqual(body, "body\n")

    def test_crlf(self):
        fm, body = validate.parse_frontmatter("---\r\nname: x\r\n---\r\nbody\r\n")
        self.assertEqual(fm, {"name": "x"})
        self.assertEqual(body, "body\r\n")

    def test_bom(self):
        fm, _ = validate.parse_frontmatter("\ufeff---\nname: x\n---\n")
        self.assertEqual(fm, {"name": "x"})

    def test_unsupported_values_are_flagged(self):
        fm, _ = validate.parse_frontmatter(
            "---\na: |\n  x\nb: [x, y]\nc:\n  - x\nd: one\n  two\ne: ok\n---\n"
        )
        for k in "abcd":
            self.assertIsInstance(fm[k], validate.Unsupported, k)
        self.assertEqual(fm["e"], "ok")

    def test_unterminated(self):
        fm, _ = validate.parse_frontmatter("---\nname: x\n")
        self.assertIsNone(fm)


if __name__ == "__main__":
    unittest.main()

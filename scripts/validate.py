#!/usr/bin/env python3
"""Validate the bq plugin's structure. Stdlib only, python3 >= 3.9.

Usage: python3 scripts/validate.py [REPO_ROOT]

Prints FAIL/WARN lines with file paths; exits 1 if any FAIL, else 0.
CI runs exactly this command.
"""
import json
import re
import sys
from pathlib import Path

KNOWN_MODELS = {"inherit", "sonnet", "opus", "haiku", "fable"}
KNOWN_TOOLS = {
    "Read", "Grep", "Glob", "Edit", "Write", "Bash", "WebFetch", "WebSearch",
    "Agent", "Task", "Skill", "NotebookEdit", "LSP", "ToolSearch", "Monitor",
    "TaskCreate", "TaskUpdate", "TaskGet", "TaskList",
}
DELEGATION_TOOLS = {"Agent", "Task"}
ORCHESTRATOR = "maestro"
# Agent Skills spec caps description at 1024 chars; warn only.
SKILL_DESC_MAX = 1024
# Skills that load often and have grown; warn (like `wc -w`) so a split is considered, not forced.
SKILL_WORDS_MAX = {"feedback-loop": 1900}
REQUIRED_TEMPLATES = [
    "README.md",
    "charter.md",
    "decision-template.md",
    "discussions/discussion-template.md",
    "lessons/README.md",
    "lessons/lesson-template.md",
    "requirements/requirement-template.md",
    "research/research-template.md",
    "reviews/review-template.md",
    "tasks/task-template.md",
]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
MARKER = re.compile(r"<!--\s*(/?)claude-only\s*-->")
# Plugin-scoped `bq:x` (no leading slash — that's a command) must name an agent or skill;
# bare `bq-x` is the manual/Copilot install name, valid for an agent `x` or a skill.
PLUGIN_AGENT_REF = re.compile(r"(?<![\w/=])bq:([a-z][a-z0-9-]*)")
BARE_AGENT_REF = re.compile(r"(?<![\w/.:-])bq-([a-z][a-z0-9-]*)")
# Lookbehind skips URLs/paths such as https://x.com/bq:foo.
COMMAND_REF = re.compile(r"(?<![\w/.])/bq:([a-z][a-z0-9-]*)")
# Frontmatter keys the checks read; a value the mini-parser can't represent is a FAIL.
CHECKED_KEYS = {"name", "description", "model", "tools", "argument-hint"}
# The lesson format lives in both files: the skill's fenced block (first line `# {Lesson title}`)
# and the template. Their `- **X:**` field lines and `## Log` format line must agree exactly.
LESSON_SKILL = "skills/feedback-loop/SKILL.md"
LESSON_TEMPLATE = "templates/bq/lessons/lesson-template.md"
LESSON_BLOCK_START = "# {Lesson title}"
FIELD_LINE = re.compile(r"^- \*\*([^*]+):\*\*")
# A state's name is the text before its placeholder: `Shared → {file}`, `Superseded by {slug}`.
STATE_NAME = re.compile(r"\s+(?:→|by|—)\s.*$")
# `Name` or `Name(pattern)`, e.g. `Bash(git:*)`; commas inside parens don't split.
TOOL_ITEM = re.compile(r"\s*([^,(]+?)\s*(\([^)]*\))?\s*(?:,|$)")

# Hook events bq may use; anything else is likely a typo (WARN only: the platform list grows).
HOOKS_JSON = "hooks/hooks.json"
KNOWN_HOOK_EVENTS = {
    "SessionStart", "SessionEnd", "UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart",
    "PreToolUse", "PostToolUse", "Notification", "PreCompact",
}
HOOK_TIMEOUT_MAX = 5
PLUGIN_ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)")
# The one command shape bq ships: quoted so a plugin root with spaces still works, python3, no args.
HOOK_COMMAND = re.compile(r'python3 "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/[\w.-]+\.py"')
# Hooks make no network calls and spawn nothing (ADR 0010); an import of these is suspicious.
HOOK_BANNED_IMPORT = re.compile(r"^\s*(?:import\s+(?:[\w.]+\s*,\s*)*|from\s+)(socket|urllib|http|subprocess)\b", re.M)


class Report:
    def __init__(self, root):
        self.root = root
        self.fails = []
        self.warns = []
        self.texts = {}  # path -> text, or None if unreadable (see read_text)

    def _rel(self, path):
        try:
            return str(Path(path).relative_to(self.root))
        except ValueError:
            return str(path)

    def fail(self, path, msg):
        self.fails.append(f"FAIL: {self._rel(path)}: {msg}")

    def warn(self, path, msg):
        self.warns.append(f"WARN: {self._rel(path)}: {msg}")


def read_text(rep, path):
    """Read UTF-8 text (leading BOM stripped), or FAIL once and return None.

    Cached per path so several checks reading one file report one decode failure.
    """
    cache = rep.texts
    if path not in cache:
        try:
            cache[path] = path.read_text(encoding="utf-8").removeprefix("\ufeff")
        except UnicodeDecodeError as e:
            rep.fail(path, f"not valid UTF-8 ({e})")
            cache[path] = None
    return cache[path]


class Unsupported(str):
    """A frontmatter value the mini-parser cannot represent; the str is the reason."""


def parse_frontmatter(text):
    """Return (dict, body) or (None, text) if frontmatter is missing or never closed.

    A deliberately tiny YAML subset, not a YAML parser:
      - one `key: value` per line; values are plain, 'single-' or "double-quoted" strings;
      - blank lines and `#` comment lines are skipped; a leading UTF-8 BOM is ignored;
      - LF and CRLF line endings both work.
    Not supported: block scalars (`key: >` / `key: |`), block or flow lists
    (`- item` lines, `[a, b]`), nested maps, and multi-line (indented continuation)
    values. Those keys are returned as an `Unsupported` value (reason string) so a
    caller can FAIL explicitly instead of misreading them.
    """
    text = text.removeprefix("\ufeff")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, text
    fm = {}
    last = None
    for i in range(1, len(lines)):
        line = lines[i].rstrip("\r\n")
        if line == "---":
            return fm, "".join(lines[i + 1:])
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t" or line.startswith("- "):
            # Continuation of the previous key: a block list/map or a folded plain scalar.
            if last is not None and not isinstance(fm[last], Unsupported):
                kind = "a YAML list or nested map" if fm[last] == "" else "a multi-line value"
                fm[last] = Unsupported(kind)
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        last = key
        if value[:1] in (">", "|"):
            fm[key] = Unsupported(f"a block scalar ({value})")
            continue
        if value.startswith("["):
            fm[key] = Unsupported("a YAML flow list")
            continue
        if len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        elif len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace('\\"', '"')
        fm[key] = value
    return None, text  # never closed


def load_md(rep, path):
    """Parse frontmatter; FAIL and return (None, body) if absent or unrepresentable."""
    text = read_text(rep, path)
    if text is None:
        return None, ""
    fm, body = parse_frontmatter(text)
    if fm is None:
        rep.fail(path, "missing or unterminated frontmatter")
        return None, body
    bad = sorted(k for k in CHECKED_KEYS if isinstance(fm.get(k), Unsupported))
    for k in bad:
        rep.fail(path, f"frontmatter '{k}' is {fm[k]}; the validator only supports "
                       f"single-line '{k}: value' (use a quoted one-line string)")
    return (None if bad else fm), body


def load_json(rep, path, required):
    if not path.exists():
        rep.fail(path, "missing")
        return None
    text = read_text(rep, path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        rep.fail(path, f"invalid JSON ({e})")
        return None
    if not isinstance(data, dict):
        rep.fail(path, "top level must be an object")
        return None
    for key in required:
        if key not in data:
            rep.fail(path, f"missing required key '{key}'")
    return data


def check_manifests(rep, root):
    ppath = root / ".claude-plugin" / "plugin.json"
    mpath = root / ".claude-plugin" / "marketplace.json"
    plugin = load_json(rep, ppath, ["name", "version"])
    market = load_json(rep, mpath, ["name", "plugins"])

    pver = None
    if plugin:
        if plugin.get("name") != "bq":
            rep.fail(ppath, f"name must be 'bq' (got {plugin.get('name')!r})")
        pver = plugin.get("version")
        if pver is not None and not SEMVER.match(str(pver)):
            rep.fail(ppath, f"version {pver!r} is not semver (X.Y.Z)")
    if not market:
        return
    if "plugins" not in market:
        return  # already reported as a missing required key
    plugins = market["plugins"]
    if not isinstance(plugins, list):
        rep.fail(mpath, f"'plugins' must be a list (got {type(plugins).__name__})")
        return
    entry = next((p for p in plugins if isinstance(p, dict) and p.get("name") == "bq"), None)
    if entry is None:
        rep.fail(mpath, "plugins must list 'bq'")
    else:
        if not entry.get("source"):
            rep.fail(mpath, "plugin 'bq' entry missing 'source'")
        ever = entry.get("version")
        if ever is None:
            rep.fail(mpath, "plugin 'bq' entry missing 'version'")
        elif not SEMVER.match(str(ever)):
            rep.fail(mpath, f"plugin 'bq' version {ever!r} is not semver (X.Y.Z)")
        elif pver is not None and ever != pver:
            rep.fail(mpath, f"plugin 'bq' version {ever!r} != plugin.json version {pver!r}")
    meta = market.get("metadata")
    if isinstance(meta, dict) and "version" in meta and pver is not None and meta["version"] != pver:
        rep.fail(mpath, f"metadata.version {meta['version']!r} != plugin.json version {pver!r}")


def check_agents(rep, root):
    files = sorted((root / "agents").glob("*.md"))
    if not files:
        rep.fail(root / "agents", "no *.md files found")
    for f in files:
        fm, _ = load_md(rep, f)
        if fm is None:
            continue
        name = fm.get("name")
        if not name:
            rep.fail(f, "frontmatter missing name")
        elif name != f.stem:
            rep.fail(f, f"name {name!r} must equal filename stem {f.stem!r}")
        if not fm.get("description"):
            rep.fail(f, "frontmatter missing description")
        model = fm.get("model")
        if model is not None and model not in KNOWN_MODELS and not model.startswith("claude-"):
            rep.fail(f, f"unknown model {model!r} (want one of {sorted(KNOWN_MODELS)} or claude-*)")
        if "tools" not in fm:
            rep.fail(f, "missing 'tools:' line (omitting it inherits every tool, including Agent)")
            continue
        tools = [m.group(1) for m in TOOL_ITEM.finditer(fm["tools"]) if m.group(1)]
        if not tools:
            rep.fail(f, "'tools:' is empty")
        for t in tools:
            if t.startswith("mcp__"):
                continue
            if t == "TodoWrite":
                rep.fail(f, "TodoWrite is not allowed (use TaskCreate/TaskUpdate)")
            elif t not in KNOWN_TOOLS:
                rep.fail(f, f"unknown tool {t!r}")
            elif t in DELEGATION_TOOLS and f.stem != ORCHESTRATOR:
                rep.fail(f, f"tool {t!r} is only allowed in {ORCHESTRATOR} (keeps orchestration single-level)")


def check_commands(rep, root):
    files = sorted((root / "commands").glob("*.md"))
    if not files:
        rep.fail(root / "commands", "no *.md files found")
    for f in files:
        fm, body = load_md(rep, f)
        if fm is None:
            continue
        if not fm.get("description"):
            rep.fail(f, "frontmatter missing description")
        if "${input" in body:
            rep.fail(f, "contains Copilot syntax '${input' (use $ARGUMENTS)")
        if fm.get("argument-hint") and "$ARGUMENTS" not in body:
            rep.warn(f, "has argument-hint but body never references $ARGUMENTS")


def check_skills(rep, root):
    files = sorted((root / "skills").glob("*/SKILL.md"))
    if not files:
        rep.fail(root / "skills", "no */SKILL.md files found")
    for f in files:
        fm, _ = load_md(rep, f)
        if fm is None:
            continue
        folder = f.parent.name
        if fm.get("name") != folder:
            rep.fail(f, f"skill name {fm.get('name')!r} must match folder {folder!r}")
        desc = fm.get("description")
        if not desc:
            rep.fail(f, "frontmatter missing description")
        elif len(desc) > SKILL_DESC_MAX:
            rep.warn(f, f"description is {len(desc)} chars (> {SKILL_DESC_MAX}); may be truncated")
        cap = SKILL_WORDS_MAX.get(folder)
        words = len((read_text(rep, f) or "").split()) if cap else 0
        if cap and words > cap:
            rep.warn(f, f"{words} words (> {cap} words); consider splitting it into its own skill")


def doc_files(root):
    """Markdown the plugin ships or documents (not shell scripts)."""
    files = []
    for d in ("agents", "commands", "skills", "docs", "templates"):
        files += sorted((root / d).rglob("*.md"))
    readme = root / "README.md"
    if readme.exists():
        files.append(readme)
    return files


def check_markers(rep, root):
    for f in doc_files(root):
        depth = 0
        text = read_text(rep, f)
        if text is None:
            continue
        for m in MARKER.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            if m.group(1):  # close
                if depth == 0:
                    rep.fail(f, f"line {line}: <!-- /claude-only --> without matching open")
                else:
                    depth -= 1
            else:
                if depth:
                    rep.fail(f, f"line {line}: nested <!-- claude-only --> (previous block not closed)")
                depth += 1
        if depth:
            rep.fail(f, "unclosed <!-- claude-only --> at end of file")


def check_readme_and_templates(rep, root):
    readme = root / "README.md"
    if not readme.exists():
        rep.fail(readme, "missing")
    else:
        text = read_text(rep, readme) or ""
        for c in sorted(p.stem for p in (root / "commands").glob("*.md")):
            # Exact match: /bq:review must not be satisfied by /bq:review-mr.
            if not re.search(rf"/bq:{re.escape(c)}(?![\w-])", text):
                rep.fail(readme, f"missing command reference /bq:{c}")
    for rel in REQUIRED_TEMPLATES:
        p = root / "templates" / "bq" / rel
        if not p.exists():
            rep.fail(p, "missing memory template")


def check_cross_refs(rep, root):
    agents = {p.stem for p in (root / "agents").glob("*.md")}
    skills = {p.name for p in (root / "skills").iterdir() if p.is_dir()} if (root / "skills").is_dir() else set()
    commands = {p.stem for p in (root / "commands").glob("*.md")}

    all_docs = doc_files(root)

    def in_templates(f):
        return f.parts[len(root.parts)] == "templates"

    def in_personas(f):
        return f.parts[len(root.parts)] in ("agents", "commands", "skills")

    for f in all_docs:
        text = read_text(rep, f)
        if text is None:
            continue

        # 1. Plugin-scoped `bq:x` (no slash): agents/commands/skills plus docs and README.
        if not in_templates(f):
            seen = set()
            for m in PLUGIN_AGENT_REF.finditer(text):
                name = m.group(1)
                if name in agents or name in skills or name in seen:
                    continue
                seen.add(name)
                if name in commands:
                    rep.fail(f, f"references 'bq:{name}', which looks like a command — did you mean /bq:{name}?")
                else:
                    rep.fail(f, f"references agent 'bq:{name}' but no agents/{name}.md or skills/{name}/ exists")

        # 2. Bare `bq-x`: persona files only (README/USAGE legitimately list Copilot names).
        if in_personas(f):
            seen = set()
            for m in BARE_AGENT_REF.finditer(text):
                x = m.group(1)
                if x in agents or x in skills or f"bq-{x}" in skills or x in seen:
                    continue
                seen.add(x)
                rep.fail(f, f"references agent 'bq-{x}' but agents/{x}.md does not exist")

        # 3. `/bq:x` commands: everywhere, templates included.
        seen = set()
        for m in COMMAND_REF.finditer(text):
            c = m.group(1)
            if c not in commands and c not in seen:
                seen.add(c)
                rep.fail(f, f"references /bq:{c} but commands/{c}.md does not exist")


def lesson_block(text):
    """Lines of the fenced block whose first line starts `# {Lesson title}`, or None."""
    block, in_fence = None, False
    for line in text.splitlines():
        s = line.rstrip()
        if s.startswith("```"):
            if block is not None:
                return block
            in_fence = not in_fence
            first = in_fence
        elif in_fence and first:
            first = False
            if s.startswith(LESSON_BLOCK_START):
                block = [s]
        elif block is not None:
            block.append(s)
    return None


def lesson_fields(rep, path, lines):
    """[(name, line)] for `- **X:**` lines; FAIL on a duplicated field name."""
    fields, seen = [], set()
    for line in lines:
        m = FIELD_LINE.match(line)
        if not m:
            continue
        if m.group(1) in seen:
            rep.fail(path, f"duplicate '- **{m.group(1)}:**' field line in the lesson format")
        seen.add(m.group(1))
        fields.append((m.group(1), line))
    return fields


def log_format(lines):
    """First non-blank line after `## Log`, or None."""
    it = iter(lines)
    for line in it:
        if line == "## Log":
            return next((l for l in it if l.strip()), None)
    return None


def state_name(entry):
    return STATE_NAME.sub("", entry.strip())


def states_table(lines):
    """State names from the table headed `| State | ...`, or None if absent."""
    names = None
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if names is None:
            if line.startswith("|") and cells[0] == "State":
                names = []
        elif not line.startswith("|"):
            break
        elif not set(cells[0]) <= set("-: "):
            names.append(state_name(cells[0]))
    return names


def check_lesson_format(rep, root):
    """The skill's lesson format and the template agree; the states table matches the Status list."""
    skill, tmpl = root / LESSON_SKILL, root / LESSON_TEMPLATE
    texts = {}
    for p in (skill, tmpl):
        if not p.exists():
            rep.fail(p, f"missing (its lesson format must match {LESSON_SKILL if p == tmpl else LESSON_TEMPLATE})")
        else:
            texts[p] = read_text(rep, p)
    if texts.get(skill) is None or texts.get(tmpl) is None:
        return
    skill_all = [l.rstrip() for l in texts[skill].splitlines()]
    block = lesson_block(texts[skill])
    if block is None:
        rep.fail(skill, f"no fenced lesson-format block whose first line is '{LESSON_BLOCK_START}'")
        return
    tmpl_lines = [l.rstrip() for l in texts[tmpl].splitlines()]

    # 1. field block: same fields, same text, same order
    sf, tf = lesson_fields(rep, skill, block), lesson_fields(rep, tmpl, tmpl_lines)
    s_map, t_map = dict(sf), dict(tf)
    for name, _ in tf:
        if name not in s_map:
            rep.fail(tmpl, f"field '- **{name}:**' is not in the {LESSON_SKILL} lesson format")
    for name, _ in sf:
        if name not in t_map:
            rep.fail(skill, f"lesson-format field '- **{name}:**' is not in {LESSON_TEMPLATE}")
    for name, line in tf:
        if name in s_map and s_map[name] != line:
            rep.fail(tmpl, f"'- **{name}:**' line differs from {LESSON_SKILL}: {line!r} != {s_map[name]!r}")
    common = [n for n, _ in sf if n in t_map]
    if common != [n for n, _ in tf if n in s_map]:
        rep.fail(tmpl, f"lesson field order differs from {LESSON_SKILL}: expected {common}")

    # 2. the `## Log` format line
    s_log, t_log = log_format(block), log_format(tmpl_lines)
    for p, log in ((skill, s_log), (tmpl, t_log)):
        if log is None:
            rep.fail(p, "lesson format has no '## Log' section with a format line")
    if s_log is not None and t_log is not None and s_log != t_log:
        rep.fail(tmpl, f"'## Log' format line differs from {LESSON_SKILL}: {t_log!r} != {s_log!r}")

    # 3. the lesson-states table names exactly the Status states
    table = states_table(skill_all)
    if table is None:
        rep.fail(skill, "no lesson-states table (header row starting '| State |')")
        return
    status = s_map.get("Status")
    if status is None:
        rep.fail(skill, "lesson format has no '- **Status:**' field to check the states table against")
        return
    enum = [state_name(e) for e in status.split(":**", 1)[1].split("|")]
    for n in table:
        if n not in enum:
            rep.fail(skill, f"lesson-states table names '{n}', which is not in the '- **Status:**' list")
    for n in enum:
        if n not in table:
            rep.fail(skill, f"'- **Status:**' list names '{n}', which is missing from the lesson-states table")


def check_hooks(rep, root):
    """hooks/hooks.json: {"hooks": {Event: [{matcher?, hooks: [{type: command, command, args?, timeout<=5}]}]}},
    every command is `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<x>.py"` and the file exists, and no
    hooks/*.py imports socket/urllib/http/subprocess (WARN) (ADR 0010)."""
    for py in sorted((root / "hooks").glob("*.py")):
        for m in HOOK_BANNED_IMPORT.finditer(py.read_text(encoding="utf-8", errors="replace")):
            rep.warn(py, f"imports '{m.group(1)}' (hooks make no network calls and spawn no processes)")
    path = root / HOOKS_JSON
    data = load_json(rep, path, ["hooks"])
    if data is None:
        return
    events = data.get("hooks")
    if not isinstance(events, dict) or not events:
        rep.fail(path, "'hooks' must be a non-empty object of event name -> list of matcher groups")
        return
    for event, groups in events.items():
        where = f"hooks.{event}"
        if event not in KNOWN_HOOK_EVENTS:
            rep.warn(path, f"{where}: unknown hook event '{event}'")
        if not isinstance(groups, list) or not groups:
            rep.fail(path, f"{where} must be a non-empty list of matcher groups")
            continue
        for i, group in enumerate(groups):
            gw = f"{where}[{i}]"
            if not isinstance(group, dict):
                rep.fail(path, f"{gw} must be an object")
                continue
            if "matcher" in group and not isinstance(group["matcher"], str):
                rep.fail(path, f"{gw}.matcher must be a string")
            hooks = group.get("hooks")
            if not isinstance(hooks, list) or not hooks:
                rep.fail(path, f"{gw}.hooks must be a non-empty list")
                continue
            for j, hook in enumerate(hooks):
                check_hook_entry(rep, root, path, f"{gw}.hooks[{j}]", hook)


def check_hook_entry(rep, root, path, where, hook):
    if not isinstance(hook, dict):
        rep.fail(path, f"{where} must be an object")
        return
    if hook.get("type") != "command":
        rep.fail(path, f"{where}.type must be 'command' (bq ships no prompt/agent hooks)")
    command, args = hook.get("command"), hook.get("args", [])
    if not isinstance(command, str) or not command.strip():
        rep.fail(path, f"{where}.command must be a non-empty string")
        command = ""
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        rep.fail(path, f"{where}.args must be a list of strings")
        args = []
    if command and not HOOK_COMMAND.fullmatch(command):
        rep.fail(path, f'{where}.command must be exactly python3 "${{CLAUDE_PLUGIN_ROOT}}/hooks/<name>.py", '
                       f"got {command!r}")
    timeout = hook.get("timeout")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= HOOK_TIMEOUT_MAX:
        rep.fail(path, f"{where}.timeout must be a number in (0, {HOOK_TIMEOUT_MAX}] seconds, got {timeout!r}")
    for text in [command, *args]:
        for rel in PLUGIN_ROOT_PATH.findall(text):
            if not (root / rel).is_file():
                rep.fail(path, f"{where} references missing file '{rel}'")


CHECKS = [
    check_manifests,
    check_agents,
    check_commands,
    check_skills,
    check_markers,
    check_readme_and_templates,
    check_cross_refs,
    check_lesson_format,
    check_hooks,
]


def run(root):
    root = Path(root).resolve()
    rep = Report(root)
    for check in CHECKS:
        check(rep, root)
    return rep


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    rep = run(root)
    for line in rep.warns + rep.fails:
        print(line)
    if rep.fails:
        print(f"validate: {len(rep.fails)} failure(s), {len(rep.warns)} warning(s)")
        return 1
    print(f"validate: OK ({len(rep.warns)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

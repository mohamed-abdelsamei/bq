"""Durable history for the ~/.ai memory store (ADR 0011). Stdlib only.

The one bq module allowed to spawn processes, and only `git` (plus `xcode-select -p` on macOS).

Layout: a bare repo H (history_dir()) outside the store, with $AI_HOME (default ~/.ai) as the
work tree, passed as --git-dir/--work-tree on every call. Nothing is written into the store
itself: ignore patterns live in H/info/exclude, attribute overrides in H/info/attributes, and
no path is baked into H's config. H is mode 0700 and never gets a remote.

Every git call:
- runs with a fixed identity, no signing, no hooks, and the user's global/system git config
  ignored (GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM=1), inherited GIT_* vars scrubbed;
- has a timeout: READ_TIMEOUT for reads, WRITE_TIMEOUT for add/commit. Writes get a generous
  budget on purpose: killing git mid-write strands index.lock, and a lock is never auto-deleted.
  On timeout git gets SIGTERM first (so it removes its own lock files), then SIGKILL.

Restore never destroys newer work: in place only when the folder is missing, otherwise to
<dir>.restored-<rev>/, and --force first checkpoints the current state so overwritten bytes
stay in history.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bqhook as h  # noqa: E402

READ_TIMEOUT = 5
WRITE_TIMEOUT = 60
LOCK_STALE = 600  # seconds: an index.lock older than this is reported, never removed
EXCLUDES = ["*.env", ".env", "*.pem", "*.key", "id_rsa*", "id_ed25519*", "id_ecdsa*", "id_dsa*", ".DS_Store", "*.restored-*/"]
# Store bytes exactly as on disk: no eol conversion, filters or export tweaks from any .gitattributes.
ATTRIBUTES = "* -text -filter -ident -working-tree-encoding -export-ignore -export-subst\n"
EXCLUDE_HEADER = "# bq memory (ADR 0011): secrets, OS junk, restore extracts, symlinked entries\n"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "bq_memory.py"
GIT_CONFIG = ["-c", "user.name=bq", "-c", "user.email=bq@localhost", "-c", "commit.gpgsign=false",
              "-c", "core.hooksPath=/dev/null", "-c", "core.quotepath=false"]


class MemError(Exception):
    """An expected refusal or failure, reported as one line."""


# ---------------------------------------------------------------- locations


def ai_home():
    return h.ai_home()


def default_history_dir():
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "bq" / "ai-history.git"
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base).expanduser() / "bq" / "ai-history.git"


def history_dir():
    env = os.environ.get("BQ_MEMORY_GIT_DIR")
    return Path(env).expanduser() if env else default_history_dir()


def has_history(hist=None):
    hist = hist or history_dir()
    return (hist / "HEAD").is_file() and (hist / "objects").is_dir()


# ---------------------------------------------------------------- process plumbing


def _env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", LC_ALL="C", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM="1", GIT_OPTIONAL_LOCKS="0")
    return env


def _spawn(cmd, timeout, cwd=None, stdin=None):
    """Run cmd; return (returncode, stdout bytes, stderr bytes). Timeout -> SIGTERM, then SIGKILL."""
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL)
    except OSError as e:
        raise MemError(f"cannot run {cmd[0]}: {e}")
    try:
        out, err = p.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        p.terminate()
        try:
            p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
        raise MemError(f"{cmd[0]} timed out after {timeout}s")
    return p.returncode, out, err


class GitError(MemError):
    def __init__(self, args, rc, err):
        self.stderr = err.decode("utf-8", "replace").strip()
        super().__init__(f"git {args[0]} failed ({rc}): {self.stderr.splitlines()[-1] if self.stderr else ''}")


class Repo:
    def __init__(self, hist=None, home=None):
        self.hist = Path(hist or history_dir())
        self.home = Path(home or ai_home())

    def run(self, *args, timeout=READ_TIMEOUT, stdin=None, check=True):
        cmd = ["git", f"--git-dir={self.hist}", f"--work-tree={self.home}", *GIT_CONFIG, *args]
        cwd = self.home if self.home.is_dir() else self.hist  # pathspecs are relative to the store root
        rc, out, err = _spawn(cmd, timeout, cwd=cwd, stdin=stdin)
        if check and rc != 0:
            raise GitError(args, rc, err)
        return out if check else (rc, out, err)

    def text(self, *args, **kw):
        return self.run(*args, **kw).decode("utf-8", "replace").strip()

    def head(self):
        rc, out, _ = self.run("rev-parse", "--verify", "-q", "HEAD^{commit}", check=False)
        return out.decode().strip() if rc == 0 else None

    def short(self, rev):
        return self.text("rev-parse", "--short", rev)

    def top_dirs(self, rev):
        out = self.run("ls-tree", "-d", "-z", "--name-only", rev)
        return {os.fsdecode(n) for n in out.split(b"\0") if n}

    def has_tree(self, rev, path):
        rc, out, _ = self.run("cat-file", "-t", f"{rev}:{path}", check=False)
        return rc == 0 and out.strip() == b"tree"


# ---------------------------------------------------------------- init


def _check_git():
    git = shutil.which("git")
    if not git:
        raise MemError("git not found on PATH")
    if sys.platform == "darwin" and os.path.realpath(git) == "/usr/bin/git":
        # The /usr/bin/git shim opens an installer dialog when the command line tools are missing.
        rc, _, _ = _spawn(["xcode-select", "-p"], READ_TIMEOUT)
        if rc != 0:
            raise MemError("git is the Xcode shim without command line tools (run: xcode-select --install)")
    rc, out, _ = _spawn(["git", "--version"], READ_TIMEOUT)
    if rc != 0 or not out.startswith(b"git version"):
        raise MemError("git is not usable (`git --version` failed)")


def _escape(name):
    """A top-level name as an anchored gitignore pattern."""
    esc = re.sub(r"([*?\[\\])", r"\\\1", name)
    return "/" + (esc[:-1] + "\\ " if esc.endswith(" ") else esc)


def _sync_info(repo, out):
    """Write H/info/exclude (fixed patterns + symlinked top-level entries) and H/info/attributes.
    Warns once per newly skipped symlink."""
    info = repo.hist / "info"
    info.mkdir(exist_ok=True)
    links = sorted(e.name for e in os.scandir(repo.home) if e.is_symlink()) if repo.home.is_dir() else []
    exclude = info / "exclude"
    old = exclude.read_text(encoding="utf-8").splitlines() if exclude.is_file() else []
    want = [*EXCLUDES, *(_escape(n) for n in links)]
    for n in links:
        if _escape(n) not in old:
            out(f"bq memory: skipping symlinked entry {n} (not tracked; history covers real folders only)")
    for path, text in ((exclude, EXCLUDE_HEADER + "\n".join(want) + "\n"), (info / "attributes", ATTRIBUTES)):
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")


def init(out=print):
    repo = Repo()
    _check_git()
    home, hist = repo.home, repo.hist
    if not home.is_dir():
        raise MemError(f"{home} does not exist; nothing to protect yet")
    rh, rhist = home.resolve(), hist.resolve()
    if rhist == rh or rh in rhist.parents:
        raise MemError(f"history dir {hist} must be outside {home}")
    rc, _, _ = _spawn(["git", "-C", str(home), "rev-parse", "--git-dir"], READ_TIMEOUT)
    if rc == 0:
        raise MemError(f"{home} is inside another git repository; refusing to add a second history")
    if has_history(hist):
        created = False
    else:
        if hist.exists() and (not hist.is_dir() or any(hist.iterdir())):
            raise MemError(f"{hist} exists and is not a bq history repo")
        hist.parent.mkdir(parents=True, exist_ok=True)
        rc, _, err = _spawn(["git", "init", "-q", "--bare", "--initial-branch=main", str(hist)], WRITE_TIMEOUT)
        if rc != 0:
            raise MemError(f"git init failed: {err.decode('utf-8', 'replace').strip()}")
        created = True
    os.chmod(hist, 0o700)
    _sync_info(repo, out)
    remotes = repo.text("remote")
    if remotes:
        out(f"bq memory: warning: history has remote(s) {remotes.split()} — bq never pushes; remove them")
    verb = "created" if created else "already initialized:"
    out(f"bq memory: {verb} history {hist} (work tree {home}); "
        f"first checkpoint: python3 {SCRIPT} checkpoint")
    return 0


# ---------------------------------------------------------------- checkpoint


def checkpoint(out=print, warn=None):
    """Commit every change in the store. Exit-0 no-ops: no history, fresh lock, nothing changed."""
    warn = warn or (lambda s: print(s, file=sys.stderr))
    repo = Repo()
    if not has_history(repo.hist):
        return 0
    if not repo.home.is_dir():
        warn(f"bq memory: {repo.home} is missing — nothing committed; restore folders with: "
             f"python3 {SCRIPT} restore <dir>")
        return 0
    lock = repo.hist / "index.lock"
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age >= LOCK_STALE:
            warn(f"bq memory: stale lock {lock} ({int(age // 60)} min old); checkpoint skipped — "
                 "remove it by hand once no git process is running")
        return 0
    _sync_info(repo, warn)
    before = repo.head()
    old_dirs = repo.top_dirs(before) if before else set()
    try:
        repo.run("add", "-A", timeout=WRITE_TIMEOUT)
        changed = [os.fsdecode(p) for p in
                   repo.run("diff", "--cached", "--name-only", "--no-renames", "-z").split(b"\0") if p]
        if not changed:
            return 0
        tops = sorted({p.split("/", 1)[0] for p in changed})
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        msg = f"bq checkpoint {stamp}\n\nChanged: {', '.join(tops)}\n"
        repo.run("commit", "-q", "--no-verify", "-F", "-", stdin=msg.encode(), timeout=WRITE_TIMEOUT)
    except GitError as e:
        if ".lock" in e.stderr:  # another checkpoint won the race: skip quietly
            return 0
        raise
    if before:
        short = repo.short(before)
        for d in sorted(old_dirs - repo.top_dirs("HEAD")):
            out(f"bq memory: {d} deleted — restore: python3 {SCRIPT} restore {d} (from {short})")
    return 0


# ---------------------------------------------------------------- status / log


def missing_dirs():
    """Top-level folders in HEAD that are missing on disk ([] without history or commits)."""
    repo = Repo()
    if not has_history(repo.hist) or not repo.head():
        return []
    return sorted(d for d in repo.top_dirs("HEAD") if not (repo.home / d).is_dir())


def status(out=print):
    repo = Repo()
    if not has_history(repo.hist):
        out(f"bq memory: no history at {repo.hist} (opt in with: python3 {SCRIPT} init)")
        return 0
    out(f"history: {repo.hist}\nwork tree: {repo.home}")
    if not repo.head():
        out("last checkpoint: none yet")
        return 0
    out("last checkpoint: " + repo.text("log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M"))
    if repo.home.is_dir():
        entries = repo.run("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all")
        count = len([e for e in entries.split(b"\0") if e])
        out(f"uncommitted changes: {count}")
    missing = missing_dirs()
    out("missing folders: " + (", ".join(missing) if missing else "none"))
    return 0


def log(path=None, limit=20, out=print):
    repo = Repo()
    if not has_history(repo.hist):
        out(f"bq memory: no history at {repo.hist}")
        return 0
    if not repo.head():
        out("bq memory: no checkpoints yet")
        return 0
    args = ["log", f"-n{int(limit)}", "--format=%h %ad  %b", "--date=format:%Y-%m-%d %H:%M"]
    lines = [ln for ln in repo.text(*args, *(["--", path] if path else [])).splitlines() if ln.strip()]
    out("\n".join(lines) or "bq memory: no matching checkpoints")
    return 0


# ---------------------------------------------------------------- restore


def _valid_name(name):
    if not name or name.startswith(".") or "/" in name or "\\" in name or "\0" in name:
        raise MemError(f"restore takes one top-level folder name, got {name!r}")


def _find_rev(repo, name, rev):
    if rev:
        rc, out, _ = repo.run("rev-parse", "--verify", "-q", f"{rev}^{{commit}}", check=False)
        if rc != 0:
            raise MemError(f"unknown revision {rev!r}")
        full = out.decode().strip()
        if not repo.has_tree(full, name):
            raise MemError(f"{name} does not exist in {rev}")
        return full
    if repo.has_tree("HEAD", name):
        return repo.head()
    for c in repo.text("rev-list", "HEAD", "--", name).split():
        if repo.has_tree(c, name):
            return c
        if repo.has_tree(c + "^", name):  # c is the commit that deleted it
            return repo.text("rev-parse", c + "^")
    raise MemError(f"{name} was never recorded in history")


def _blobs(repo, rev, name):
    """[(mode, relpath, bytes)] for every entry under rev:name, exact bytes from the object store."""
    listing = repo.run("ls-tree", "-r", "-z", "--full-tree", rev, "--", name)
    entries = []
    for rec in (r for r in listing.split(b"\0") if r):
        meta, path = rec.split(b"\t", 1)
        mode, kind, sha = meta.split()
        rel = os.fsdecode(path)[len(name) + 1:]
        if kind != b"blob" or not rel or ".." in rel.split("/") or rel.startswith("/"):
            continue  # gitlinks and anything odd are skipped
        entries.append((mode.decode(), rel, sha.decode()))
    data = repo.run("cat-file", "--batch", stdin="".join(s + "\n" for _, _, s in entries).encode(),
                    timeout=WRITE_TIMEOUT)
    out, pos = [], 0
    for mode, rel, sha in entries:
        nl = data.index(b"\n", pos)
        size = int(data[pos:nl].split()[2])
        out.append((mode, rel, data[nl + 1:nl + 1 + size]))
        pos = nl + 1 + size + 1
    return out


def _write_tree(blobs, dest, overwrite=False):
    """Write blobs under dest; return the list of skipped relpaths. Verifies bytes after writing."""
    skipped = []
    for mode, rel, content in blobs:
        p = dest / rel
        if any((dest / q).is_symlink() for q in Path(rel).parents if str(q) != "."):
            skipped.append(rel)  # never write through a symlinked folder
            continue
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if mode == "120000":
                if os.path.lexists(p):
                    if not overwrite or p.is_dir() and not p.is_symlink():
                        skipped.append(rel)
                        continue
                    p.unlink()
                os.symlink(os.fsdecode(content), p)
                continue
            if p.is_dir() and not p.is_symlink():
                skipped.append(rel)
                continue
            if p.is_symlink():
                p.unlink()
            p.write_bytes(content)
            if mode == "100755":
                p.chmod(p.stat().st_mode | 0o111)
            if p.read_bytes() != content:
                raise MemError(f"verification failed for {p}")
        except OSError:
            skipped.append(rel)
    return skipped


def restore(name, rev=None, force=False, out=print):
    _valid_name(name)
    repo = Repo()
    if not has_history(repo.hist) or not repo.head():
        raise MemError(f"no checkpoints in {repo.hist}")
    rev = _find_rev(repo, name, rev)
    short = repo.short(rev)
    target = repo.home / name
    if not os.path.lexists(target):
        repo.home.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix=f"{name}.restored-tmp-", dir=repo.home))  # excluded by pattern
        try:
            skipped = _write_tree(_blobs(repo, rev, name), tmp)
            os.rename(tmp, target)
            os.chmod(target, repo.home.stat().st_mode & 0o777)  # mkdtemp made it 0700
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        out(f"bq memory: restored {name} from {short} into {target}")
    elif force:
        checkpoint(out=out, warn=out)  # save the current state first so overwritten bytes stay in history
        if repo.run("status", "--porcelain", "-z", "--", name).strip(b"\0"):
            raise MemError(f"could not checkpoint the current {name} first (lock held?); not overwriting")
        saved = repo.short("HEAD")
        diff = repo.text("diff", "--stat", rev, "HEAD", "--", name)
        out(f"bq memory: overwriting {name} with {short}; current state saved as {saved} "
            f"(undo: restore {name} --rev {saved} --force)\n{diff or '(no differences)'}")
        skipped = _write_tree(_blobs(repo, rev, name), target, overwrite=True)
        out(f"bq memory: files present now but absent in {short} were kept")
    else:
        dest = repo.home / f"{name}.restored-{short}"
        if os.path.lexists(dest):
            raise MemError(f"{dest} already exists; compare or remove it first")
        skipped = _write_tree(_blobs(repo, rev, name), dest)
        out(f"bq memory: {name} exists, so {short} was extracted to {dest} (nothing overwritten)\n"
            f"compare: diff -ru {target} {dest}\n"
            f"overwrite instead: python3 {SCRIPT} restore {name} --rev {short} --force")
    for rel in skipped:
        out(f"bq memory: skipped {name}/{rel} (path conflict)")
    return 0


# ---------------------------------------------------------------- stamp

USERINFO = re.compile(r"^([A-Za-z][\w+.-]*://)[^/@]*@")


def stamp(cwd=None, out=print):
    """Write <AI_HOME>/<project>/.identity: the main checkout root and its remotes (no credentials)."""
    cwd = Path(cwd or os.getcwd()).resolve()
    found = next((p for p in (cwd, *cwd.parents) if (p / ".git").exists()), None)
    if found is None:
        raise MemError(f"{cwd} is not inside a git repository")
    root = h.main_root(found)
    name = root.name
    if not name or name.casefold() == "shared":
        raise MemError(f"{name!r} cannot have project memory")
    mem = ai_home() / name
    if not mem.is_dir():
        raise MemError(f"no memory folder {mem}; create it with /bq:init or /bq:onboard first")
    remotes = []
    common = h.git_common_dir(found)
    if common is not None and (common / "config").is_file():
        rc, text, _ = _spawn(["git", "config", "--file", str(common / "config"), "--get-regexp",
                              r"^remote\..*\.url$"], READ_TIMEOUT)
        if rc == 0:
            remotes = sorted({USERINFO.sub(r"\1", ln.split(None, 1)[1])
                              for ln in text.decode("utf-8", "replace").splitlines() if " " in ln})
    data = {"project": name, "roots": [str(root.resolve())], "remotes": remotes,
            "stamped": datetime.date.today().isoformat()}
    tmp = mem / ".identity.tmp"
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, mem / ".identity")
    out(f"bq memory: stamped {mem / '.identity'} (root {data['roots'][0]}, {len(remotes)} remote(s))")
    return 0

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

Checkpoints are serialized by a non-blocking flock on H/bq-checkpoint.lock (held -> quiet skip).
Any git *.lock in H (top level and refs/) older than LOCK_STALE is reported as stuck, never removed.
A failed checkpoint leaves one line in H/bq-last-error (time + reason, no file contents), cleared
by the next successful one; a checkpoint that stages a nested git repo leaves H/bq-notice, shown
for RECENT_DAYS. Both are plain files so the SessionStart hook reads them without git.

Restore never destroys newer work: in place only when the folder is missing, otherwise to
<dir>.restored-<rev>/, and --force first checkpoints the current state so overwritten bytes
stay in history. It refuses a target that is a symlink or not a real folder (history can't have
saved what lies behind it).
"""
import datetime
import json
import os
import re
import shlex
import shutil
import stat as st
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # not POSIX: checkpoints are not serialized
    fcntl = None

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bqhook as h  # noqa: E402

READ_TIMEOUT = 5
WRITE_TIMEOUT = 60
LOCK_STALE = 120  # seconds: a checkpoint takes ~0.2 s, so an older index.lock is stuck (reported, never removed)
RECENT_DAYS = 7  # deletions recorded within this many days keep their restore notice
EXCLUDES = ["*.env", ".env", "*.pem", "*.key", "id_rsa*", "id_ed25519*", "id_ecdsa*", "id_dsa*", ".DS_Store", "*.restored-*/"]
# Store bytes exactly as on disk: no eol conversion, filters or export tweaks from any .gitattributes.
ATTRIBUTES = "* -text -filter -ident -working-tree-encoding -export-ignore -export-subst\n"
EXCLUDE_HEADER = "# bq memory (ADR 0011): secrets, OS junk, restore extracts, symlinked entries\n"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "bq_memory.py"
CHECKPOINT_LOCK = "bq-checkpoint.lock"  # bq's own flock file: persistent, never a stuck git lock
LAST_ERROR = "bq-last-error"
NOTICE = "bq-notice"
RECOVERY = "see the memory skill's Durability and recovery section"
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def command(*args):
    """A copy-pasteable `python3 "<SCRIPT>" <args>` line (the plugin root may contain spaces)."""
    script = str(SCRIPT)
    script = shlex.quote(script) if re.search(r'["$`\\]', script) else f'"{script}"'
    return f"python3 {script}" + "".join(" " + shlex.quote(str(a)) for a in args)


def restore_command(name, rev=None, force=False):
    """The restore command for a top-level folder; a name starting with `-` goes after `--`."""
    opts = [*(["--rev", rev] if rev else []), *(["--force"] if force else [])]
    return command("restore", *opts, "--", name) if name.startswith("-") else command("restore", name, *opts)

GIT_CONFIG = ["-c", "user.name=bq", "-c", "user.email=bq@localhost", "-c", "commit.gpgsign=false",
              "-c", "core.hooksPath=/dev/null", "-c", "core.quotepath=false",
              # git reads ~/.config/git/{ignore,attributes} even with GIT_CONFIG_GLOBAL=/dev/null
              "-c", f"core.excludesFile={os.devnull}", "-c", f"core.attributesFile={os.devnull}",
              "-c", "advice.addEmbeddedRepo=false"]


class MemError(Exception):
    """An expected refusal or failure, reported as one line."""


# ---------------------------------------------------------------- locations


def ai_home():
    return h.ai_home()


default_history_dir = h.default_history_dir
history_dir = h.history_dir
has_history = h.has_history
has_commits = h.has_commits


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
        f"first checkpoint: {command('checkpoint')}")
    return 0


# ---------------------------------------------------------------- checkpoint


def git_locks(hist=None):
    """[(path, mtime)] of git *.lock files in H (top level and refs/, never objects/), bq's own
    flock file excluded. Stats only; a file vanishing mid-scan is skipped."""
    hist = Path(hist or history_dir())
    found = []

    def scan(d, recurse):
        try:
            entries = os.scandir(d)
        except OSError:
            return
        with entries:
            for e in entries:
                try:
                    if e.name.endswith(".lock") and e.name != CHECKPOINT_LOCK and e.is_file(follow_symlinks=False):
                        found.append((Path(e.path), e.stat(follow_symlinks=False).st_mtime))
                    elif recurse and e.is_dir(follow_symlinks=False):
                        scan(e.path, True)
                except OSError:
                    pass

    scan(hist, False)
    scan(hist / "refs", True)
    return found


def stale_locks(hist=None):
    """git_locks() older than LOCK_STALE, oldest first."""
    now = time.time()
    return sorted((lk for lk in git_locks(hist) if now - lk[1] >= LOCK_STALE), key=lambda lk: lk[1])


def _fresh_lock(hist):
    now = time.time()
    return any(now - mtime < LOCK_STALE for _, mtime in git_locks(hist))


@contextmanager
def checkpoint_lock(hist=None):
    """Yield True while holding the non-blocking flock on H/bq-checkpoint.lock, False when another
    checkpoint holds it. Exiting only closes the fd: a forked child that inherited it keeps the lock."""
    if fcntl is None:
        yield True
        return
    fd = os.open(Path(hist or history_dir()) / CHECKPOINT_LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        yield True
    finally:
        os.close(fd)


def _write_record(hist, name, reason):
    """One line `<YYYY-MM-DD HH:MM>\t<reason>` in H/<name>, atomically; never raises."""
    try:
        tmp = Path(hist) / f"{name}.tmp"
        tmp.write_text(f"{when(time.time())}\t{CONTROL.sub(' ', reason)[:300]}\n", encoding="utf-8")
        os.replace(tmp, Path(hist) / name)
    except OSError:
        pass


def _clear_record(hist, name):
    try:
        (Path(hist) / name).unlink()
    except OSError:
        pass


def read_record(hist=None, name=LAST_ERROR, max_age=None):
    """(when, reason) from H/<name>, or None (absent, unreadable, older than max_age seconds).
    A plain file read, no git."""
    path = Path(hist or history_dir()) / name
    try:
        if max_age is not None and time.time() - path.stat().st_mtime > max_age:
            return None
        with open(path, "rb") as f:
            line = f.read(1024).decode("utf-8", "replace").split("\n", 1)[0]
    except OSError:
        return None
    stamp, sep, reason = line.partition("\t")
    return (CONTROL.sub("", stamp), CONTROL.sub(" ", reason).strip()) if sep and reason.strip() else None


def record_error(reason, hist=None):
    _write_record(hist or history_dir(), LAST_ERROR, reason)


def last_error_line(hist=None):
    rec = read_record(hist, LAST_ERROR)
    return f"bq memory: last checkpoint failed {rec[0]}: {rec[1]} — {RECOVERY}" if rec else None


def notice_line(hist=None):
    rec = read_record(hist, NOTICE, max_age=RECENT_DAYS * 86400)
    return f"bq memory: {rec[1]} (checkpoint {rec[0]}) — {RECOVERY}" if rec else None


_UNREADABLE = re.compile(r"""^(?:error: open\("(.+)"\):|error: unable to index file '(.+)'|"""
                         r"""warning: could not open directory '(.+?)/?':)""", re.M)


def _unreadable(err):
    """Paths `git add --ignore-errors` could not read, from its stderr, sorted and deduped."""
    text = err.decode("utf-8", "replace")
    return sorted({next(g for g in m.groups() if g) for m in _UNREADABLE.finditer(text)})


def _staged(repo):
    """(changed paths, newly staged gitlinks) from one `diff --cached --raw -z`."""
    toks = repo.run("diff", "--cached", "--raw", "-z", "--no-renames").split(b"\0")
    changed, links = [], []
    for meta, path in zip(toks[0::2], toks[1::2]):
        if not meta.startswith(b":"):
            break
        old_mode, new_mode = meta[1:].split()[:2]
        changed.append(os.fsdecode(path))
        if new_mode == b"160000" and old_mode != b"160000":
            links.append(os.fsdecode(path))
    return changed, links


def checkpoint(out=print, warn=None, locked=False):
    """Commit every change in the store. Exit-0 no-ops: no history, another checkpoint running
    (flock held; `locked` means the caller already holds it), a fresh git lock, nothing changed.
    A failure raises MemError and is recorded in H/bq-last-error; success clears that record."""
    warn = warn or (lambda s: print(s, file=sys.stderr))
    repo = Repo()
    if not has_history(repo.hist):
        return 0
    if not repo.home.is_dir():
        warn(f"bq memory: {repo.home} is missing — nothing committed; restore folders with: "
             f"{command('restore')} <dir>")
        return 0
    if locked:
        return _checkpoint(repo, out, warn)
    try:
        with checkpoint_lock(repo.hist) as held:
            return _checkpoint(repo, out, warn) if held else 0
    except OSError as e:  # the flock file itself could not be opened
        record_error(f"cannot open {CHECKPOINT_LOCK}: {e.strerror or e}", repo.hist)
        raise MemError(f"cannot open {repo.hist / CHECKPOINT_LOCK}: {e.strerror or e}")


def _checkpoint(repo, out, warn):
    stale = stale_locks(repo.hist)
    if stale:
        path, mtime = stale[0]
        warn(f"bq memory: stale lock {path} ({int((time.time() - mtime) // 60)} min old); checkpoint "
             f"skipped — {RECOVERY} (never remove it while git runs)")
        record_error(f"history lock {path.name} stuck since {when(mtime)}", repo.hist)
        return 0
    if git_locks(repo.hist):
        return 0  # a fresh git lock: some git is running in H; skip quietly
    try:
        return _commit(repo, out, warn)
    except (MemError, OSError) as e:
        reason = str(e) if isinstance(e, MemError) else f"{type(e).__name__}: {e.strerror or e}"
        if isinstance(e, GitError) and ".lock" in e.stderr and _fresh_lock(repo.hist):
            return 0  # lost a race with a git that is still running
        record_error(reason, repo.hist)
        if isinstance(e, MemError):
            raise
        raise MemError(reason) from e
    except Exception as e:  # any other crash must still leave a trace, never a silent wedge
        reason = f"{type(e).__name__}: {e}"
        record_error(reason, repo.hist)
        raise MemError(reason) from e


def _commit(repo, out, warn):
    _sync_info(repo, warn)
    before = repo.head()
    old_dirs = repo.top_dirs(before) if before else set()
    rc, _, err = repo.run("add", "-A", "--ignore-errors", timeout=WRITE_TIMEOUT, check=False)
    failed = _unreadable(err) if rc in (0, 1) else []  # 1: --ignore-errors skipped some paths
    if rc != 0 and not failed:
        raise GitError(("add",), rc, err)
    changed, links = _staged(repo)
    if changed:
        tops = sorted({p.split("/", 1)[0] for p in changed})
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        msg = f"bq checkpoint {stamp}\n\nChanged: {', '.join(tops)}\n"
        rc, cout, err = repo.run("commit", "-q", "--no-verify", "-F", "-", stdin=msg.encode(),
                                 timeout=WRITE_TIMEOUT, check=False)
        if rc != 0 and b"nothing to commit" not in cout + err:
            raise GitError(("commit",), rc, err or cout)
    if links:
        note = (f"nested git repo(s) {', '.join(links[:3])}{' …' if len(links) > 3 else ''} in the store: "
                "only their commit pointer is kept, not their files")
        _write_record(repo.hist, NOTICE, note)
        warn(f"bq memory: {note} — {RECOVERY}")
    if failed:
        reason = (f"could not read {len(failed)} path(s): {', '.join(failed[:3])}"
                  f"{' …' if len(failed) > 3 else ''} (the rest was committed)")
        record_error(reason, repo.hist)
        warn(f"bq memory: {reason} — {RECOVERY}")
    else:
        _clear_record(repo.hist, LAST_ERROR)
    if before and changed:
        short = repo.short(before)
        for d in sorted(old_dirs - repo.top_dirs("HEAD")):
            out(f"bq memory: {d} deleted — restore: {restore_command(d)} (from {short})")
    return 0


# ---------------------------------------------------------------- status / log


def _head_dirs(repo):
    """Top-level folders in HEAD, or None without history or commits. One git call."""
    if not has_history(repo.hist):
        return None
    rc, out, _ = repo.run("ls-tree", "-d", "-z", "--name-only", "HEAD", check=False)
    return {os.fsdecode(n) for n in out.split(b"\0") if n} if rc == 0 else None


def _missing(repo, head_dirs):
    return sorted(d for d in head_dirs if not (repo.home / d).is_dir())


def _recent(repo, head_dirs, days):
    """restore_notices()' `recent`. One git call.

    The log lists deleted files, not folders; a folder d not in HEAD was deleted by the newest
    commit C that deleted a file under it (a later re-add + delete would be a newer C), so C^ still
    has d. Names without a slash are top-level files and are skipped."""
    cutoff = int(time.time()) - days * 86400
    raw = repo.run("log", f"--since={days}.days.ago", "--no-renames", "--diff-filter=D", "--name-only",
                   "-z", "--format=%x01%p %ct", "HEAD")
    found, commit = {}, None
    for tok in raw.split(b"\0"):
        tok = tok.lstrip(b"\n")
        if tok.startswith(b"\x01"):  # a commit header: "<parent> <committer time>" (none on the root)
            parent, _, ct = tok[1:].decode().partition(" ")
            commit = (parent.split()[0], int(ct)) if parent and ct.isdigit() else None
        elif b"/" in tok and commit:
            found.setdefault(os.fsdecode(tok.split(b"/", 1)[0]), commit)  # newest first: keep the latest
    return sorted((d, rev, ct) for d, (rev, ct) in found.items()
                  if ct >= cutoff and d not in head_dirs and not (repo.home / d).is_dir())


def restore_notices(days=RECENT_DAYS):
    """(missing, recent) sharing one HEAD listing, both ([], []) without history or commits: two
    git calls. missing: top-level folders in HEAD that are missing on disk. recent: [(dir,
    rev_before, deleted_at)] for top-level folders whose deletion a checkpoint committed in the last
    `days` days and that are still missing on disk: newest deletion per folder, sorted by name.
    rev_before is the short parent of the deleting commit, deleted_at its committer time (epoch
    seconds). Folders still in HEAD are `missing`'s business, not listed in `recent`."""
    repo = Repo()
    head_dirs = _head_dirs(repo)
    if head_dirs is None:
        return [], []
    return _missing(repo, head_dirs), _recent(repo, head_dirs, days)


def when(epoch, fmt="%Y-%m-%d %H:%M"):
    return datetime.datetime.fromtimestamp(epoch).strftime(fmt)


def lock_line(mtime, prefix="bq memory: history lock"):
    return f"{prefix} stuck since {when(mtime)} — checkpoints are paused; {RECOVERY}"


def status(out=print):
    repo = Repo()
    if not has_history(repo.hist):
        out(f"bq memory: no history at {repo.hist} (opt in with: {command('init')})")
        return 0
    out(f"history: {repo.hist}\nwork tree: {repo.home}")
    stale = stale_locks(repo.hist)
    if stale:
        out(lock_line(stale[0][1], prefix="history lock:"))
        for path, mtime in stale:
            out(f"  {path} (since {when(mtime)})")
    else:
        out("history lock: " + ("held (a checkpoint is running)" if git_locks(repo.hist) else "none"))
    err = last_error_line(repo.hist)
    if err and not stale:
        out(err)
    notice = notice_line(repo.hist)
    if notice:
        out(notice)
    if not repo.head():
        out("last checkpoint: none yet")
        return 0
    out("last checkpoint: " + repo.text("log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M"))
    if repo.home.is_dir():
        entries = repo.run("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all")
        count = len([e for e in entries.split(b"\0") if e])
        out(f"uncommitted changes: {count}")
    missing, recent = restore_notices()
    out("missing folders: " + (", ".join(missing) if missing else "none"))
    out(f"deleted in the last {RECENT_DAYS} days: " + ("" if recent else "none"))
    for d, rev, ct in recent:
        out(f"  {d} — deleted {when(ct, '%Y-%m-%d')}, last in {rev} — restore: {restore_command(d)}")
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
    if os.path.islink(dest):
        raise MemError(f"{dest} is a symlink; refusing to write through it")
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
    if os.path.lexists(target) and (os.path.islink(target) or not st.S_ISDIR(os.lstat(target).st_mode)):
        # symlinked entries are excluded from history: whatever is behind this was never saved
        raise MemError(f"{target} is a symlink or not a folder; refusing to restore onto it "
                       "(move it aside, then run restore again)")
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
            f"(undo: {restore_command(name, saved, force=True)})\n{diff or '(no differences)'}")
        skipped = _write_tree(_blobs(repo, rev, name), target, overwrite=True)
        out(f"bq memory: files present now but absent in {short} were kept")
    else:
        dest = repo.home / f"{name}.restored-{short}"
        if os.path.lexists(dest):
            raise MemError(f"{dest} already exists; compare or remove it first")
        skipped = _write_tree(_blobs(repo, rev, name), dest)
        out(f"bq memory: {name} exists, so {short} was extracted to {dest} (nothing overwritten)\n"
            f"compare: diff -ru {shlex.quote(str(target))} {shlex.quote(str(dest))}\n"
            f"overwrite instead: {restore_command(name, short, force=True)}")
    for rel in skipped:
        out(f"bq memory: skipped {name}/{rel} (path conflict)")
    return 0


# ---------------------------------------------------------------- stamp

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
    remotes = sorted(h.clean_remote_urls(root))  # the hook's own parser: one reading of the config
    data = {"project": name, "roots": [str(root.resolve())], "remotes": remotes,
            "stamped": datetime.date.today().isoformat()}
    tmp = mem / ".identity.tmp"
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, mem / ".identity")
    out(f"bq memory: stamped {mem / '.identity'} (root {data['roots'][0]}, {len(remotes)} remote(s))")
    return 0


# ---------------------------------------------------------------- index (X1)

INDEX_MAX_BYTES = 64 * 1024
CLOSED_REQUIREMENT = {"Delivered", "Dropped", "Rejected", "Withdrawn", "Superseded"}
OPEN_DECISION = {"Proposed", "Accepted"}
_FIELD = r"^[ \t]*(?:[-*][ \t]+)?\*\*{}:\*\*[ \t]*(.*)$"
_STATUS = re.compile(_FIELD.format("Status"), re.M)
_DATE = re.compile(_FIELD.format("Date"), re.M)
_OPEN_TASK = re.compile(r"^[ \t]*(?:[-*]|\d+[.)])[ \t]+\[([ ~!])\]", re.M)
_CUT = re.compile(r" · | — | \(|\*\*|[\x00-\x1f\x7f]")
_NOISE = re.compile(r"\*\*|[\x00-\x1f\x7f]")


def _is_artifact(p):
    """A regular file bq wrote as a record: not a symlink, dotfile, README.md or *-template.md."""
    return (p.is_file() and not p.is_symlink() and not p.name.startswith(".")
            and p.name != "README.md" and not p.stem.endswith("-template"))


def _read(p):
    try:
        with open(p, "rb") as f:
            return f.read(INDEX_MAX_BYTES).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _field(rx, text):
    m = rx.search(text)
    return _CUT.split(m.group(1), 1)[0].strip() if m else ""


def _lesson_rules():
    """(status_of, flagged_since, in_force) from the SessionStart hook, so the index and the hook
    agree; a simple fallback when the hook can't be imported (imported lazily: no cycle)."""
    try:
        import session_start as s
        return s.status_of, s.flagged_since, s.IN_FORCE
    except Exception:
        flag = re.compile(r"·\s*(?:Missed|Contradicted)\b")
        return ((lambda t: _field(_STATUS, t).split(" ")[0] or "Active"),
                (lambda t, lines: sum(bool(flag.search(ln)) for ln in lines)), {"Active", "Shared"})


def _project_mem(project, cwd):
    if project is None:
        project = h.project_dir({"cwd": str(cwd)} if cwd else {}).name
    if (not project or project.startswith(".") or "/" in project or "\\" in project
            or project.casefold() == "shared"):
        raise MemError(f"{project!r} is not a project memory name")
    mem = ai_home() / project
    if not mem.is_dir():
        raise MemError(f"no memory folder {mem}")
    return project, mem


def index(project=None, cwd=None, out=print):
    """Print a deterministic memory index: open loops first (requirements not Delivered/Dropped,
    open task items, Proposed/Accepted decisions, Proposed lessons, in-force lessons flagged since
    their last review), then one `path — title — status — date` line per artifact.

    Pure file reads (no git, no timestamps). Skips dotfiles, symlinks, README.md and *-template.md;
    archive/ is a file count only. Missing title/status/date fields print blank.
    """
    project, mem = _project_mem(project, cwd)
    status_of, flagged_since, in_force = _lesson_rules()
    rows, loops = [], []
    folders = sorted(e for e in mem.iterdir() if e.is_dir() and not e.is_symlink()
                     and not e.name.startswith(".") and e.name != "archive")
    top = sorted(p for p in mem.iterdir() if _is_artifact(p))
    for p in top + [f for d in folders for f in sorted(d.rglob("*")) if _is_artifact(f)]:
        rel = p.relative_to(mem).as_posix()
        folder = rel.split("/", 1)[0] if "/" in rel else ""
        text = _read(p) if p.suffix == ".md" else ""
        lines = text.splitlines()
        title = next((_NOISE.sub("", ln[2:]).strip() for ln in lines if ln.startswith("# ")), "")
        status = _field(_STATUS, text)
        word = status.split(" ")[0]
        rows.append(f"{rel} — {title} — {status} — {_field(_DATE, text)}")
        if folder == "requirements" and word not in CLOSED_REQUIREMENT:
            loops.append((0, f"requirement not delivered: {rel} ({status or 'no status'})"))
        elif folder == "decisions" and word in OPEN_DECISION:
            loops.append((2, f"decision not implemented: {rel} ({word})"))
        elif folder == "tasks":
            marks = _OPEN_TASK.findall(text)
            if marks:
                counts = ", ".join(f"[{c}] {marks.count(c)}" for c in " ~!" if c in marks)
                loops.append((1, f"open tasks: {rel} — {len(marks)} ({counts})"))
        elif folder == "lessons" and "/" not in rel[len("lessons/"):]:
            lesson_status = status_of(text)
            if lesson_status == "Proposed":
                loops.append((3, f"lesson Proposed: {rel}"))
            elif lesson_status in in_force and flagged_since(text, lines):
                loops.append((4, f"lesson Missed/Contradicted since last review: {rel}"))
    out(f"# bq memory index: {project}\nmemory: {mem}\n")
    out("## Open loops")
    out("\n".join(f"- {ln}" for _, ln in sorted(loops, key=lambda x: x[0])) if loops else "- none")
    out("\n## Artifacts")
    out("\n".join(rows) if rows else "(none)")
    archive = mem / "archive"
    if archive.is_dir() and not archive.is_symlink():
        n = sum(1 for p in archive.rglob("*") if p.is_file() and not p.name.startswith("."))
        out(f"archive/ — {n} file(s)")
    return 0

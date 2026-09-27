"""bq memory history (ADR 0011): M1-M5, M7, I3 against scripts/bq_memory.py.

Run: python3 -m unittest discover -s scripts -p 'test_*.py'
Every run uses a temp AI_HOME, a temp BQ_MEMORY_GIT_DIR and a temp HOME. The module guard (M7)
fingerprints the real ~/.ai tree and the default history dir before and after, read-only.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True  # keep hooks/ free of __pycache__
REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "scripts" / "bq_memory.py"
sys.path.insert(0, str(REPO / "hooks"))
import _bqmem as m  # noqa: E402

GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}


# ---------------------------------------------------------------- M7 guard

def fingerprint(root):
    """sha256 over (relpath, size, mtime_ns) of every entry under root, read-only; None if absent."""
    root = Path(root)
    if not os.path.lexists(root):
        return None
    rows = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for n in sorted(dirnames + filenames):
            p = Path(dirpath) / n
            st = p.lstat()
            rows.append(f"{p.relative_to(root)}\0{st.st_size}\0{st.st_mtime_ns}")
    return hashlib.sha256("\n".join(sorted(rows)).encode("utf-8", "surrogateescape")).hexdigest()


def real_locations():
    with mock.patch.dict(os.environ, {"HOME": str(Path.home())}):
        os.environ.pop("BQ_MEMORY_GIT_DIR", None)
        os.environ.pop("XDG_DATA_HOME", None)
        hist = m.default_history_dir()
    return [Path.home() / ".ai", hist]


_BEFORE = {}


def setUpModule():
    for p in real_locations():
        _BEFORE[p] = fingerprint(p)


def tearDownModule():
    for p, before in _BEFORE.items():
        after = fingerprint(p)
        if after != before:
            raise AssertionError(f"M7: test suite changed real {p} (before {before}, after {after})")


# ---------------------------------------------------------------- helpers

def git(*args, cwd, check=True):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                        *args], cwd=cwd, capture_output=True, timeout=30, env={**os.environ, **GIT_ENV})
    if check and r.returncode:
        raise AssertionError(r.stderr.decode())
    return r.stdout.decode()


class MemBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(self._tmp.name).resolve()
        self.ai, self.hist, self.home = self.t / "ai", self.t / "state" / "ai-history.git", self.t / "home"
        self.ai.mkdir()
        self.home.mkdir()
        self.env = {**os.environ, "AI_HOME": str(self.ai), "BQ_MEMORY_GIT_DIR": str(self.hist),
                    "HOME": str(self.home), "XDG_DATA_HOME": str(self.home / "xdg")}

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args, cwd=None, env=None, ok=True):
        env = env or self.env
        for k in ("AI_HOME", "BQ_MEMORY_GIT_DIR", "HOME"):  # M7: never spawn against real paths
            self.assertTrue(env.get(k, "").startswith(str(self.t)), f"{k} not isolated")
        r = subprocess.run([sys.executable, str(CLI), *args], cwd=cwd or self.t, env=env,
                           capture_output=True, text=True, timeout=60)
        if ok is not None:
            self.assertEqual(r.returncode, 0 if ok else 1, r.stdout + r.stderr)
        return r

    def hgit(self, *args):
        return git(f"--git-dir={self.hist}", f"--work-tree={self.ai}", *args, cwd=self.ai)

    def commits(self):
        r = subprocess.run(["git", f"--git-dir={self.hist}", "rev-list", "--count", "HEAD"],
                           capture_output=True, text=True, env={**os.environ, **GIT_ENV})
        return int(r.stdout.strip()) if r.returncode == 0 else 0

    def files(self, root):
        root = Path(root)
        return {str(p.relative_to(root)): (os.readlink(p) if p.is_symlink() else p.read_bytes())
                for p in root.rglob("*") if p.is_file() or p.is_symlink()}

    def put(self, rel, data):
        p = self.ai / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode())

    def ready(self):
        self.cli("init")
        self.put("p1/charter.md", "# p1\n")
        self.put("p2/lessons/a.md", "lesson a\n")
        self.cli("checkpoint")


# ---------------------------------------------------------------- M1

class Init(MemBase):
    def test_creates_private_bare_history_outside_store(self):
        self.put("p1/charter.md", "x")
        before = self.files(self.ai)
        r = self.cli("init")
        self.assertIn("created history", r.stdout)
        self.assertEqual(self.hist.stat().st_mode & 0o777, 0o700)
        self.assertEqual(git("--git-dir", str(self.hist), "config", "core.bare", cwd=self.t).strip(), "true")
        self.assertEqual(git("--git-dir", str(self.hist), "remote", cwd=self.t).strip(), "")
        exclude = (self.hist / "info" / "exclude").read_text()
        for pat in m.EXCLUDES:
            self.assertIn(pat, exclude.splitlines())
        self.assertEqual(self.files(self.ai), before, "init wrote into the store")
        self.assertEqual(sorted(os.listdir(self.ai)), ["p1"])
        self.assertEqual(self.commits(), 0)

    def test_idempotent(self):
        self.cli("init")
        exclude = (self.hist / "info" / "exclude").read_text()
        r = self.cli("init")
        self.assertIn("already initialized", r.stdout)
        self.assertEqual((self.hist / "info" / "exclude").read_text(), exclude)

    def test_refuses_inside_another_git_work_tree(self):
        outer = self.t / "outer"
        (outer / "ai").mkdir(parents=True)
        git("init", "-q", cwd=outer)
        r = self.cli("init", env={**self.env, "AI_HOME": str(outer / "ai")}, ok=False)
        self.assertIn("inside another git repository", r.stderr)
        self.assertFalse(self.hist.exists())

    def test_refuses_unusable_git(self):
        fake = self.t / "fakebin"
        fake.mkdir()
        (fake / "git").write_text("#!/bin/sh\nexit 1\n")
        (fake / "git").chmod(0o755)
        r = self.cli("init", env={**self.env, "PATH": str(fake)}, ok=False)
        self.assertIn("git is not usable", r.stderr)
        self.assertFalse(self.hist.exists())

    def test_refuses_history_inside_store(self):
        r = self.cli("init", env={**self.env, "BQ_MEMORY_GIT_DIR": str(self.ai / "h.git")}, ok=False)
        self.assertIn("must be outside", r.stderr)
        self.assertFalse((self.ai / "h.git").exists())

    def test_refuses_missing_store(self):
        r = self.cli("init", env={**self.env, "AI_HOME": str(self.t / "nope")}, ok=False)
        self.assertIn("does not exist", r.stderr)

    def test_symlinked_entry_warned_and_skipped(self):
        (self.t / "elsewhere").mkdir()
        (self.t / "elsewhere" / "f.md").write_text("outside")
        os.symlink(self.t / "elsewhere", self.ai / "linked")
        self.put("real/a.md", "a")
        r = self.cli("init")
        self.assertIn("skipping symlinked entry linked", r.stdout)
        self.cli("checkpoint")
        self.assertEqual(self.hgit("ls-tree", "--name-only", "HEAD").split(), ["real"])
        self.assertNotIn("linked", self.cli("checkpoint").stderr)  # warned once, not every run

    def test_secrets_and_junk_excluded(self):
        self.cli("init")
        for rel in ("p/.env", "p/prod.env", "p/tls.pem", "p/k.key", "p/id_ed25519", ".DS_Store", "p/.DS_Store"):
            self.put(rel, "secret")
        self.put("p/notes.md", "keep")
        self.cli("checkpoint")
        self.assertEqual(self.hgit("ls-tree", "-r", "--name-only", "HEAD").split(), ["p/notes.md"])

    def test_no_history_means_no_op(self):
        self.put("p1/a.md", "a")
        for cmd in ("checkpoint",):
            r = self.cli(cmd)
            self.assertEqual((r.stdout, r.stderr), ("", ""))
        self.assertIn("no history", self.cli("status").stdout)
        self.assertFalse(self.hist.exists())
        with mock.patch.dict(os.environ, self.env):
            self.assertEqual(m.missing_dirs(), [])


# ---------------------------------------------------------------- M2

class Checkpoint(MemBase):
    def test_one_commit_then_none(self):
        self.cli("init")
        self.put("p1/a.md", "a")
        self.put("p2/b.md", "b")
        r = self.cli("checkpoint")
        self.assertEqual((r.stdout, r.stderr), ("", ""))
        self.assertEqual(self.commits(), 1)
        self.cli("checkpoint")
        self.assertEqual(self.commits(), 1)
        self.put("p2/b.md", "b2")
        self.cli("checkpoint")
        self.assertEqual(self.commits(), 2)
        msg = self.hgit("log", "-1", "--format=%s%n%b")
        self.assertTrue(msg.startswith("bq checkpoint 20"), msg)
        self.assertIn("Changed: p2", msg)
        ident = self.hgit("log", "-1", "--format=%an <%ae>|%cn <%ce>").strip()
        self.assertEqual(ident, "bq <bq@localhost>|bq <bq@localhost>")

    def test_bypasses_user_git_config_hooks_and_signing(self):
        hooks = self.home / "hooks"
        hooks.mkdir()
        for name in ("pre-commit", "commit-msg"):
            (hooks / name).write_text("#!/bin/sh\nexit 1\n")
            (hooks / name).chmod(0o755)
        (self.home / ".gitconfig").write_text(
            f"[user]\n\temail = me@example.com\n[commit]\n\tgpgsign = true\n[core]\n\thooksPath = {hooks}\n"
            "\texcludesFile = ~/.gitignore_global\n")
        (self.home / ".gitignore_global").write_text("*.md\n")
        env = {**self.env, "GIT_DIR": str(self.t / "bogus"), "GIT_INDEX_FILE": str(self.t / "bogus-index")}
        self.cli("init", env=env)
        self.put("p1/a.md", "a")
        self.cli("checkpoint", env=env)
        self.assertEqual(self.commits(), 1)
        self.assertEqual(self.hgit("ls-tree", "-r", "--name-only", "HEAD").split(), ["p1/a.md"])
        self.assertEqual(self.hgit("log", "-1", "--format=%ae").strip(), "bq@localhost")
        self.assertFalse((self.t / "bogus").exists())

    def test_whole_store_missing_commits_nothing(self):
        self.ready()
        os.rename(self.ai, self.t / "ai-moved")
        r = self.cli("checkpoint")
        self.assertIn("is missing", r.stderr)
        self.assertEqual(self.commits(), 1)


# ---------------------------------------------------------------- M3

class Deletion(MemBase):
    def test_deletion_committed_with_one_notice(self):
        self.ready()
        before = self.hgit("rev-parse", "--short", "HEAD").strip()
        (self.ai / "p1" / "charter.md").unlink()
        (self.ai / "p1").rmdir()
        with mock.patch.dict(os.environ, self.env):
            self.assertEqual(m.missing_dirs(), ["p1"])
        r = self.cli("checkpoint")
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertIn("p1 deleted", lines[0])
        self.assertIn(f"restore p1 (from {before})", lines[0])
        self.assertIn(f"python3 {CLI} restore p1", lines[0])
        self.assertEqual(self.commits(), 2)
        self.assertEqual(self.hgit("ls-tree", "--name-only", "HEAD").split(), ["p2"])
        with mock.patch.dict(os.environ, self.env):
            self.assertEqual(m.missing_dirs(), [])
        self.put("p2/new.md", "n")
        self.assertEqual(self.cli("checkpoint").stdout, "")  # the notice appears once


# ---------------------------------------------------------------- M4

class Restore(MemBase):
    CONTENT = {
        "p/charter.md": b"# p\r\nCRLF kept\r\n",
        "p/bin.dat": bytes(range(256)) * 4,
        "p/deep/er/x.md": "unicode é—\n".encode(),
        "p/run.sh": b"#!/bin/sh\necho hi\n",
    }

    def seed(self):
        self.cli("init")
        (self.ai / ".gitattributes").write_text("* text=auto eol=crlf\n")  # must not alter stored bytes
        for rel, data in self.CONTENT.items():
            self.put(rel, data)
        (self.ai / "p" / "run.sh").chmod(0o755)
        os.symlink("charter.md", self.ai / "p" / "link.md")
        self.cli("checkpoint")
        return self.files(self.ai / "p")

    def test_missing_folder_restored_byte_identical(self):
        snap = self.seed()
        import shutil
        shutil.rmtree(self.ai / "p")
        self.cli("checkpoint")  # deletion recorded: default rev is the one before it
        r = self.cli("restore", "p")
        self.assertIn("restored p from", r.stdout)
        self.assertEqual(self.files(self.ai / "p"), snap)
        self.assertTrue(os.access(self.ai / "p" / "run.sh", os.X_OK))
        self.assertEqual((self.ai / "p").stat().st_mode & 0o777, self.ai.stat().st_mode & 0o777)
        self.assertEqual([n for n in os.listdir(self.ai) if "restored" in n], [])

    def test_missing_folder_before_checkpoint(self):
        snap = self.seed()
        import shutil
        shutil.rmtree(self.ai / "p")
        self.cli("restore", "p")
        self.assertEqual(self.files(self.ai / "p"), snap)

    def partial(self):
        snap = self.seed()
        self.put("p/charter.md", "NEWER EDIT\n")
        (self.ai / "p" / "bin.dat").unlink()
        self.put("p/fresh.md", "brand new\n")
        return snap, self.files(self.ai / "p")

    def test_partial_folder_loses_no_newer_bytes(self):
        snap, current = self.partial()
        short = self.hgit("rev-parse", "--short", "HEAD").strip()
        r = self.cli("restore", "p")
        self.assertEqual(self.files(self.ai / "p"), current, "restore touched the live folder")
        dest = self.ai / f"p.restored-{short}"
        self.assertEqual(self.files(dest), snap)
        self.assertIn("diff -ru", r.stdout)
        self.assertIn("--force", r.stdout)
        self.cli("checkpoint")
        self.assertNotIn(dest.name, self.hgit("ls-tree", "--name-only", "HEAD").split())
        r = self.cli("restore", "p", "--rev", short, ok=False)  # never overwrite an earlier extract
        self.assertIn("already exists", r.stderr)

    def test_force_overwrites_after_saving_current_state(self):
        snap, current = self.partial()
        old = self.hgit("rev-parse", "--short", "HEAD").strip()
        r = self.cli("restore", "p", "--rev", old, "--force")
        self.assertIn("p/charter.md", r.stdout)  # diff --stat shown
        now = self.files(self.ai / "p")
        for rel, data in snap.items():
            self.assertEqual(now[rel], data, rel)
        self.assertEqual(now["fresh.md"], b"brand new\n")  # newer file kept, not deleted
        self.assertEqual(self.hgit("show", "HEAD:p/charter.md"), "NEWER EDIT\n")  # newer bytes in history

    def test_bad_names_and_unknown(self):
        self.seed()
        for bad in ("../x", "a/b", ".hidden", ""):
            self.cli("restore", bad, ok=False)
        self.assertIn("never recorded", self.cli("restore", "nope", ok=False).stderr)
        self.assertIn("unknown revision", self.cli("restore", "p", "--rev", "zzz", ok=False).stderr)


# ---------------------------------------------------------------- M5

class Locks(MemBase):
    def test_fresh_lock_skips_quietly(self):
        self.ready()
        lock = self.hist / "index.lock"
        lock.write_text("")
        self.put("p1/b.md", "b")
        r = self.cli("checkpoint")
        self.assertEqual((r.stdout, r.stderr), ("", ""))
        self.assertEqual(self.commits(), 1)
        self.assertTrue(lock.exists())

    def test_stale_lock_warns_once_and_is_kept(self):
        self.ready()
        lock = self.hist / "index.lock"
        lock.write_text("")
        old = time.time() - 11 * 60
        os.utime(lock, (old, old))
        self.put("p1/b.md", "b")
        r = self.cli("checkpoint")
        self.assertEqual(r.stdout, "")
        self.assertEqual(len(r.stderr.splitlines()), 1, r.stderr)
        self.assertIn("stale lock", r.stderr)
        self.assertTrue(lock.exists())
        self.assertEqual(self.commits(), 1)

    def test_timeout_terminates_child(self):
        start = time.time()
        with self.assertRaises(m.MemError):
            m._spawn([sys.executable, "-c", "import time; time.sleep(30)"], 0.3)
        self.assertLess(time.time() - start, 5)


# ---------------------------------------------------------------- status / log

class StatusLog(MemBase):
    def test_status_and_log(self):
        self.ready()
        self.put("p2/lessons/b.md", "b")
        import shutil
        shutil.rmtree(self.ai / "p1")
        out = self.cli("status").stdout
        self.assertIn("uncommitted changes: 2", out)
        self.assertIn("missing folders: p1", out)
        self.assertIn("Changed: p1, p2", self.cli("log").stdout)
        self.assertEqual(len(self.cli("log", "p2").stdout.splitlines()), 1)


# ---------------------------------------------------------------- I3

class Stamp(MemBase):
    def make_repo(self):
        repo = self.t / "repos" / "myproj"
        (repo / "sub").mkdir(parents=True)
        git("init", "-q", cwd=repo)
        git("remote", "add", "origin", "https://user:s3cret@github.com/o/myproj.git", cwd=repo)
        git("remote", "add", "up", "git@github.com:o/myproj.git", cwd=repo)
        (self.ai / "myproj").mkdir()
        return repo

    def identity(self):
        return json.loads((self.ai / "myproj" / ".identity").read_text())

    def test_stamp_lists_root_and_remotes_without_credentials(self):
        repo = self.make_repo()
        self.cli("stamp", cwd=repo / "sub")
        ident = self.identity()
        self.assertEqual(ident["project"], "myproj")
        self.assertEqual(ident["roots"], [str(repo.resolve())])
        self.assertEqual(ident["remotes"], ["git@github.com:o/myproj.git", "https://github.com/o/myproj.git"])
        self.assertNotIn("s3cret", (self.ai / "myproj" / ".identity").read_text())

    def test_stamp_from_worktree_names_main_checkout(self):
        repo = self.make_repo()
        git("commit", "-q", "--allow-empty", "-m", "i", cwd=repo)
        wt = self.t / "repos" / "myproj-wt"
        git("worktree", "add", "-q", str(wt), cwd=repo)
        self.cli("stamp", cwd=wt)
        ident = self.identity()
        self.assertEqual(ident["roots"], [str(repo.resolve())])
        self.assertEqual(len(ident["remotes"]), 2)

    def test_stamp_refusals(self):
        self.assertIn("not inside a git repository", self.cli("stamp", ok=False).stderr)
        other = self.t / "repos" / "unknown"
        other.mkdir(parents=True)
        git("init", "-q", cwd=other)
        self.assertIn("no memory folder", self.cli("stamp", cwd=other, ok=False).stderr)


if __name__ == "__main__":
    unittest.main()

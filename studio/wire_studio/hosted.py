"""Hosted mode: Studio's views for a release read from a GitHub repository.

Local Studio reads a clone on the director's machine. Hosted Studio runs as
a service behind another site's sign-in and reads the repository itself,
read only, with its own GitHub credential. It uses the same readers
(`record.py`, `runnable.py`, `tickets.py`) on a checkout of the branch, so it
gives the same answer as local Studio for the same commit.

What differs from local mode:

- The repository comes with each request (`X-Wire-Repo: <owner>/<repo>`),
  set by the site that serves the page, never by the browser.
- Releases are gathered from several branches: the default branch, branches
  the request names (`X-Wire-Branches`), and `feature/*` and `release/*`
  branches. A release found on more than one branch is shown from the one
  whose `status.md` was updated last.
- No launch endpoint, no directives, no lanes. Every POST, PUT, PATCH and
  DELETE gets 405.
- Results are cached in memory per repository, branch and commit: branch
  heads for `REFS_TTL` seconds, loaded releases for `RESULT_TTL` seconds.

The repository is reached through a client with four methods (`refs`,
`list_releases`, `read`, `checkout`; `prune` is optional), so the tests can
use a fake. `GitClient` is the real one: a blobless clone of every branch
(history and trees, file contents fetched when read), with a worktree per
commit. History is kept because a ticket's changed files come from git.
"""

import base64
import json
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .record import load_release, read_engagement, safe_file, split_front_matter, summarise

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
BASE_PATTERN = re.compile(r"^/(?:[A-Za-z0-9_-]+/)*$")
BACK_PATTERN = re.compile(r"^/[A-Za-z0-9_/-]{0,200}$")
STATUS_PATH = re.compile(r"^\.wire/releases/([^/]+)/status\.md$")
DISCOVERED_PREFIXES = ("feature/", "release/")
MAX_DISCOVERED = 30
MAX_NAMED = 10
REFS_TTL = 30
RESULT_TTL = 60


class RepoError(Exception):
    """The repository could not be read (missing, no access, network)."""


# ---------------------------------------------------------------------------
# Choosing branches and releases (pure, tested directly)
# ---------------------------------------------------------------------------
def candidate_branches(refs, named=()):
    """Branches to look for releases on, in preference order: the branches
    the project names, then `feature/*` and `release/*` (newest first, as the
    client lists them, at most MAX_DISCOVERED), then the default branch."""
    branches = refs.get("branches") or {}
    out = []
    for b in named:
        if b in branches and b not in out:
            out.append(b)
    found = [b for b in branches if b.startswith(DISCOVERED_PREFIXES) and b not in out]
    out += found[:MAX_DISCOVERED]
    default = refs.get("default")
    if default in branches and default not in out:
        out.append(default)
    return out


def updated_key(value):
    """A sortable form of status.md's `last_updated` (date, datetime or text)."""
    if value is None:
        return ""
    text = str(value)  # a YAML date or datetime prints as ISO text
    return text.strip().replace("T", " ")


def choose_releases(found):
    """`found`: [(branch, release name, last_updated)] in branch preference
    order. One entry per release, from the branch with the latest
    last_updated (a tie goes to the earlier, preferred branch), most
    recently updated first."""
    best = {}
    seen = {}
    for rank, (branch, name, updated) in enumerate(found):
        seen.setdefault(name, []).append(branch)
        key = updated_key(updated)
        cur = best.get(name)
        if cur is None or key > cur["_key"]:
            best[name] = {"name": name, "branch": branch, "last_updated": key, "_key": key, "_rank": rank}
    out = []
    for name, e in best.items():
        e["other_branches"] = [b for b in seen[name] if b != e["branch"]]
        out.append(e)
    out.sort(key=lambda e: (e["_key"], -e["_rank"]), reverse=True)
    for e in out:
        del e["_key"], e["_rank"]
    return out


def parse_request_headers(headers):
    """The repository, named branches, page base and back link a request
    carries. Raises ValueError for a missing or malformed repository."""
    repo = (headers.get("X-Wire-Repo") or "").strip()
    if not REPO_PATTERN.match(repo) or ".." in repo:
        raise ValueError("X-Wire-Repo must be <owner>/<repo>")
    named = []
    for b in (headers.get("X-Wire-Branches") or "").split(","):
        b = b.strip()
        if b and BRANCH_PATTERN.match(b) and ".." not in b and b not in named:
            named.append(b)
    base = (headers.get("X-Wire-Base") or "/").strip()
    back = (headers.get("X-Wire-Back") or "").strip()
    return {"repo": repo, "named": tuple(named[:MAX_NAMED]),
            "base": base if BASE_PATTERN.match(base) else "/",
            "back": back if BACK_PATTERN.match(back) and ".." not in back else ""}


# ---------------------------------------------------------------------------
# The record, through a client, with a cache
# ---------------------------------------------------------------------------
class HostedRecord:
    def __init__(self, framework, client, clock=datetime.now, monotonic=time.monotonic,
                 refs_ttl=REFS_TTL, result_ttl=RESULT_TTL, allowed_owners=()):
        self.framework = framework
        self.client = client
        self.clock = clock
        self.monotonic = monotonic
        self.refs_ttl = refs_ttl
        self.result_ttl = result_ttl
        self.allowed_owners = {o.lower() for o in allowed_owners if o}
        self.lock = threading.RLock()
        self._refs = {}       # repo -> (time, refs)
        self._listing = {}    # (repo, sha) -> [release names]
        self._status = {}     # (repo, sha, name) -> last_updated
        self._results = {}    # key -> (time, value)

    def _check_repo(self, repo):
        if self.allowed_owners and repo.split("/")[0].lower() not in self.allowed_owners:
            raise PermissionError(f"{repo} is not in an allowed GitHub organisation")

    def refs(self, repo):
        self._check_repo(repo)
        with self.lock:
            hit = self._refs.get(repo)
            if hit and self.monotonic() - hit[0] < self.refs_ttl:
                return hit[1]
            refs = self.client.refs(repo)
            self._refs[repo] = (self.monotonic(), refs)
            return refs

    def _cached(self, key, build):
        with self.lock:
            hit = self._results.get(key)
            if hit and self.monotonic() - hit[0] < self.result_ttl:
                return hit[1]
        value = build()
        with self.lock:
            self._results[key] = (self.monotonic(), value)
            if len(self._results) > 256:
                for k, _ in sorted(self._results.items(), key=lambda kv: kv[1][0])[:64]:
                    del self._results[k]
        return value

    def releases(self, repo, named=()):
        """[{name, branch, sha, last_updated, other_branches}], most recent first."""
        refs = self.refs(repo)
        branches = refs["branches"]
        found = []
        for b in candidate_branches(refs, named):
            sha = branches[b]
            with self.lock:
                if (repo, sha) not in self._listing:
                    self._listing[(repo, sha)] = sorted(self.client.list_releases(repo, sha))
                names = self._listing[(repo, sha)]
            for name in names:
                key = (repo, sha, name)
                with self.lock:
                    if key not in self._status:
                        text = self.client.read(repo, sha, f".wire/releases/{name}/status.md") or ""
                        fm, _ = split_front_matter(text)
                        self._status[key] = fm.get("last_updated")
                    updated = self._status[key]
                found.append((b, name, updated))
        out = choose_releases(found)
        for e in out:
            e["sha"] = branches[e["branch"]]
        return out

    def _entry(self, repo, named, name):
        for e in self.releases(repo, named):
            if e["name"] == name:
                return e
        raise KeyError(name)

    def checkout(self, repo, sha):
        with self.lock:
            return Path(self.client.checkout(repo, sha))

    def release(self, repo, named, name):
        e = self._entry(repo, named, name)

        def build():
            rel = load_release(self.framework, self.checkout(repo, e["sha"]), name, self.clock())
            rel.update(branch=e["branch"], sha=e["sha"], other_branches=e["other_branches"])
            rel["lanes"] = []  # the console's agent status covers lanes; no stall rule here
            return rel
        return self._cached(("release", repo, e["branch"], e["sha"], name), build)

    def summary(self, repo, named):
        entries = self.releases(repo, named)
        refs = self.refs(repo)

        def build():
            rows = []
            for e in entries:
                try:
                    row = summarise(self.release(repo, named, e["name"]))
                except Exception as ex:  # one broken release must not hide the others
                    row = {"name": e["name"], "error": str(ex)}
                row.update(branch=e["branch"], last_updated=e["last_updated"], other_branches=e["other_branches"])
                rows.append(row)
            default = refs.get("default")
            engagement = {"present": False, "orchestration_mode": "orchestrated"}
            if default in refs["branches"]:
                root = self.checkout(repo, refs["branches"][default])
                engagement = read_engagement(root)
                if engagement.get("title") == root.name:  # no title in context.md: not the commit id
                    engagement["title"] = repo
            engagement.setdefault("title", repo)
            return {
                "version": __version__, "repo": repo, "hosted": True,
                "framework": {"root": "", "layout": self.framework.layout},
                "engagement": engagement, "releases": rows, "launch": None,
                "now": self.clock().strftime("%Y-%m-%d %H:%M"),
            }
        key = ("summary", repo, tuple((e["name"], e["branch"], e["sha"]) for e in entries))
        result = self._cached(key, build)
        if hasattr(self.client, "prune"):
            keep = {e["sha"] for e in entries}
            if refs.get("default") in refs["branches"]:
                keep.add(refs["branches"][refs["default"]])
            with self.lock:
                self.client.prune(repo, keep)
        return result

    def file(self, repo, named, release, path):
        e = self._entry(repo, named, release)
        root = self.checkout(repo, e["sha"])
        p = safe_file(root, release, path)
        return {"path": str(p.relative_to(root.resolve())), "text": p.read_text(encoding="utf-8", errors="replace")}


# ---------------------------------------------------------------------------
# The real client: git over HTTPS with a read-only token
# ---------------------------------------------------------------------------
class GitClient:
    """Reads GitHub repositories with git. One blobless bare clone per
    repository (every branch's history and trees; file contents fetched when
    first read) and one detached worktree per commit shown.

    The token reaches git through GIT_CONFIG_* environment variables, never a
    URL or a file, and is set in this process's environment so the git calls
    `scripts/ticket_delivery.py` makes for a ticket's changed files can fetch
    file contents too."""

    def __init__(self, root, token=None, base_url="https://github.com/", keep=8):
        self.root = Path(root)
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.keep = keep
        (self.root / "mirrors").mkdir(parents=True, exist_ok=True)
        (self.root / "trees").mkdir(parents=True, exist_ok=True)
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        os.environ["GIT_OPTIONAL_LOCKS"] = "0"
        if token:
            auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
            os.environ.update({
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": f"http.{self.base_url}.extraheader",
                "GIT_CONFIG_VALUE_0": f"Authorization: Basic {auth}",
            })

    def _git(self, *args, cwd=None, timeout=120):
        try:
            out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise RepoError(f"git {args[0]} failed: {e}") from None
        if out.returncode != 0:
            raise RepoError(f"git {args[0]} failed: {out.stderr.strip()[-300:]}")
        return out.stdout

    def _slug(self, repo):
        return repo.replace("/", "__")

    def _mirror(self, repo):
        m = self.root / "mirrors" / f"{self._slug(repo)}.git"
        if not m.exists():
            tmp = m.with_suffix(".tmp")
            shutil.rmtree(tmp, ignore_errors=True)
            self._git("clone", "--quiet", "--bare", "--filter=blob:none", f"{self.base_url}{repo}.git", str(tmp))
            self._git("--git-dir", str(tmp), "config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*")
            tmp.rename(m)
        return m

    def refs(self, repo):
        m = self.root / "mirrors" / f"{self._slug(repo)}.git"
        fresh = not m.exists()
        m = self._mirror(repo)
        if not fresh:
            self._git("--git-dir", str(m), "fetch", "--quiet", "--prune", "origin")
        default = self._git("--git-dir", str(m), "symbolic-ref", "--short", "HEAD").strip()
        branches = {}
        listing = self._git("--git-dir", str(m), "for-each-ref", "--sort=-committerdate",
                            "--format=%(refname:short) %(objectname)", "refs/heads")
        for line in listing.splitlines():
            name, sha = line.rsplit(" ", 1)
            branches[name] = sha
        return {"default": default, "branches": branches}

    def list_releases(self, repo, sha):
        m = self._mirror(repo)
        try:
            listing = self._git("--git-dir", str(m), "ls-tree", "-r", "--name-only", sha, "--", ".wire/releases")
        except RepoError:
            return []
        return [mm.group(1) for mm in map(STATUS_PATH.match, listing.splitlines()) if mm]

    def read(self, repo, sha, path):
        m = self._mirror(repo)
        try:
            return self._git("--git-dir", str(m), "show", f"{sha}:{path}")
        except RepoError:
            return None

    def checkout(self, repo, sha):
        if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
            raise RepoError("not a commit id")
        m = self._mirror(repo)
        dest = self.root / "trees" / self._slug(repo) / sha
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            self._git("--git-dir", str(m), "worktree", "add", "--quiet", "--detach", "--force", str(dest), sha, timeout=300)
        os.utime(dest)
        return dest

    def prune(self, repo, keep_shas):
        """Remove worktrees beyond the newest `keep`, never one in use."""
        parent = self.root / "trees" / self._slug(repo)
        if not parent.is_dir():
            return
        trees = sorted(parent.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        m = self._mirror(repo)
        for p in trees[self.keep:]:
            if p.name in keep_shas:
                continue
            try:
                self._git("--git-dir", str(m), "worktree", "remove", "--force", str(p))
            except RepoError:
                shutil.rmtree(p, ignore_errors=True)
        self._git("--git-dir", str(m), "worktree", "prune")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def make_hosted_handler(hosted):
    from .server import static_file

    class Handler(BaseHTTPRequestHandler):
        server_version = f"WireStudio/{__version__} hosted"

        def log_message(self, fmt, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _refuse(self):
            self._send(405, {"error": "Hosted Wire Studio is read only. Work on a release starts from its tickets."})

        do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            url = urlparse(self.path)
            path, q = url.path, parse_qs(url.query)
            if path == "/healthz":
                return self._send(200, {"ok": True, "version": __version__})
            try:
                req = parse_request_headers(self.headers)
            except ValueError as e:
                if path.startswith("/api/"):
                    return self._send(400, {"error": str(e)})
                req = {"base": "/", "back": ""}
            try:
                if path == "/api/summary":
                    return self._send(200, hosted.summary(req["repo"], req["named"]))
                if path.startswith("/api/release/"):
                    name = unquote(path[len("/api/release/"):])
                    return self._send(200, hosted.release(req["repo"], req["named"], name))
                if path == "/api/file":
                    return self._send(200, hosted.file(req["repo"], req["named"], q.get("release", [""])[0],
                                                       q.get("path", [""])[0]))
                if path.startswith("/api/"):
                    return self._send(404, {"error": "not found"})
                code, data, ctype = static_file(path, {"token": "", "mode": "hosted",
                                                       "base": req["base"], "back": req["back"]})
                return self._send(code, data, ctype)
            except KeyError as e:
                return self._send(404, {"error": f"no release {e}"})
            except FileNotFoundError as e:
                return self._send(404, {"error": f"not found: {e}"})
            except PermissionError as e:
                return self._send(403, {"error": str(e)})
            except RepoError as e:
                return self._send(502, {"error": f"Could not read the repository: {e}"})

    return Handler


def serve_hosted(hosted, host="0.0.0.0", port=8080):
    return ThreadingHTTPServer((host, port), make_hosted_handler(hosted))

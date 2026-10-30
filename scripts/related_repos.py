#!/usr/bin/env python3
"""Related repos (wire#381; rules in specs/utils/repos.md). Plain script, no AI call.

  related_repos.py list [--json]                    each repo: role, local copy, commit, fetch age, state
  related_repos.py refresh [<id>]                   clone (blobless) or fetch the default branch
  related_repos.py find <text> [--repo <id>] [--path <glob>] [--regex] [--max N] [--json]
                                                    git grep at the recorded commit, read only
  related_repos.py add <github_url> --id <id> --role <role> [--branch B] [--paths a,b]
                       [--description T] [--lookup L] [--yes]
                                                    propose an entry; --yes writes context.md
  related_repos.py remove <id> [--yes]              propose removing an entry; --yes writes context.md
  related_repos.py check                            check the list and the local file

An engagement lists the client's other repositories once, in the
`related_repos:` block of .wire/engagement/context.md (committed). Where each
person's copy is lives in .wire/local/repos.yml (git-ignored), as `id: path`.
A repo with no local path is cloned blobless to ~/.wire/repos/<org>/<repo>/
(WIRE_REPOS_HOME overrides the root) with the person's own git access. The
commit each refresh read is recorded in .wire/local/repos_state.json, and
`find` reads at that commit, so a citation names what was read.

Read only. Nothing here commits, pushes, checks out, branches or writes a file
in a related repo. In a person's own clone, refresh runs `git fetch`, which
moves only the remote-tracking ref. No credential is asked for or stored: git
runs with GIT_TERMINAL_PROMPT=0, a URL with a user or token in it is refused,
and a repo that cannot be reached is reported and skipped.

When context.md has `client_repo:` with a github_url, it is read as one more
entry, id `client_repo`, role `code`, unless a related_repos entry has the same
URL. Its committed local_path is used as its local copy.

The schema is wire/schemas/related-repos-schema.md. Run in the engagement
repository (or pass --repo).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTEXT_FILE = Path(".wire") / "engagement" / "context.md"
LOCAL_FILE = Path(".wire") / "local" / "repos.yml"
STATE_FILE = Path(".wire") / "local" / "repos_state.json"
IGNORE_LINE = ".wire/local/"
ROLES = ["code", "dbt", "orchestration", "ingestion", "lookml", "omni", "infrastructure", "other"]
LOOKUPS = ["on_request", "offer", "auto"]
FIELDS = ["id", "github_url", "default_branch", "role", "paths", "description", "lookup"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
CLIENT_REPO_ID = "client_repo"
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": "", "GCM_INTERACTIVE": "never"}


# ---------------------------------------------------------------------------
# Reading context.md front matter without a YAML library (the plugin needs
# none). Only the two blocks this script uses are read: related_repos (a list
# of flat mappings; `paths` inline [a, b] or a block list) and client_repo (a
# flat mapping). The grammar is in the schema.
# ---------------------------------------------------------------------------

def front_matter(text: str) -> tuple[list[str], int, int]:
    """(lines, start, end): the front matter is lines[start:end], between the --- markers."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return lines, 0, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines, 1, i
    return lines, 0, 0


def scalar(value: str):
    v = value.split(" #", 1)[0].strip()
    if v in ("", "null", "~"):
        return None
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def block_span(lines: list[str], start: int, end: int, key: str) -> tuple[int, int] | None:
    """Line span [a, b) of a top-level key's block in the front matter, or None."""
    for i in range(start, end):
        if re.match(rf"^{re.escape(key)}:", lines[i]):
            j = i + 1
            while j < end and (not lines[j].strip() or lines[j][0] in " \t-#"):
                j += 1
            # Trailing blank and comment lines belong to whatever follows.
            while j > i + 1 and (not lines[j - 1].strip() or lines[j - 1].lstrip().startswith("#")):
                j -= 1
            return i, j
    return None


def parse_list_block(lines: list[str]) -> list[dict]:
    entries, current, list_key = [], None, None
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)-\s+(\w+):\s*(.*)$", raw)
        if m and (current is None or len(m.group(1)) <= current["_indent"]):
            current = {"_indent": len(m.group(1)), m.group(2): scalar(m.group(3))}
            entries.append(current)
            list_key = None
            continue
        if current is None:
            continue
        m = re.match(r"^\s+(\w+):\s*(.*)$", raw)
        if m:
            value = scalar(m.group(2))
            current[m.group(1)] = value if value is not None or m.group(2).strip() else []
            list_key = m.group(1) if not m.group(2).split(" #", 1)[0].strip() else None
            continue
        m = re.match(r"^\s+-\s+(.+)$", raw)
        if m and list_key:
            current[list_key].append(scalar(m.group(1)))
    for e in entries:
        e.pop("_indent", None)
    return entries


def parse_mapping_block(lines: list[str]) -> dict:
    out = {}
    for raw in lines:
        m = re.match(r"^\s+(\w+):\s*(.*)$", raw)
        if m and not raw.lstrip().startswith("#"):
            out[m.group(1)] = scalar(m.group(2))
    return out


def read_context(repo: Path) -> tuple[list[dict], dict | None]:
    """(related_repos entries as written, client_repo mapping or None)."""
    path = repo / CONTEXT_FILE
    if not path.exists():
        return [], None
    lines, start, end = front_matter(path.read_text(encoding="utf-8"))
    span = block_span(lines, start, end, "related_repos")
    entries = []
    if span:
        entries = parse_list_block(lines[span[0] + 1:span[1]])
    span = block_span(lines, start, end, "client_repo")
    client = parse_mapping_block(lines[span[0] + 1:span[1]]) if span else None
    return entries, client


def normalise_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"^git@([^:]+):", r"https://\1/", u)
    return u.lower()


def org_repo(url: str) -> tuple[str, str]:
    """<org>, <repo> from the last two path parts of a URL (https, ssh, file)."""
    u = re.sub(r"\.git$", "", (url or "").strip().rstrip("/"))
    u = re.sub(r"^git@[^:]+:", "", u)
    parts = [p for p in re.split(r"[/:]", u) if p]
    if len(parts) < 2:
        return "", ""
    return parts[-2], parts[-1]


def has_credentials(url: str) -> bool:
    return bool(re.match(r"^[a-z+]+://[^/@]+@", url or "", re.I))


def entries(repo: Path) -> list[dict]:
    """The related repos with defaults applied, client_repo folded in as one entry."""
    listed, client = read_context(repo)
    out = []
    for e in listed:
        e = dict(e)
        e.setdefault("default_branch", "main")
        e["default_branch"] = e["default_branch"] or "main"
        e.setdefault("lookup", "on_request")
        e["lookup"] = e["lookup"] or "on_request"
        paths = e.get("paths") or []
        e["paths"] = paths if isinstance(paths, list) else [paths]
        e["source"] = "related_repos"
        out.append(e)
    if client and client.get("github_url"):
        urls = {normalise_url(e.get("github_url")) for e in out}
        if normalise_url(client["github_url"]) not in urls:
            out.append({"id": CLIENT_REPO_ID, "github_url": client["github_url"],
                        "default_branch": client.get("default_branch") or "main", "role": "code",
                        "paths": [], "description": "client_repo in context.md", "lookup": "on_request",
                        "source": "client_repo", "committed_local_path": client.get("local_path")})
    return out


# ---------------------------------------------------------------------------
# Local copies and state (both under .wire/local/, git-ignored)
# ---------------------------------------------------------------------------

def read_local(repo: Path) -> dict:
    path = repo / LOCAL_FILE
    out = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Za-z0-9_-]+):\s*(.+?)\s*$", raw)
            if m and not raw.lstrip().startswith("#"):
                value = scalar(m.group(2))
                if value:
                    out[m.group(1)] = value
    return out


def read_state(repo: Path) -> dict:
    path = repo / STATE_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except ValueError:
        return {}


def write_state(repo: Path, state: dict) -> None:
    path = repo / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ensure_ignored(repo)


def ensure_ignored(repo: Path) -> bool:
    """Add .wire/local/ to the engagement repo's .gitignore if missing. True if it was added."""
    gitignore = repo / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if any(l.strip() in (IGNORE_LINE, IGNORE_LINE.rstrip("/"), "/" + IGNORE_LINE) for l in text.splitlines()):
        return False
    if text and not text.endswith("\n"):
        text += "\n"
    gitignore.write_text(text + IGNORE_LINE + "\n", encoding="utf-8")
    return True


def cache_root() -> Path:
    return Path(os.environ.get("WIRE_REPOS_HOME") or Path.home() / ".wire" / "repos")


def local_copy(repo: Path, entry: dict, local: dict) -> tuple[Path | None, str]:
    """(path, kind): kind is `own` for a person's clone, `cache` for Wire's blobless clone."""
    own = local.get(entry["id"]) or entry.get("committed_local_path")
    if own:
        return Path(os.path.expanduser(own)), "own"
    org, name = org_repo(entry.get("github_url", ""))
    if not org:
        return None, "cache"
    return cache_root() / org / name, "cache"


def git(path: Path | None, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    cmd = ["git"] + (["-C", str(path)] if path else []) + list(args)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **GIT_ENV})
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "timed out")


def read_ref(path: Path, kind: str, branch: str) -> str | None:
    """The commit of the default branch in a local copy: the remote-tracking ref in
    a person's clone (what was fetched, not what they have checked out), the branch
    itself in Wire's bare clone."""
    refs = [f"refs/remotes/origin/{branch}", f"refs/heads/{branch}"] if kind == "own" else [f"refs/heads/{branch}"]
    for ref in refs:
        r = git(path, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return None


def first_line(text: str) -> str:
    """The line of git's stderr that says what went wrong (its `fatal:` line if any)."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    fatal = [l for l in lines if l.startswith(("fatal:", "error:"))]
    return (fatal or lines or ["unknown error"])[0]


def refresh_one(repo: Path, entry: dict, local: dict, now: str) -> dict:
    """Clone or fetch one repo. Returns its new state record."""
    path, kind = local_copy(repo, entry, local)
    branch = entry["default_branch"]
    url = entry.get("github_url") or ""
    record = {"path": str(path) if path else None, "kind": kind, "refreshed_at": now}
    if has_credentials(url):
        return {**record, "status": "unreachable", "reason": "the URL holds a user or token; remove it from context.md"}
    if path is None:
        return {**record, "status": "unreachable", "reason": f"cannot read an org and repo from {url!r}"}
    if kind == "own":
        if git(path, "rev-parse", "--git-dir").returncode != 0:
            return {**record, "status": "unreachable", "reason": f"{path} is not a git repository"}
        r = git(path, "fetch", "--quiet", "--no-write-fetch-head", "origin", branch)
    elif (path / "HEAD").exists():
        r = git(path, "fetch", "--quiet", "--no-write-fetch-head", "origin", f"+refs/heads/{branch}:refs/heads/{branch}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        r = git(None, "clone", "--quiet", "--bare", "--filter=blob:none", "--single-branch", "--branch", branch, url, str(path))
    commit = read_ref(path, kind, branch) if path.exists() else None
    if r.returncode != 0:
        # A failed fetch on a copy that already has the branch keeps the old commit.
        reason = first_line(r.stderr)
        if commit:
            return {**record, "status": "stale", "commit": commit, "reason": f"fetch failed: {reason}"}
        return {**record, "status": "unreachable", "reason": reason}
    if not commit:
        return {**record, "status": "unreachable", "reason": f"no branch {branch} after fetch"}
    return {**record, "status": "ready", "commit": commit, "fetched_at": now}


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def age(fetched_at: str | None, now: datetime) -> str:
    if not fetched_at:
        return "never"
    try:
        then = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    minutes = int((now - then).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}m"
    if minutes < 48 * 60:
        return f"{minutes // 60}h"
    return f"{minutes // 1440}d"


def status_rows(repo: Path, now: datetime) -> list[dict]:
    local, state = read_local(repo), read_state(repo)
    rows = []
    for e in entries(repo):
        path, kind = local_copy(repo, e, local)
        s = state.get(e["id"], {})
        commit = s.get("commit")
        if s.get("status") in ("ready", "stale") and commit:
            status = s["status"]
        elif s.get("status") == "unreachable":
            status = "unreachable"
        elif path is not None and path.exists() and read_ref(path, kind, e["default_branch"]):
            # A person's clone that was never refreshed through Wire can still be read.
            commit = read_ref(path, kind, e["default_branch"])
            status = "not refreshed"
        else:
            status = "not fetched"
        rows.append({"id": e["id"], "role": e.get("role"), "lookup": e["lookup"], "source": e["source"],
                     "local_copy": str(path) if path else None, "kind": kind, "commit": commit,
                     "short": commit[:7] if commit else None, "fetched_at": s.get("fetched_at"),
                     "age": age(s.get("fetched_at"), now), "status": status, "reason": s.get("reason")})
    return rows


# ---------------------------------------------------------------------------
# find
# ---------------------------------------------------------------------------

def find(repo: Path, text: str, only: str | None, path_glob: str | None, regex: bool, limit: int,
         now: datetime) -> tuple[list[dict], list[str]]:
    """(hits, notes). Each hit: id, commit, short, path, line, text, citation."""
    local = read_local(repo)
    hits, notes = [], []
    rows = {r["id"]: r for r in status_rows(repo, now)}
    chosen = [e for e in entries(repo) if not only or e["id"] == only]
    if only and not chosen:
        notes.append(f"no related repo with id {only}")
    for e in chosen:
        row = rows[e["id"]]
        if not row["commit"]:
            if row["status"] == "unreachable":
                notes.append(f"{e['id']}: unreachable ({row.get('reason')}); skipped")
            else:
                notes.append(f"{e['id']}: not fetched; run refresh first")
            continue
        if row["status"] == "not refreshed":
            notes.append(f"{e['id']}: read at the clone's origin/{e['default_branch']}, not refreshed through Wire")
        path, _ = local_copy(repo, e, local)
        globs = [path_glob] if path_glob else e.get("paths") or []
        pathspec = [f":(glob){g.rstrip('/') + '/**' if g.endswith('/') else g}" for g in globs]
        args = ["grep", "-n", "-I", "--null", "--no-color", "-E" if regex else "-F", "-e", text, row["commit"]]
        r = git(path, *args, "--", *pathspec) if pathspec else git(path, *args)
        if r.returncode not in (0, 1):
            notes.append(f"{e['id']}: git grep failed: {first_line(r.stderr)}")
            continue
        found = []
        for line in r.stdout.splitlines():
            parts = line.split("\0")
            if len(parts) < 3:
                continue
            file_path = parts[0].split(":", 1)[1] if ":" in parts[0] else parts[0]
            found.append({"id": e["id"], "commit": row["commit"], "short": row["short"], "path": file_path,
                          "line": int(parts[1]), "text": parts[2].strip(),
                          "citation": f"{e['id']}@{row['short']}:{file_path}"})
        found.sort(key=lambda h: (h["path"], h["line"]))
        if len(found) > limit:
            notes.append(f"{e['id']}: {len(found)} hits, first {limit} shown; narrow with --path")
        hits.extend(found[:limit])
    return hits, notes


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def check(repo: Path) -> list[str]:
    problems = []
    listed, _ = read_context(repo)
    seen = set()
    for i, e in enumerate(listed, 1):
        name = e.get("id") or f"entry {i}"
        if not e.get("id"):
            problems.append(f"{name}: no id")
        elif not ID_RE.match(str(e["id"])):
            problems.append(f"{name}: id must be lower case letters, digits, - and _")
        elif e["id"] in seen:
            problems.append(f"{name}: id listed twice")
        elif e["id"] == CLIENT_REPO_ID:
            problems.append(f"{name}: id {CLIENT_REPO_ID} is kept for the client_repo entry")
        seen.add(e.get("id"))
        if not e.get("github_url"):
            problems.append(f"{name}: no github_url")
        elif has_credentials(e["github_url"]):
            problems.append(f"{name}: github_url holds a user or token; never commit a credential")
        elif not org_repo(e["github_url"])[0]:
            problems.append(f"{name}: cannot read an org and repo from github_url")
        if e.get("role") not in ROLES:
            problems.append(f"{name}: role {e.get('role')!r} is not one of {', '.join(ROLES)}")
        if e.get("lookup") not in (None, *LOOKUPS):
            problems.append(f"{name}: lookup {e.get('lookup')!r} is not one of {', '.join(LOOKUPS)}")
        unknown = [k for k in e if k not in FIELDS]
        if unknown:
            problems.append(f"{name}: unknown field(s) {', '.join(unknown)}")
    urls = [normalise_url(e.get("github_url")) for e in listed if e.get("github_url")]
    for u in sorted({u for u in urls if urls.count(u) > 1}):
        problems.append(f"{u}: listed more than once")
    ids = {e["id"] for e in entries(repo)}
    for key in read_local(repo):
        if key not in ids:
            problems.append(f"{LOCAL_FILE}: {key} is not a related repo")
    if (repo / ".wire" / "local").exists():
        gi = repo / ".gitignore"
        lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
        if not any(l.strip() in (IGNORE_LINE, IGNORE_LINE.rstrip("/"), "/" + IGNORE_LINE) for l in lines):
            problems.append(f".gitignore: {IGNORE_LINE} is not ignored, so the local files could be committed")
    return problems


# ---------------------------------------------------------------------------
# add and remove: text edits to the front matter, nothing else in the file moves
# ---------------------------------------------------------------------------

def format_entry(e: dict) -> list[str]:
    out = [f"  - id: {e['id']}"]
    for key in FIELDS[1:]:
        value = e.get(key)
        if value in (None, [], ""):
            continue
        if isinstance(value, list):
            out.append(f"    {key}: [{', '.join(value)}]")
        elif key == "description":
            out.append(f"    {key}: \"{value}\"")
        else:
            out.append(f"    {key}: {value}")
    return out


def add_entry(text: str, entry: dict) -> str:
    lines, start, end = front_matter(text)
    if end == 0:
        raise ValueError(f"{CONTEXT_FILE} has no front matter")
    span = block_span(lines, start, end, "related_repos")
    new = format_entry(entry)
    if span:
        a, b = span
        if lines[a].strip() != "related_repos:":
            lines[a] = "related_repos:"  # `related_repos: []` becomes a block
        lines[b:b] = new
    else:
        lines[end:end] = ["related_repos:"] + new
    return "\n".join(lines) + "\n"


def remove_entry(text: str, entry_id: str) -> str:
    lines, start, end = front_matter(text)
    span = block_span(lines, start, end, "related_repos")
    if not span:
        raise ValueError(f"no related_repos block in {CONTEXT_FILE}")
    a, b = span
    for i in range(a + 1, b):
        m = re.match(r"^(\s*)-\s+id:\s*(.+)$", lines[i])
        if m and scalar(m.group(2)) == entry_id:
            j = i + 1
            while j < b and not re.match(rf"^{m.group(1)}-\s", lines[j]):
                j += 1
            del lines[i:j]
            b -= j - i
            if not parse_list_block(lines[a + 1:b]):
                del lines[a:b]  # the last entry: drop the block, as if it had never been added
            return "\n".join(lines) + "\n"
    raise ValueError(f"no related repo with id {entry_id}")


def unified(before: str, after: str) -> str:
    import difflib
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        str(CONTEXT_FILE), str(CONTEXT_FILE)))


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def now_utc() -> datetime:
    fixed = os.environ.get("WIRE_RELATED_REPOS_NOW")
    if fixed:
        return datetime.fromisoformat(fixed.replace("Z", "+00:00"))
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="engagement repository (default: current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    rf = sub.add_parser("refresh")
    rf.add_argument("id", nargs="?")
    fd = sub.add_parser("find")
    fd.add_argument("text")
    fd.add_argument("--repo-id", "--in", dest="only", help="one related repo by id")
    fd.add_argument("--path", dest="path_glob", help="glob, e.g. 'models/**/*.yml' (default: the entry's paths)")
    fd.add_argument("--regex", action="store_true", help="extended regular expression (default: fixed text)")
    fd.add_argument("--max", type=int, default=50, help="hits per repo (default 50)")
    fd.add_argument("--json", action="store_true")
    ad = sub.add_parser("add")
    ad.add_argument("github_url")
    ad.add_argument("--id", required=True)
    ad.add_argument("--role", required=True, choices=ROLES)
    ad.add_argument("--branch", default="main")
    ad.add_argument("--paths", default="", help="comma-separated, e.g. 'dags_*/,plugins/'")
    ad.add_argument("--description", default="")
    ad.add_argument("--lookup", default="on_request", choices=LOOKUPS)
    ad.add_argument("--yes", action="store_true", help="write context.md (without it, only the proposal is shown)")
    rm = sub.add_parser("remove")
    rm.add_argument("id")
    rm.add_argument("--yes", action="store_true")
    sub.add_parser("check")
    # `find --repo <id>` is the form in the issue and the spec; --repo before the
    # sub-command is the engagement repository, as in persona.py.
    argv = list(sys.argv[1:] if argv is None else argv)
    if "find" in argv:
        k = argv.index("find")
        argv = argv[:k + 1] + ["--repo-id" if a == "--repo" else a for a in argv[k + 1:]]
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    now = now_utc()

    if args.cmd == "list":
        rows = status_rows(repo, now)
        if args.json:
            print(json.dumps(rows, indent=2, sort_keys=True))
            return 0
        if not rows:
            print("No related repos (no related_repos or client_repo in .wire/engagement/context.md)")
            return 0
        print("| Repo | Role | Lookup | Commit | Fetched | State | Local copy |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            state = r["status"] + (f": {r['reason']}" if r["status"] in ("unreachable", "stale") and r.get("reason") else "")
            print(f"| {r['id']} | {r['role']} | {r['lookup']} | {r['short'] or '-'} | {r['age']} | {state} | {r['local_copy'] or '-'} |")
        return 0

    if args.cmd == "refresh":
        chosen = [e for e in entries(repo) if not args.id or e["id"] == args.id]
        if args.id and not chosen:
            print(f"no related repo with id {args.id}", file=sys.stderr)
            return 2
        local, state = read_local(repo), read_state(repo)
        for e in chosen:
            record = refresh_one(repo, e, local, iso(now))
            if record["status"] == "stale" or (record["status"] == "unreachable" and state.get(e["id"], {}).get("commit")):
                # Keep the last good fetch time and commit; say why this one failed.
                prev = state.get(e["id"], {})
                record = {**prev, **{k: v for k, v in record.items() if k != "fetched_at"},
                          "commit": record.get("commit") or prev.get("commit"), "status": "stale"}
            state[e["id"]] = record
            line = f"{e['id']}: {record['status']}"
            if record.get("commit"):
                line += f" at {record['commit'][:7]}"
            if record.get("reason"):
                line += f" ({record['reason']})"
            print(line)
        write_state(repo, state)
        return 0

    if args.cmd == "find":
        hits, notes = find(repo, args.text, args.only, args.path_glob, args.regex, args.max, now)
        if args.json:
            print(json.dumps({"hits": hits, "notes": notes}, indent=2, sort_keys=True))
            return 0
        for h in hits:
            print(f"{h['citation']}:{h['line']}  {h['text']}")
        for n in notes:
            print(f"note: {n}")
        if not hits:
            print("no hits")
        return 0

    if args.cmd == "check":
        problems = check(repo)
        for p in problems:
            print(p)
        print(f"{len(entries(repo))} related repo(s); " + (f"{len(problems)} problem(s)" if problems else "no problems"))
        return 1 if problems else 0

    path = repo / CONTEXT_FILE
    if not path.exists():
        print(f"no {CONTEXT_FILE}; run /wire:new or /wire:adopt first", file=sys.stderr)
        return 2
    before = path.read_text(encoding="utf-8")
    if args.cmd == "add":
        entry = {"id": args.id, "github_url": args.github_url, "default_branch": args.branch, "role": args.role,
                 "paths": [p.strip() for p in args.paths.split(",") if p.strip()],
                 "description": args.description.replace('"', "'"), "lookup": args.lookup}
        if not ID_RE.match(args.id) or args.id == CLIENT_REPO_ID:
            print(f"id {args.id!r}: use lower case letters, digits, - and _ (not {CLIENT_REPO_ID})", file=sys.stderr)
            return 2
        if has_credentials(args.github_url):
            print("the URL holds a user or token; give the plain https URL (git uses your own access)", file=sys.stderr)
            return 2
        existing = entries(repo)
        if any(e["id"] == args.id for e in existing):
            print(f"id {args.id} is already listed", file=sys.stderr)
            return 2
        if any(normalise_url(e.get("github_url")) == normalise_url(args.github_url) for e in existing):
            print(f"{args.github_url} is already listed", file=sys.stderr)
            return 2
        after = add_entry(before, entry)
    else:
        if args.id == CLIENT_REPO_ID:
            print(f"{CLIENT_REPO_ID} comes from client_repo in context.md; edit that block by hand", file=sys.stderr)
            return 2
        try:
            after = remove_entry(before, args.id)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    print(unified(before, after), end="")
    if not args.yes:
        print("proposal only; nothing written (run again with --yes to write)")
        return 0
    path.write_text(after, encoding="utf-8")
    note = " Any local copy is left where it is." if args.cmd == "remove" else ""
    print(f"changed: {CONTEXT_FILE} (commit it to share).{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

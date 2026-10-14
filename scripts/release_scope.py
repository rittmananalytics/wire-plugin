#!/usr/bin/env python3
"""Which release a branch is working on (wire#301, specs/status.md
"Persona: delivery-manager", Scope). Plain script, no AI call; read-only git.

  release_scope.py [--repo <engagement repo>] [--json]

The first two rules are the branch step of active-release resolution
(specs/start.md Step B1, wire/TEMPLATES/wire-session-check.sh), so both give
the same answer for a branch that names its release. The rest are for the
delivery manager's view: a ticket branch is traced to the release branch it
was cut from, and the default branch asks rather than guessing from recent
activity.

Rules, in order:
  1. claimed-branch    the branch recorded in a release's claim (status.md
                       agents: ... branch:): that release.
  2. branch-names-release
                       the release folder appears in the branch name
                       (release/<release>, <release>/<artifact>, feat/<release>-x):
                       that release; more than one: ask between them.
  3. only-release      the engagement has one release: that release.
  4. default-branch    the default branch (main, master, or a status.md
                       client_repo_branch): ask, listing the releases.
  5. parent-release    any other branch: the release branch it was cut from,
                       the one with the fewest of this branch's commits
                       missing. Ask on a tie, when the default branch is as
                       near (the branch was cut from it), or with no release
                       branches.

Prints the release folder, or "ask:" and the releases to choose from.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def decide(branch: str, releases: list[str], default_branches: list[str], ahead: dict[str, int],
           default_ahead: int | None = None, claimed: dict[str, str] | None = None) -> dict:
    """The rule's decision. `ahead` maps a release to the number of commits on
    this branch that its release branch lacks (only releases that have a
    release branch); `default_ahead` the same count against the default
    branch; `claimed` maps a release to the branch its claim records.
    Returns {release, rule} or {ask: [...], rule}."""
    releases = sorted(releases)
    for release, claimed_branch in sorted((claimed or {}).items()):
        if claimed_branch and claimed_branch == branch and release in releases:
            return {"release": release, "rule": "claimed-branch"}
    named = [r for r in releases if r in branch]
    if len(named) == 1:
        return {"release": named[0], "rule": "branch-names-release"}
    if len(named) > 1:
        return {"ask": named, "rule": "branch-names-several"}
    if len(releases) == 1:
        return {"release": releases[0], "rule": "only-release"}
    if branch in default_branches:
        return {"ask": releases, "rule": "default-branch"}
    candidates = {r: n for r, n in ahead.items() if r in releases}
    if candidates:
        best = min(candidates.values())
        if default_ahead is not None and default_ahead <= best:
            return {"ask": releases, "rule": "cut-from-default-branch"}
        nearest = sorted(r for r, n in candidates.items() if n == best)
        if len(nearest) == 1:
            return {"release": nearest[0], "rule": "parent-release"}
        return {"ask": nearest, "rule": "parent-release-tie"}
    return {"ask": releases, "rule": "no-release-branch"}


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def collect(repo: Path) -> dict:
    """The inputs to decide() from the engagement repository."""
    releases_dir = repo / ".wire" / "releases"
    releases = sorted(p.parent.name for p in releases_dir.glob("*/status.md") if not p.parent.name.startswith("_"))
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    claimed = {}
    for status in releases_dir.glob("*/status.md"):
        m = re.search(r"^    branch:\s*['\"]?([^'\"\s#]+)", status.read_text(encoding="utf-8", errors="replace"), re.M)
        if m and m.group(1) not in ("null", "~"):
            claimed[status.parent.name] = m.group(1)
    defaults = {"main", "master"}
    origin_head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if origin_head:
        defaults.add(origin_head.split("/", 1)[-1])
    for status in releases_dir.glob("*/status.md"):
        m = re.search(r"^client_repo_branch:\s*['\"]?([^'\"\s#]+)", status.read_text(encoding="utf-8", errors="replace"), re.M)
        if m and m.group(1) not in ("null", "~"):
            defaults.add(m.group(1))
    default_ahead = None
    for ref in sorted(defaults):
        count = git(repo, "rev-list", "--count", f"{ref}..HEAD") if git(repo, "rev-parse", "--verify", "--quiet", ref) else ""
        if count.isdigit():
            default_ahead = int(count) if default_ahead is None else min(default_ahead, int(count))
    ahead = {}
    for release in releases:
        for ref in (f"release/{release}", f"origin/release/{release}"):
            if git(repo, "rev-parse", "--verify", "--quiet", ref):
                count = git(repo, "rev-list", "--count", f"{ref}..HEAD")
                if count.isdigit():
                    ahead[release] = int(count)
                break
    return {"branch": branch, "releases": releases, "default_branches": sorted(defaults), "ahead": ahead, "default_ahead": default_ahead, "claimed": claimed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    inputs = collect(Path(args.repo))
    if not inputs["releases"]:
        print("no releases found under .wire/releases/", file=sys.stderr)
        return 1
    out = decide(inputs["branch"], inputs["releases"], inputs["default_branches"], inputs["ahead"], inputs["default_ahead"], inputs["claimed"])
    if args.json:
        print(json.dumps({**out, "branch": inputs["branch"]}))
    elif "release" in out:
        print(out["release"])
    else:
        print("ask: " + ", ".join(out["ask"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

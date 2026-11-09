"""`wire update` and `wire uninstall` (ROADMAP.md phase 7).

- update: finds the newest Wire CLI release on rittmananalytics/wire-plugin
  (pre-releases included, since CLI releases are published as pre-releases), and runs that release's own
  install-wire.sh with WIRE_VERSION set. `--check` only reports. A Homebrew
  install is left to `brew upgrade wire`.
- uninstall: removes what install-wire.sh wrote (the launcher, the installed
  versions, ~/.wire/current, ~/.wire/venv). Keys (~/.wire/secrets.env), the
  agent's home (~/.wire/agent: sessions, MCP sign-ins) and the telemetry id
  stay unless `--all`. Nothing is removed without `--yes`; without it the
  plan is printed. A Homebrew install is left to `brew uninstall wire`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REPO = "rittmananalytics/wire-plugin"
KEEP_WITHOUT_ALL = ("secrets.env", "agent", "telemetry_id", "cli_history", "repos")


def version_key(v: str) -> tuple:
    """Semantic version order with pre-releases before their release:
    5.0.0-alpha.1 < 5.0.0-alpha.2 < 5.0.0-beta.1 < 5.0.0."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?", v or "")
    if not m:
        return (-1,)
    core = tuple(int(x) for x in m.groups()[:3])
    pre = m.group(4)
    if not pre:
        return core + ((1,),)
    parts = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split("."))
    return core + ((0,) + parts,)


def newest(releases: list, current: str) -> str | None:
    """The newest release tag that ships the CLI and is newer than `current`."""
    best = None
    for r in releases or []:
        tag = str(r.get("tag_name") or "")
        assets = {a.get("name") for a in r.get("assets") or []}
        v = tag.lstrip("v")
        if f"wire-cli-{v}.tar.gz" not in assets or r.get("draft"):
            continue
        if version_key(v) > version_key(current) and (best is None or version_key(v) > version_key(best)):
            best = v
    return best


def install_kind(here: Path | None = None) -> str:
    here = (here or Path(__file__)).resolve()
    s = str(here)
    if "/Cellar/" in s or ("/homebrew/" in s.lower() and "/libexec/" in s):
        return "homebrew"
    if "/.wire/versions/" in s:
        return "installer"
    if "/.claude/plugins/" in s:
        return "plugin"  # the Wire CLI inside the Claude Code plugin (4.6.4)
    return "checkout"


def fetch_releases() -> list:
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases?per_page=30",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "wire-cli"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update(current: str, check_only: bool, out=print, env: dict | None = None, releases: list | None = None,
           kind: str | None = None, run=subprocess.run) -> int:
    kind = kind or install_kind()
    if kind == "homebrew":
        out("This Wire CLI was installed with Homebrew: `brew update && brew upgrade wire`.")
        return 0
    if kind == "plugin":
        out("This Wire CLI ships in the Wire plugin for Claude Code: /plugin update wire@rittman-analytics, then /reload-plugins.")
        return 0
    if kind == "checkout":
        out("This Wire CLI runs from a source checkout: update it with git.")
        return 0
    try:
        releases = releases if releases is not None else fetch_releases()
    except Exception as exc:  # noqa: BLE001 - no network is a plain message
        out(f"Could not read the releases of {REPO}: {exc}")
        return 1
    target = newest(releases, current)
    if not target:
        out(f"Wire CLI {current} is the newest release.")
        return 0
    out(f"Wire CLI {target} is available (installed: {current}).")
    if check_only:
        return 0
    url = f"https://github.com/{REPO}/releases/download/v{target}/install-wire.sh"
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "install-wire.sh"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                script.write_bytes(resp.read())
        except Exception as exc:  # noqa: BLE001
            out(f"Could not download {url}: {exc}")
            return 1
        run_env = dict(os.environ if env is None else env)
        run_env["WIRE_VERSION"] = target
        return run(["sh", str(script)], env=run_env).returncode


def uninstall_plan(home: Path, bin_dir: Path, everything: bool) -> list:
    """(path, what) pairs that would be removed."""
    plan = []
    launcher = bin_dir / "wire"
    if launcher.is_file():
        try:
            text = launcher.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if "Installed by install-wire.sh" in text or str(home / "current") in text:
            plan.append((launcher, "the wire launcher"))
    wire_home = home
    if everything:
        if wire_home.exists():
            plan.append((wire_home, "everything under ~/.wire, keys and the agent's home included"))
        return plan
    for name, what in (("versions", "the installed versions"), ("current", "the link to the current version"),
                       ("venv", "the private Python environment"), ("bridge", "the bridge's config and logs"),
                       ("bridge-venv", "the bridge's Python environment")):
        p = wire_home / name
        if p.exists() or p.is_symlink():
            plan.append((p, what))
    return plan


def uninstall(yes: bool, everything: bool, out=print, env: dict | None = None, kind: str | None = None) -> int:
    kind = kind or install_kind()
    if kind == "homebrew":
        out("This Wire CLI was installed with Homebrew: `brew uninstall wire` (your ~/.wire keys and agent home stay).")
        return 0
    env = dict(os.environ if env is None else env)
    home = Path(env.get("WIRE_HOME") or Path(env.get("HOME") or Path.home()) / ".wire")
    bin_dir = Path(env.get("WIRE_BIN") or Path(env.get("HOME") or Path.home()) / ".local" / "bin")
    plan = uninstall_plan(home, bin_dir, everything)
    if not plan:
        out("Nothing of the Wire CLI's install was found.")
        return 0
    out("Removes:" if yes else "Would remove (run again with --yes):")
    for p, what in plan:
        out(f"  {p}  ({what})")
    if not everything:
        kept = [n for n in KEEP_WITHOUT_ALL if (home / n).exists()]
        if kept:
            out("Keeps: " + ", ".join(f"~/.wire/{n}" for n in kept) + " (--all removes them too)")
    if not yes:
        return 0
    for p, _what in plan:
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
    out("Uninstalled.")
    return 0

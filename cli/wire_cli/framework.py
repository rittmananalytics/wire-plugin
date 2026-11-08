"""Where the framework is, and what it knows.

The framework root is the folder that holds specs/, release-types/, scripts/
and studio/: `wire/` in a checkout (this file is wire/cli/wire_cli/framework.py)
and the plugin root in a built Codex plugin (<plugin>/cli/wire_cli/framework.py).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
DEFAULT_ROOT = HERE.parents[2]


def _is_root(root: Path) -> bool:
    return all((root / needed).is_dir() for needed in ("specs", "release-types", "scripts"))


def framework_root(override: str | None = None) -> Path:
    """The framework: the override, else the folder this CLI sits in, else the
    framework the standalone agent carries (`wire-agent framework path`), so a
    CLI unpacked on its own still finds the specs."""
    root = Path(override).resolve() if override else DEFAULT_ROOT
    if _is_root(root):
        return root
    if not override:
        carried = _carried()
        if carried is not None and _is_root(carried):
            return carried
    missing = next(n for n in ("specs", "release-types", "scripts") if not (root / n).is_dir())
    raise FileNotFoundError(f"{root} has no {missing}/; not a Wire framework root")


def _carried() -> Path | None:
    import os
    from .harness.codex import find_codex, is_forked_agent
    exe = find_codex()
    if not is_forked_agent(exe):
        return None
    from .agent_home import carried_framework, home
    env = dict(os.environ)
    env.setdefault("CODEX_HOME", str(home(env)))
    return carried_framework(exe, env)


def load_studio(root: Path):
    """The Studio resolver, the executable form of specs/utils/runnable_set.md.
    Returns (Framework instance, split_front_matter, read_rulings, resolve)."""
    studio = root / "studio"
    if not studio.is_dir():
        raise FileNotFoundError(f"{root} has no studio/; the resolver is not shipped here")
    if str(studio) not in sys.path:
        sys.path.insert(0, str(studio))
    from wire_studio.framework import Framework  # noqa: E402
    from wire_studio.record import read_rulings, split_front_matter  # noqa: E402
    from wire_studio.runnable import resolve  # noqa: E402
    return Framework(root), split_front_matter, read_rulings, resolve


def load_script(root: Path, name: str):
    """A script under <root>/scripts as a module (status_file, wire_gate, ...)."""
    import importlib.util
    path = root / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"wire_scripts_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"wire_scripts_{name}"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------- catalogue

def _catalogue_from_json(path: Path) -> dict:
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {e["command"]: e for e in entries}


def _catalogue_from_build_script(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^COMMANDS=\(\n(.*?)^\)", text, re.S | re.M)
    if not m:
        return {}
    out = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line.startswith('"'):
            continue
        parts = line.strip('"').split("|")
        if len(parts) < 3:
            continue
        name = parts[0].replace("/", "-").replace(":", "-")
        out[name] = {"command": name, "spec": parts[1], "description": parts[2],
                     "arguments": parts[3] if len(parts) > 3 else "",
                     "telemetry": (parts[4].strip().lower() == "yes") if len(parts) > 4 else False}
    return out


def catalogue(root: Path) -> dict:
    """command name -> entry (spec path, description, arguments). The built
    Codex plugin's references/commands.json, or the Claude Code plugin's
    cli/commands.json, when it is there, else the build
    script's COMMANDS array (a checkout before a build)."""
    for rel in ("skills/wire/references/commands.json", "cli/commands.json",
                "dist/codex-plugin/skills/wire/references/commands.json"):
        p = root / rel
        if p.is_file():
            return _catalogue_from_json(p)
    script = root / "scripts" / "build-packages.sh"
    if script.is_file():
        return _catalogue_from_build_script(script)
    return {}


def normalise_command(name: str) -> str:
    return name.replace("/wire:", "").replace("wire:", "").replace("/", "-").replace(":", "-").strip()


def spec_path(root: Path, entry: dict) -> Path:
    rel = entry["spec"]
    for candidate in (root / "specs" / f"{rel}.md", root / "generated" / f"{rel}.md"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"spec {rel}.md is not under {root}/specs")


# ---------------------------------------------------------------- spec front matter

def front_matter(text: str) -> dict:
    """A small reader for a spec's front matter: scalars, lists of scalars and
    lists of flat mappings (`produces:`). Enough for workload, command,
    action_type and produces types; not a YAML parser."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    data: dict = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if indent == 0 and ":" in s:
            key, _, value = s.partition(":")
            key = key.strip()
            value = value.split("  #", 1)[0].strip()
            data[key] = value.strip("\"'") if value else []
        elif key is not None and s.startswith("- "):
            item = s[2:].strip()
            if isinstance(data.get(key), list):
                if ":" in item and not item.startswith(("'", '"')):
                    k, _, v = item.partition(":")
                    data[key].append({k.strip(): v.strip().strip("\"'")})
                else:
                    data[key].append(item.strip("\"'"))
        elif key is not None and indent >= 2 and ":" in s and isinstance(data.get(key), list) and data[key] and isinstance(data[key][-1], dict):
            k, _, v = s.partition(":")
            data[key][-1][k.strip()] = v.strip().strip("\"'")
    return data


def workload_of(text: str) -> str:
    fm = front_matter(text)
    w = fm.get("workload")
    return w if isinstance(w, str) else ""


def is_client_facing(text: str) -> bool:
    """specs/delegate.md, "Client-facing deliverable": a generate with
    action_type artifact, any review, or a produces entry of type document,
    deck or pr. A validate whose produces are all reports counts as
    client-facing until the spec says otherwise (the floor holds)."""
    fm = front_matter(text)
    command = str(fm.get("command", ""))
    if command == "review":
        return True
    if command == "generate" and str(fm.get("action_type", "")) == "artifact":
        return True
    produces = fm.get("produces") or []
    types = [p.get("type", "") for p in produces if isinstance(p, dict)]
    if any(t in ("document", "deck", "pr") for t in types):
        return True
    if command == "validate" and types and all(t == "report" for t in types):
        return True
    return False

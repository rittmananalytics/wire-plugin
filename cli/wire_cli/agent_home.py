"""The standalone agent's own home (ROADMAP.md phase 3: "its own identity").

`wire-agent` runs with CODEX_HOME=~/.wire/agent (WIRE_AGENT_HOME to change it),
never ~/.codex, so a person's own Codex (its sign-in, its settings, its trusted
folders) is never read or changed by a Wire run. Found the hard way: Codex
logs a stored ChatGPT session out when it meets a setting it disagrees with.

Wire keeps that home's config.toml itself, with only what a Wire run needs:

- the engagement repository as a trusted project, so Codex reads its
  `.codex/` (agents, settings) as it does for a folder a person trusted;
- Wire's own two hooks trusted, and only while the repository's
  `.codex/hooks.json` is byte-identical to the one Wire ships. Codex trusts a
  hook by a SHA-256 of its normalised definition (codex-rs config
  fingerprint.rs, hooks discovery.rs); `hook_hash` below reproduces it and the
  tests pin it to the values Codex wrote. A changed hooks.json is never
  trusted here: the person reviews it in Codex with /hooks.

Everything else in the file is left as Codex or the person wrote it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

MANAGED_BEGIN = "# >>> wire: managed by the Wire CLI (agent_home.py); edits inside are replaced"
MANAGED_END = "# <<< wire"
EVENT_KEYS = {"PreToolUse": "pre_tool_use", "PostToolUse": "post_tool_use"}


def home(env: dict) -> Path:
    named = (env.get("WIRE_AGENT_HOME") or "").strip()
    return Path(named).expanduser() if named else Path(env.get("HOME") or Path.home()) / ".wire" / "agent"


def hook_hash(event_key: str, handler: dict, matcher: str | None = None) -> str:
    """Codex's trust hash for one hook handler: SHA-256 of the compact,
    key-sorted JSON of {event_name, matcher?, hooks: [handler with defaults]}."""
    h = dict(handler)
    if h.get("type", "command") == "command":
        h.setdefault("async", False)
    ident = {"event_name": event_key, "hooks": [{k: v for k, v in h.items() if v is not None}]}
    if matcher is not None:
        ident["matcher"] = matcher
    text = json.dumps(ident, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def hook_trust_entries(hooks_json: Path) -> list:
    """(state key, trusted hash) for every handler in a hooks.json."""
    data = json.loads(hooks_json.read_text(encoding="utf-8"))
    out = []
    for event, groups in (data.get("hooks") or {}).items():
        key = EVENT_KEYS.get(event)
        if not key:
            continue
        for gi, group in enumerate(groups or []):
            for hi, handler in enumerate(group.get("hooks") or []):
                out.append((f"{hooks_json}:{key}:{gi}:{hi}", hook_hash(key, handler, group.get("matcher"))))
    return out


def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def managed_block(repo: Path, trusted_hooks: list) -> str:
    lines = [MANAGED_BEGIN, f"[projects.{_toml_str(str(repo))}]", 'trust_level = "trusted"', ""]
    for key, digest in trusted_hooks:
        lines += [f"[hooks.state.{_toml_str(key)}]", f"trusted_hash = {_toml_str(digest)}", ""]
    lines.append(MANAGED_END)
    return "\n".join(lines) + "\n"


def merge(existing: str, repo: Path, block: str) -> str:
    """The config with this repository's managed block replaced (one block per repository)."""
    marker = f"[projects.{_toml_str(str(repo))}]"
    pattern = re.compile(re.escape(MANAGED_BEGIN) + r"\n" + re.escape(marker) + r"\n.*?" + re.escape(MANAGED_END) + r"\n?", re.S)
    if pattern.search(existing or ""):
        return pattern.sub(lambda _m: block, existing, count=1)
    sep = "" if not existing or existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    return (existing or "") + sep + block


BLOCK_RE = re.compile(re.escape(MANAGED_BEGIN) + r'\n\[projects\."((?:[^"\\]|\\.)*)"\]\n.*?' + re.escape(MANAGED_END) + r"\n?", re.S)


def prune(existing: str) -> str:
    """Drop managed blocks for folders that no longer exist (finished lane worktrees)."""
    return BLOCK_RE.sub(lambda m: m.group(0) if Path(m.group(1).replace('\\"', '"').replace("\\\\", "\\")).exists() else "",
                        existing or "")


def shipped_hooks(framework_root: Path) -> Path | None:
    for candidate in (framework_root / "install" / ".codex" / "hooks.json",
                      framework_root / "packaging" / "codex-plugin" / "install" / ".codex" / "hooks.json",
                      framework_root / "dist" / "codex-plugin" / "install" / ".codex" / "hooks.json"):
        if candidate.is_file():
            return candidate
    return None


BUNDLED = "wire-bundled"
REGISTERED = "registered.txt"
_carried_cache: dict = {}


def carried_framework(executable: str, env: dict) -> Path | None:
    """The framework this wire-agent carries, unpacked in its home
    (`wire-agent framework path`), or None for a build that carries none."""
    import subprocess
    key = (executable, env.get("CODEX_HOME"))
    if key in _carried_cache:
        return _carried_cache[key]
    found = None
    try:
        # The agent refuses a CODEX_HOME that does not exist; on a new install
        # nothing has created it yet (wire doctor, framework_root's fallback).
        if env.get("CODEX_HOME"):
            Path(env["CODEX_HOME"]).mkdir(parents=True, exist_ok=True)
        proc = subprocess.run([executable, "framework", "path"], capture_output=True, text=True, env=env, timeout=120)
        if proc.returncode == 0 and proc.stdout.strip():
            p = Path(proc.stdout.strip().split("\n")[-1])
            found = p if (p / "specs").is_dir() else None
    except (OSError, subprocess.SubprocessError):
        found = None
    _carried_cache[key] = found
    return found


def register_carried(executable: str, env: dict, framework: Path) -> list:
    """The carried framework as the `wire` plugin in the agent's home: a local
    marketplace, then the plugin installed from it (Codex's own commands, so the
    plugin cache is laid out as Codex expects). Done once per framework folder;
    the folder is recorded in <home>/framework/registered.txt. Returns notes."""
    import subprocess
    h = Path(env["CODEX_HOME"])
    record = h / "framework" / REGISTERED
    if record.is_file() and record.read_text(encoding="utf-8").strip() == str(framework):
        return []
    notes = []
    steps = [[executable, "plugin", "marketplace", "remove", BUNDLED],
             [executable, "plugin", "marketplace", "add", str(framework)],
             [executable, "plugin", "add", f"wire@{BUNDLED}"]]
    for i, argv in enumerate(steps):
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            return [f"could not register the Wire framework wire-agent carries: {exc}"]
        if proc.returncode != 0 and i > 0:  # removing a marketplace that is not there is fine
            tail = (proc.stderr or proc.stdout).strip().split("\n")[-1:]
            return [f"could not register the Wire framework wire-agent carries ({' '.join(argv[1:4])}): {' '.join(tail)}"]
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(str(framework) + "\n", encoding="utf-8")
    return notes


def uses_repo_copy(repo: Path) -> bool:
    """The repository carries its own copy of the plugin (an earlier `wire codex-install`)."""
    return (repo / ".wire" / "codex-plugin").is_dir() or (repo / ".agents" / "plugins" / "marketplace.json").is_file()


def prepare(repo: Path, env: dict, framework_root: Path | None = None, executable: str | None = None) -> tuple[dict, list]:
    """CODEX_HOME for a wire-agent run, the home's config brought up to date for
    this repository, and notes. Returns (env, notes). With the agent's path, the
    framework it carries is registered as its `wire` plugin."""
    env = dict(env)
    if env.get("CODEX_HOME"):
        return env, []  # the person chose a home; leave it alone
    h = home(env)
    h.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(h, 0o700)
    except OSError:
        pass
    repo = repo.resolve()
    notes: list = []
    trusted: list = []
    repo_hooks = repo / ".codex" / "hooks.json"
    if repo_hooks.is_file():
        ours = shipped_hooks(framework_root) if framework_root else None
        if ours and ours.read_bytes() == repo_hooks.read_bytes():
            trusted = hook_trust_entries(repo_hooks)
        else:
            notes.append(f"{repo_hooks} differs from the hooks Wire ships; review it in wire-agent with /hooks "
                         f"(CODEX_HOME={h}) before lanes rely on it")
    cfg = h / "config.toml"
    existing = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
    new = merge(prune(existing), repo, managed_block(repo, trusted))
    if new != existing:
        cfg.write_text(new, encoding="utf-8")
    env["CODEX_HOME"] = str(h)
    if executable:
        # Registered whatever the repository holds: a copy from an earlier
        # `wire codex-install --copy` is never loaded in a Wire CLI run (Codex
        # installs a repository's marketplace plugin only through /plugins, seen
        # live on 0.166.0), so the carried one is the only `wire` skill a run sees.
        carried = carried_framework(executable, env)
        if carried:
            notes += register_carried(executable, env, carried)
    return env, notes

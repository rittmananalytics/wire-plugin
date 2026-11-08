"""`wire doctor`: what this machine can run. Names keys, never values."""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .secrets import present, secret_files, too_open


def _version(cmd: list) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip().split("\n")[0] or "present"
    except (OSError, subprocess.SubprocessError):
        return "present"


def lmstudio_models(url: str = "http://localhost:1234/v1/models") -> list:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310 - localhost only
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("id", "?") for m in data.get("data", [])]
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return []


def doctor(repo: Path, env: dict, args, out=print) -> int:
    rows = []
    from .harness.codex import find_codex
    codex = find_codex()
    codex_path = codex if Path(codex).is_file() else shutil.which(codex)
    rows.append(("codex", f"{_version([codex_path, '--version'])} ({codex_path})" if codex_path else "not found (npm install -g @openai/codex, or the standalone install's wire-agent)"))
    claude = shutil.which("claude")
    rows.append(("claude", _version([claude, "--version"]) if claude else "not on PATH"))
    try:
        import yaml  # noqa: F401
        rows.append(("pyyaml", "present"))
    except ImportError:
        rows.append(("pyyaml", "missing (pip install pyyaml); the resolver needs it"))
    if codex_path:
        from .harness.codex import is_forked_agent as _forked
        if _forked(codex_path):
            from .agent_home import carried_framework, home
            fw = carried_framework(codex_path, dict(env, CODEX_HOME=str(home(env))))
            rows.append(("framework in wire-agent", str(fw) if fw else "none (an older build; the plugin is copied into each repository)"))
    keys = present(env)
    rows.append(("ANTHROPIC_API_KEY", "set" if keys["ANTHROPIC_API_KEY"] else "not set (the claude harness needs it; a subscription cannot be used here)"))
    from .harness.codex import is_forked_agent, chatgpt_login_allowed
    if keys["OPENAI_API_KEY"] or keys["CODEX_API_KEY"]:
        rows.append(("OPENAI_API_KEY", "set"))
    elif codex_path and is_forked_agent(codex_path) and not chatgpt_login_allowed(env):
        rows.append(("OPENAI_API_KEY", "not set (wire-agent signs in to OpenAI with an API key only; "
                                       "ChatGPT sign-in needs OpenAI's own codex: WIRE_CODEX_BIN=$(which codex))"))
    else:
        rows.append(("OPENAI_API_KEY", "not set (codex: `codex login` for a ChatGPT plan, or the key)"))
    for p in secret_files(repo):
        if p.is_file():
            rows.append((str(p), "readable by others, skipped; chmod 600" if too_open(p) else "loaded"))
    from .mcp import load_selection, SELECTION_FILE
    selected = load_selection(repo)
    rows.append(("MCP servers (this engagement)", ", ".join(sorted(selected)) if selected
                 else f"none selected ({SELECTION_FILE}; wire mcp list, wire mcp add <server>)"))
    models = lmstudio_models()
    rows.append(("LM Studio (localhost:1234)", ", ".join(models) if models else "not reachable (`lms server start --port 1234`)"))
    hooks = repo / ".codex" / "hooks" / "wire_hooks.py"
    rows.append((".codex/hooks (this repo)", "installed; trust once with /hooks in Codex" if hooks.is_file() else "not installed (`wire codex-install`)"))
    rows.append((".wire/ (this repo)", "present" if (repo / ".wire").is_dir() else "absent"))
    if getattr(args, "json", False):
        out(json.dumps(dict(rows), indent=2))
    else:
        width = max(len(k) for k, _ in rows)
        for k, v in rows:
            out(f"  {k:<{width}}  {v}")
    return 0

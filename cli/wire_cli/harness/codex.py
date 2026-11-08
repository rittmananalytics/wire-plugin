"""OpenAI Codex as a harness: `codex exec --json`.

What the live runs on Codex 0.166.0 showed (wire#408): the prompt goes in on
stdin (`codex exec -`), `-c model_provider=<id> -m <model>` selects the
provider per run, `-s workspace-write` allows edits, `--output-schema` shapes
the final message, `turn.completed` carries the token usage, and a call a hook
blocked appears only on stderr as `Command blocked by PreToolUse hook: ...`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import Harness, RunRequest, RunResult, Timer, Usage, blocked_from_stderr


def find_codex(env: dict | None = None) -> str:
    """The Codex binary to run: WIRE_CODEX_BIN, then the Wire-forked
    `wire-agent` beside this CLI (the standalone install), then `codex` on the PATH."""
    from pathlib import Path
    import os
    named = (env if env is not None else os.environ).get("WIRE_CODEX_BIN")
    if named and Path(named).is_file():
        return named
    here = Path(__file__).resolve()
    for root in (here.parents[3], here.parents[2]):
        candidate = root / "bin" / "wire-agent"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("codex", path=(env or {}).get("PATH")) or "codex"  # the run's own PATH when given


def is_forked_agent(executable: str) -> bool:
    """True for the Wire-forked Codex (`wire-agent`), false for OpenAI's own `codex`."""
    return Path(executable).name.startswith("wire-agent")


def chatgpt_login_allowed(env: dict) -> bool:
    return str(env.get("WIRE_ALLOW_CHATGPT_LOGIN", "")).lower() in ("1", "true", "yes")


NO_KEY_FOR_AGENT = ("wire-agent signs in to OpenAI with an API key only, and none is set. Put OPENAI_API_KEY "
                    "in ~/.wire/secrets.env, or run OpenAI's own Codex for ChatGPT sign-in: "
                    "WIRE_CODEX_BIN=$(which codex).")


ANTHROPIC_CONTEXT_WINDOW = 200_000


def anthropic_overrides() -> list:
    """The forked agent's native Anthropic provider (ROADMAP.md phase 3): the
    Messages API, no proxy. The key goes in the x-api-key header from
    ANTHROPIC_API_KEY. Codex has no metadata for Claude models, so the context
    window is stated."""
    return [
        "-c", 'model_providers.anthropic.name="Anthropic"',
        "-c", 'model_providers.anthropic.base_url="https://api.anthropic.com/v1"',
        "-c", 'model_providers.anthropic.wire_api="anthropic"',
        "-c", 'model_providers.anthropic.env_http_headers={"x-api-key"="ANTHROPIC_API_KEY"}',
        "-c", f"model_context_window={ANTHROPIC_CONTEXT_WINDOW}",
    ]


NEEDS_AGENT_FOR_ANTHROPIC = ("provider anthropic needs the standalone agent (wire-agent), which speaks the Anthropic "
                             "Messages API; OpenAI's codex does not. Use wire-agent, or `wire bridge start` and "
                             "--provider wirebridge with OpenAI's codex.")
NO_ANTHROPIC_KEY = "provider anthropic needs ANTHROPIC_API_KEY in ~/.wire/secrets.env."


def signin_env(executable: str, req: RunRequest) -> tuple[dict, str | None]:
    """The sign-in rule (ROADMAP.md phase 0). The forked agent reaches OpenAI with
    an API key only: "Sign in with ChatGPT" is for OpenAI's own Codex until OpenAI
    confirms in writing that a modified client may use it (WIRE_ALLOW_CHATGPT_LOGIN=1
    lifts the rule then). The key goes in as CODEX_API_KEY, which `codex exec`
    prefers to the stored login, so ~/.codex/auth.json is never read or changed.
    (Codex's own `forced_login_method = "api"` was tried first: it logs a stored
    ChatGPT session out, which is not ours to do.) Returns the run's environment
    and, when the rule cannot be met, the reason the run is refused."""
    env = dict(req.env or {})
    if req.provider == "anthropic":
        if not is_forked_agent(executable):
            return env, NEEDS_AGENT_FOR_ANTHROPIC
        if not env.get("ANTHROPIC_API_KEY"):
            return env, NO_ANTHROPIC_KEY
        return env, None
    if not is_forked_agent(executable) or req.provider not in (None, "", "openai") or chatgpt_login_allowed(env):
        return env, None
    key = env.get("CODEX_API_KEY") or env.get("OPENAI_API_KEY")
    if not key:
        return env, NO_KEY_FOR_AGENT
    env["CODEX_API_KEY"] = key
    return env, None


def _servers(req: RunRequest) -> dict:
    """The run's MCP servers, with Wire's tools server when the run asks for it."""
    from ..mcp import with_tools
    return with_tools(req.mcp, req.cwd, req.env) if req.wire_tools else dict(req.mcp or {})


def _mcp_note(req: RunRequest) -> str:
    from ..mcp import prompt_note
    return prompt_note(_servers(req))


LANE_PROFILE = "wire-lane"


def lane_profile_overrides(paths: list) -> list:
    """A Codex permissions profile for one lane (ROADMAP.md phase 5): the whole
    disk readable, temp folders and the lane's paths writable, nothing else.
    Enforced by the operating system's sandbox (seatbelt on macOS, landlock on
    Linux), so cp, mv, sed -i and cd are covered, which the hook cannot see.
    Seen live on wire-agent 0.166.0: a write inside a listed path succeeded,
    one at the repository root failed with "operation not permitted"."""
    entries = {":root": "read", ":tmpdir": "write", ":slash_tmp": "write"}
    for p in paths:
        entries[p] = "write"
    table = ",".join(f"{json.dumps(k)}={json.dumps(v)}" for k, v in entries.items())
    return ["-c", f'default_permissions="{LANE_PROFILE}"', "-c", f"permissions.{LANE_PROFILE}.filesystem={{{table}}}"]


def use_profile(req: RunRequest) -> bool:
    return bool(req.write_paths) and req.sandbox == "workspace-write" and str(
        (req.env or {}).get("WIRE_OS_SANDBOX", "true")).lower() != "false"


def config_overrides(req: RunRequest) -> list:
    """The `-c` overrides a run needs whichever way it is driven (exec or app-server):
    provider definitions, the provider, MCP servers. The lane profile and sandbox
    are added by the caller, since exec and app-server take them differently."""
    argv = []
    if req.provider == "wirebridge":
        from ..bridge import codex_provider_overrides
        argv += codex_provider_overrides()
    if req.provider == "anthropic":
        argv += anthropic_overrides()
    if req.provider:
        argv += ["-c", f"model_provider={req.provider}"]
    servers = _servers(req)
    if servers:
        from ..mcp import codex_overrides
        argv += codex_overrides(servers)
    return argv


def build_argv(req: RunRequest, codex: str = "codex") -> list:
    profile = use_profile(req)
    if req.resume_thread:
        # `codex exec resume` takes no -s or -C (Codex 0.166.0): the sandbox goes
        # in as a config override and the working directory is the process's cwd.
        argv = [codex, "exec", "resume", "--json", "--skip-git-repo-check"]
        argv += lane_profile_overrides(req.write_paths) if profile else ["-c", f'sandbox_mode="{req.sandbox}"']
    elif profile:
        argv = [codex, "exec", "--json", "-C", str(req.cwd), "--skip-git-repo-check"] + lane_profile_overrides(req.write_paths)
    else:
        argv = [codex, "exec", "--json", "-s", req.sandbox, "-C", str(req.cwd), "--skip-git-repo-check"]
    overrides = config_overrides(req)
    mcp_at = next((i for i in range(0, len(overrides), 2) if overrides[i + 1].startswith("mcp_servers.")), len(overrides))
    argv += overrides[:mcp_at]
    if req.model:
        argv += ["-m", req.model]
    if req.output_schema:
        argv += ["--output-schema", str(req.output_schema)]
    argv += overrides[mcp_at:]
    if req.resume_thread:
        argv.append(req.resume_thread)
    argv.append("-")
    return argv


def app_server_argv_overrides(req: RunRequest) -> list:
    """Overrides for `<agent> ... app-server`: the lane profile, then the rest."""
    return (lane_profile_overrides(req.write_paths) if use_profile(req) else []) + config_overrides(req)


OPENAI_BY_KEY = "wire-openai"


def openai_key_overrides() -> list:
    """OpenAI by API key on the app-server path. `codex exec` reads CODEX_API_KEY;
    the stdio app-server does not (Codex 0.166.0 builds its sign-in with that
    switch off), and seen live the forked agent got 401 from OpenAI. A provider
    with `env_key` reads the key from the environment on each request, so the key
    is never written to the agent's home."""
    return [
        "-c", f'model_providers.{OPENAI_BY_KEY}.name="OpenAI"',
        "-c", f'model_providers.{OPENAI_BY_KEY}.base_url="https://api.openai.com/v1"',
        "-c", f'model_providers.{OPENAI_BY_KEY}.wire_api="responses"',
        "-c", f'model_providers.{OPENAI_BY_KEY}.env_key="CODEX_API_KEY"',
        "-c", f"model_provider={OPENAI_BY_KEY}",
    ]


def streaming_wanted(req: RunRequest) -> bool:
    """A person is watching (on_text or ask) and streaming is not switched off (WIRE_STREAM=false)."""
    if req.on_text is None and req.ask is None:
        return False
    return str((req.env or {}).get("WIRE_STREAM", "true")).lower() not in ("0", "false", "no", "off")


def parse_events(lines) -> dict:
    """thread id, last agent message, usage and error from a JSONL stream."""
    out = {"thread_id": None, "final_message": "", "usage": Usage(), "error": None, "events": 0, "warnings": []}
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        out["events"] += 1
        t = e.get("type")
        if t == "thread.started":
            out["thread_id"] = e.get("thread_id")
        elif t == "item.completed":
            item = e.get("item") or {}
            if item.get("type") == "agent_message":
                out["final_message"] = item.get("text", "") or out["final_message"]
            elif item.get("type") == "error":
                out["warnings"].append(str(item.get("message", "")))
        elif t == "turn.completed":
            u = e.get("usage") or {}
            out["usage"] = Usage(
                input_tokens=int(u.get("input_tokens") or 0),
                cached_input_tokens=int(u.get("cached_input_tokens") or 0),
                output_tokens=int(u.get("output_tokens") or 0),
                reasoning_output_tokens=int(u.get("reasoning_output_tokens") or 0),
            )
        elif t == "turn.failed":
            err = e.get("error") or {}
            out["error"] = err.get("message") if isinstance(err, dict) else str(err)
        elif t == "error":
            out["error"] = e.get("message") or out["error"]
    return out


class CodexHarness(Harness):
    name = "codex"

    def __init__(self, executable: str | None = None):
        self.executable = executable or find_codex()

    def run(self, req: RunRequest) -> RunResult:
        argv = build_argv(req, self.executable)
        result = RunResult(harness=self.name, argv=argv)
        events_path = None
        if req.log_dir:
            req.log_dir.mkdir(parents=True, exist_ok=True)
            events_path = req.log_dir / f"{req.label}.codex.jsonl"
        env, refused = signin_env(self.executable, req)
        if refused:
            result.exit_code, result.error = 2, refused
            return result
        if is_forked_agent(self.executable):
            from ..agent_home import prepare
            root = Path(env["WIRE_PLUGIN_ROOT"]) if env.get("WIRE_PLUGIN_ROOT") else None
            env, notes = prepare(Path(req.cwd), env, root, self.executable)
            for note in notes:
                import sys
                sys.stderr.write(f"wire: {note}\n")
        if req.provider == "wirebridge":
            env.setdefault("WIRE_BRIDGE_KEY", "local")
        if streaming_wanted(req):
            from .app_server import AppServerUnavailable, run_turn
            from .. import __version__
            overrides = app_server_argv_overrides(req)
            if (is_forked_agent(self.executable) and req.provider in (None, "", "openai") and env.get("CODEX_API_KEY")
                    and not chatgpt_login_allowed(env)):
                overrides += openai_key_overrides()
            try:
                return run_turn(self.executable, overrides, req, req.prompt + _mcp_note(req), env,
                                use_profile(req), __version__)
            except AppServerUnavailable as exc:
                import sys
                sys.stderr.write(f"wire: no streaming for this run ({exc}); running it with codex exec.\n")
        try:
            with Timer() as t:
                proc = subprocess.run(argv, input=req.prompt + _mcp_note(req), capture_output=True, text=True,
                                      cwd=str(req.cwd), env=env)
        except OSError as exc:
            result.exit_code, result.error = 127, f"could not run codex: {exc}"
            return result
        result.duration_s = t.seconds
        result.exit_code = proc.returncode
        if events_path:
            events_path.write_text(proc.stdout, encoding="utf-8")
            (req.log_dir / f"{req.label}.codex.stderr.txt").write_text(proc.stderr, encoding="utf-8")
            result.events_path = str(events_path)
        parsed = parse_events(proc.stdout.split("\n"))
        result.thread_id = parsed["thread_id"]
        result.final_message = parsed["final_message"]
        result.usage = parsed["usage"]
        result.blocked = blocked_from_stderr(proc.stderr)
        result.stderr_tail = "\n".join([l for l in proc.stderr.split("\n") if l.strip()][-5:])
        if parsed["error"]:
            result.error = parsed["error"]
        if proc.returncode != 0 and not result.error:
            result.error = result.stderr_tail or f"codex exited {proc.returncode}"
        return result

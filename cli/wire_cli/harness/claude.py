"""Claude Code as a harness: `claude -p --output-format stream-json`.

Item 3 of wire#408. Claude runs on its native API here, never through
Codex. The stream's final `result` event carries the result text, the token
usage (input, output, cache read and cache creation) and the cost. Not yet
exercised live; the fake harness covers the CLI's behaviour in tests.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

from . import Harness, RunRequest, RunResult, Timer, Usage, blocked_from_stderr


def _plugin_servers(env: dict | None) -> dict:
    """The Wire plugin's own MCP servers (key -> url), from the framework this CLI runs in."""
    from ..framework import framework_root
    from ..mcp import plugin_servers
    try:
        return plugin_servers(framework_root((env or {}).get("WIRE_PLUGIN_ROOT")))
    except (FileNotFoundError, OSError, ValueError):
        return {}


def _servers(req: RunRequest) -> dict:
    """The run's MCP servers, with Wire's tools server when the run asks for it,
    named as Claude Code should see them: a server the plugin ships is
    plugin:wire:<key>, so the person's /mcp sign-in in Claude Code applies."""
    from ..mcp import claude_names, with_tools
    servers = with_tools(req.mcp, req.cwd, req.env) if req.wire_tools else dict(req.mcp or {})
    return claude_names(servers, _plugin_servers(req.env)) if servers else servers


def _mcp_note(req: RunRequest) -> str:
    from ..mcp import prompt_note
    return prompt_note(_servers(req))


def build_argv(req: RunRequest, claude: str = "claude") -> list:
    argv = [claude, "-p", "--output-format", "stream-json", "--verbose"]
    if req.on_text is not None and str((req.env or {}).get("WIRE_STREAM", "true")).lower() not in ("0", "false", "no", "off"):
        argv.append("--include-partial-messages")  # text deltas as stream_event lines
    if req.resume_thread:
        argv += ["--resume", req.resume_thread]
    if req.model:
        argv += ["--model", req.model]
    if str((req.env or {}).get("WIRE_CLAUDE_USER_SETTINGS", "false")).lower() not in ("1", "true", "yes", "on"):
        # A Wire step runs on the engagement's settings only: not the person's
        # user settings (their plugins, and their claude.ai connectors as MCP
        # servers), and only the MCP servers Wire passes. Measured 4.6.2: 40
        # connector servers and 5 plugins gone, input 59K to 36K tokens and
        # cost down 80% on a one-line question. WIRE_CLAUDE_USER_SETTINGS=true
        # keeps them.
        argv += ["--setting-sources", "project,local", "--strict-mcp-config"]
    servers = _servers(req)
    if servers:
        from ..mcp import claude_mcp_config
        argv += ["--mcp-config", claude_mcp_config(servers)]
    if req.sandbox == "workspace-write":
        # Edits in the working tree, and the read-only shell commands a Wire spec
        # runs (its own scripts, git reads, listing and reading files). Anything
        # else is refused by Claude Code, which a headless run cannot approve.
        # The run's MCP servers are allowed whole (mcp__<server>).
        from ..mcp import tool_prefix
        tools = list(WORKSPACE_TOOLS) + [tool_prefix(k)[:-2] for k in sorted(servers)]
        if req.write_paths:
            # a lane: edits only under its paths (Claude Code's path-scoped permission rules)
            tools = [t for t in tools if t not in ("Edit", "Write", "MultiEdit")]
            for p in req.write_paths:
                for t in ("Edit", "Write", "MultiEdit"):
                    tools.append(f"{t}({p}/**)" if not p.endswith(".md") else f"{t}({p})")
        argv += ["--permission-mode", "acceptEdits", "--allowedTools", " ".join(tools)]
    elif req.sandbox == "danger-full-access":
        argv += ["--dangerously-skip-permissions"]
    return argv


WORKSPACE_TOOLS = (
    "Edit", "Write", "Read", "Glob", "Grep", "MultiEdit",
    "Bash(python3 *)", "Bash(python *)", "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)",
    "Bash(git show*)", "Bash(git rev-parse*)", "Bash(ls*)", "Bash(cat*)", "Bash(head*)", "Bash(tail*)",
    "Bash(grep*)", "Bash(find*)", "Bash(mkdir*)", "Bash(wc*)", "Bash(date*)", "Bash(sed -n*)", "Bash(awk*)",
    "Bash(dbt parse*)", "Bash(dbt compile*)", "Bash(dbt ls*)",
)


def parse_events(lines) -> dict:
    out = {"thread_id": None, "final_message": "", "usage": Usage(), "error": None}
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        t = e.get("type")
        if t == "system" and e.get("session_id"):
            out["thread_id"] = e.get("session_id")
        elif t == "result":
            out["final_message"] = e.get("result") or out["final_message"]
            u = e.get("usage") or {}
            out["usage"] = Usage(
                input_tokens=int(u.get("input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0)
                + int(u.get("cache_creation_input_tokens") or 0),
                cached_input_tokens=int(u.get("cache_read_input_tokens") or 0),
                output_tokens=int(u.get("output_tokens") or 0),
                cost_usd=e.get("total_cost_usd"),
            )
            if e.get("is_error"):
                out["error"] = e.get("result") or "claude reported an error"
    return out


def tool_note(block: dict) -> str | None:
    """A one-line note for a tool call in an assistant message."""
    name = block.get("name", "")
    inp = block.get("input") or {}
    if name == "Bash":
        return f"$ {inp.get('command', '')}".rstrip()
    if name in ("Edit", "Write", "MultiEdit"):
        return f"editing {inp.get('file_path', '')}".rstrip()
    if name.startswith("mcp__"):
        return "tool " + ".".join(name.split("__")[1:]).replace("plugin_wire_", "", 1)
    return None


class StreamWatcher:
    """Feeds stream-json lines to the person as they arrive: text deltas to
    on_text, tool calls to on_activity. Claude Code in -p mode cannot ask the
    person anything mid-run, so a question still ends the turn."""

    def __init__(self, req: RunRequest):
        self.req = req
        self.streamed = False
        self.in_message = False

    def feed(self, raw: str) -> None:
        try:
            e = json.loads(raw)
        except ValueError:
            return
        t = e.get("type")
        if t == "stream_event":
            ev = e.get("event") or {}
            if ev.get("type") == "message_start" and self.streamed:
                self.in_message = False
            if ev.get("type") == "content_block_delta":
                d = ev.get("delta") or {}
                if d.get("type") == "text_delta" and d.get("text"):
                    if self.streamed and not self.in_message:
                        self.req.on_text("\n\n")
                    self.in_message = True
                    self.streamed = True
                    self.req.on_text(d["text"])
        elif t == "assistant" and self.req.on_activity:
            for block in (e.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    note = tool_note(block)
                    if note:
                        self.req.on_activity(note)


class ClaudeHarness(Harness):
    name = "claude"

    def __init__(self, executable: str | None = None):
        self.executable = executable or shutil.which("claude") or "claude"

    def run(self, req: RunRequest) -> RunResult:
        argv = build_argv(req, self.executable)
        result = RunResult(harness=self.name, argv=argv)
        if not req.env.get("ANTHROPIC_API_KEY"):
            # Without a key, Claude Code runs on the person's own sign-in and its
            # plan limits; business use on a consumer plan is restricted in some
            # regions (Anthropic's consumer terms). Say so, once per run.
            sys.stderr.write("wire: no ANTHROPIC_API_KEY in the environment; Claude Code will use its own sign-in "
                             "and plan limits for this run. Put a key in ~/.wire/secrets.env for API billing.\n")
        watcher = StreamWatcher(req) if "--include-partial-messages" in argv else None
        try:
            with Timer() as t:
                if watcher is None:
                    proc = subprocess.run(argv, input=req.prompt + _mcp_note(req), capture_output=True, text=True,
                                          cwd=str(req.cwd), env=req.env)
                else:
                    proc = _run_watched(argv, req, watcher)
        except OSError as exc:
            result.exit_code, result.error = 127, f"could not run claude: {exc}"
            return result
        result.streamed = bool(watcher and watcher.streamed)
        result.duration_s = t.seconds
        result.exit_code = proc.returncode
        if req.log_dir:
            req.log_dir.mkdir(parents=True, exist_ok=True)
            (req.log_dir / f"{req.label}.claude.jsonl").write_text(proc.stdout, encoding="utf-8")
            result.events_path = str(req.log_dir / f"{req.label}.claude.jsonl")
        parsed = parse_events(proc.stdout.split("\n"))
        result.thread_id = parsed["thread_id"]
        result.final_message = parsed["final_message"]
        result.usage = parsed["usage"]
        result.blocked = blocked_from_stderr(proc.stderr)
        result.stderr_tail = "\n".join([l for l in proc.stderr.split("\n") if l.strip()][-5:])
        result.error = parsed["error"]
        if proc.returncode != 0 and not result.error:
            result.error = result.stderr_tail or f"claude exited {proc.returncode}"
        return result


def _run_watched(argv: list, req: RunRequest, watcher: StreamWatcher) -> subprocess.CompletedProcess:
    """Run claude, reading its stdout line by line for the watcher. stderr goes
    to a temporary file so a full pipe never blocks the run."""
    import tempfile
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as err:
        p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True,
                             encoding="utf-8", cwd=str(req.cwd), env=req.env, bufsize=1)
        p.stdin.write(req.prompt + _mcp_note(req))
        p.stdin.close()
        lines = []
        for line in p.stdout:
            lines.append(line)
            watcher.feed(line)
        code = p.wait()
        err.seek(0)
        return subprocess.CompletedProcess(argv, code, "".join(lines), err.read())

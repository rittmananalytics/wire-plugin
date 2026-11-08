"""One turn on Codex's app-server protocol: streamed text and live questions.

ROADMAP.md phase 2. `codex exec` prints nothing until a turn ends and cannot
ask the person anything, so a question becomes the turn's last message and
the answer goes in as a new turn. `codex app-server` is the protocol Codex's
own editors use: JSON-RPC over stdio, one JSON object per line. On it the
CLI sees the reply as it is written (`item/agentMessage/delta`), sees each
command and file edit as it starts, and answers the agent's
`request_user_input` tool inside the same turn.

What the CLI uses of it (checked against the protocol schema of Codex 0.166.0
and a live handshake with wire-agent):

  > initialize {clientInfo, capabilities.experimentalApi}   < {userAgent, ...}
  > initialized (notification)
  > thread/start {cwd, sandbox, approvalPolicy, model}       < {thread: {id}}
    or thread/resume {threadId, ...}
  > turn/start {threadId, input: [{type: text, text}], outputSchema}
  < item/started, item/agentMessage/delta, item/completed,
    thread/tokenUsage/updated, hook/completed, error, turn/completed
  < item/tool/requestUserInput (a request from the server) > {answers}

The agent is offered `request_user_input` outside plan mode only with the
feature `default_mode_request_user_input`, which the CLI turns on when a
person is attached (`RunRequest.ask`). Approval requests should not arrive
(the approval policy is `never`); any that do are declined, and anything else
the server asks is answered with a JSON-RPC error, so a turn never hangs on
the CLI.

Threads are saved where `codex exec` saves them, so a thread started here can
be resumed by `codex exec resume` and the other way round.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from . import RunRequest, RunResult, Usage, blocked_from_stderr

ASK_FEATURE = ["-c", "features.default_mode_request_user_input=true"]
CLIENT_INFO = {"name": "wire-cli", "title": "Wire CLI"}
DECLINE = {
    "item/commandExecution/requestApproval": {"decision": "decline"},
    "item/fileChange/requestApproval": {"decision": "decline"},
    "applyPatchApproval": {"decision": "denied"},
    "execCommandApproval": {"decision": "denied"},
}


class AppServerUnavailable(Exception):
    """The binary has no app-server, or it did not complete the handshake."""


class Client:
    """A JSON-RPC connection to one `codex app-server` process over stdio."""

    def __init__(self, argv: list, env: dict, cwd: Path, stderr_path: Path | None = None, transcript=None):
        self.transcript = transcript
        self._stderr = open(stderr_path, "w", encoding="utf-8") if stderr_path else subprocess.DEVNULL
        try:
            self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                                         text=True, encoding="utf-8", cwd=str(cwd), env=env, bufsize=1)
        except OSError as exc:
            raise AppServerUnavailable(f"could not start {argv[0]}: {exc}") from exc
        self.next_id = 0

    def send(self, message: dict) -> None:
        try:
            self.proc.stdin.write(json.dumps(message) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as exc:
            raise AppServerUnavailable(f"the app-server closed its input: {exc}") from exc

    def read(self) -> dict | None:
        """The next message, or None when the server has gone."""
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            if self.transcript is not None:
                self.transcript.write(line)
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                return msg

    def request(self, method: str, params: dict, on_message) -> dict:
        """Send a request and read until its response; other messages go to on_message."""
        self.next_id += 1
        rid = self.next_id
        self.send({"id": rid, "method": method, "params": params})
        while True:
            msg = self.read()
            if msg is None:
                raise AppServerUnavailable(f"the app-server exited before answering {method}")
            if msg.get("id") == rid and "method" not in msg:
                if "error" in msg:
                    err = msg["error"] or {}
                    raise RuntimeError(f"{method} failed: {err.get('message', err)}")
                return msg.get("result") or {}
            on_message(msg)

    def respond(self, rid, result: dict | None = None, error: str | None = None) -> None:
        if error is not None:
            self.send({"id": rid, "error": {"code": -32000, "message": error}})
        else:
            self.send({"id": rid, "result": result or {}})

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self._stderr is not subprocess.DEVNULL:
            self._stderr.close()


def question_text(q: dict) -> str:
    """One request_user_input question as the session shows it."""
    lines = []
    if q.get("header"):
        lines.append(str(q["header"]))
    lines.append(str(q.get("question", "")))
    for i, opt in enumerate(q.get("options") or [], 1):
        desc = f" ({opt['description']})" if opt.get("description") else ""
        lines.append(f"  {i}. {opt.get('label', '')}{desc}")
    if q.get("options") and q.get("isOther", True):
        lines.append("  (a number, or your own answer)")
    return "\n".join(lines)


def chosen(q: dict, answer: str) -> str:
    """A typed number picks that option's label; anything else is the answer itself."""
    opts = q.get("options") or []
    a = answer.strip()
    if a.isdigit() and 1 <= int(a) <= len(opts):
        return str(opts[int(a) - 1].get("label", a))
    return a


def activity(item: dict) -> str | None:
    """A one-line note for an item the agent has started, or None."""
    t = item.get("type")
    if t == "commandExecution":
        return f"$ {item.get('command', '')}".rstrip()
    if t == "fileChange":
        paths = [c.get("path", "") for c in item.get("changes") or [] if isinstance(c, dict)]
        return "editing " + (", ".join(paths) if paths else "files")
    if t == "mcpToolCall":
        return f"tool {item.get('server', '')}.{item.get('tool', '')}"
    if t == "webSearch":
        return f"searching the web: {item.get('query', '')}".rstrip(": ")
    return None


def _usage(breakdown: dict) -> Usage:
    return Usage(input_tokens=int(breakdown.get("inputTokens") or 0),
                 cached_input_tokens=int(breakdown.get("cachedInputTokens") or 0),
                 output_tokens=int(breakdown.get("outputTokens") or 0),
                 reasoning_output_tokens=int(breakdown.get("reasoningOutputTokens") or 0))


class Turn:
    """The state of one turn, fed message by message (kept apart from the
    process so the tests can drive it with recorded messages)."""

    def __init__(self, req: RunRequest, client: Client | None = None):
        self.req = req
        self.client = client
        self.thread_id: str | None = None
        self.turn_id: str | None = None
        self.final = ""
        self.streamed = False
        self.usage = Usage()
        self.blocked: list = []
        self.error: str | None = None
        self.done = False
        self.status: str | None = None
        self.questions = 0

    def _text(self, s: str) -> None:
        if self.req.on_text and s:
            self.req.on_text(s)

    def _note(self, s: str) -> None:
        if self.req.on_activity and s:
            self.req.on_activity(s)

    def handle(self, msg: dict) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        if "id" in msg and method:
            self.server_request(msg["id"], method, params)
            return
        if not method:
            return
        if method == "item/agentMessage/delta":
            self._text(params.get("delta", ""))
            self.streamed = True
        elif method == "item/started":
            item = params.get("item") or {}
            if item.get("type") == "agentMessage" and self.streamed:
                self._text("\n\n")  # a second message in the same turn
            note = activity(item)
            if note:
                self._note(note)
        elif method == "item/completed":
            item = params.get("item") or {}
            if item.get("type") == "agentMessage" and item.get("text"):
                self.final = item["text"]
        elif method == "thread/tokenUsage/updated":
            # `last` is one model request; a turn makes several, so they are summed
            last = _usage((params.get("tokenUsage") or {}).get("last") or {})
            for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
                setattr(self.usage, key, getattr(self.usage, key) + getattr(last, key))
        elif method == "hook/completed":
            run = params.get("run") or {}
            if run.get("status") == "blocked":
                texts = [e.get("text", "") for e in run.get("entries") or [] if isinstance(e, dict)]
                self.blocked.append("; ".join(t for t in texts if t) or run.get("statusMessage") or "blocked by a hook")
        elif method == "error":
            if not params.get("willRetry"):
                self.error = ((params.get("error") or {}).get("message")) or "the agent reported an error"
        elif method == "turn/completed":
            turn = params.get("turn") or {}
            if self.turn_id and turn.get("id") not in (None, self.turn_id):
                return
            self.status = turn.get("status")
            if self.status == "failed":
                self.error = ((turn.get("error") or {}).get("message")) or self.error or "the turn failed"
            elif self.status == "interrupted":
                self.error = self.error or "interrupted"
            self.done = True

    def server_request(self, rid, method: str, params: dict) -> None:
        c = self.client
        if c is None:
            return
        if method == "item/tool/requestUserInput":
            if self.req.ask is None:
                c.respond(rid, error="no person is attached to this run; carry on without an answer")
                return
            answers = {}
            for q in params.get("questions") or []:
                self.questions += 1
                if self.streamed:
                    self._text("\n")
                self._note("question from the agent")
                raw = self.req.ask(question_text(q) + "\nyou> ") or ""
                answers[q.get("id", str(self.questions))] = {"answers": [chosen(q, raw)] if raw.strip() else []}
            c.respond(rid, {"answers": answers})
            return
        if method in DECLINE:
            self._note(f"declined an approval request ({method})")
            c.respond(rid, DECLINE[method])
            return
        c.respond(rid, error=f"the Wire CLI does not handle {method}")


def thread_params(req: RunRequest, lane_profile: bool) -> dict:
    p = {"cwd": str(req.cwd), "approvalPolicy": "never"}
    if not lane_profile:
        p["sandbox"] = req.sandbox
    if req.model:
        p["model"] = req.model
    return p


def run_turn(executable: str, overrides: list, req: RunRequest, prompt: str, env: dict, lane_profile: bool,
             version: str = "") -> RunResult:
    """One turn, start to finish. Raises AppServerUnavailable when the binary
    cannot serve the protocol, so the caller can fall back to `codex exec`."""
    argv = [executable] + list(overrides) + (ASK_FEATURE if req.ask is not None else []) + ["app-server"]
    result = RunResult(harness="codex", argv=argv)
    transcript = stderr_path = None
    if req.log_dir:
        req.log_dir.mkdir(parents=True, exist_ok=True)
        result.events_path = str(req.log_dir / f"{req.label}.app-server.jsonl")
        transcript = open(result.events_path, "w", encoding="utf-8")
        stderr_path = req.log_dir / f"{req.label}.app-server.stderr.txt"
    started = time.monotonic()
    client = Client(argv, env, req.cwd, stderr_path, transcript)
    turn = Turn(req, client)
    try:
        try:
            client.request("initialize", {"clientInfo": dict(CLIENT_INFO, version=version),
                                          "capabilities": {"experimentalApi": True}}, turn.handle)
        except RuntimeError as exc:
            raise AppServerUnavailable(str(exc)) from exc
        client.send({"method": "initialized"})
        params = thread_params(req, lane_profile)
        if req.resume_thread:
            res = client.request("thread/resume", dict(params, threadId=req.resume_thread), turn.handle)
        else:
            res = client.request("thread/start", params, turn.handle)
        turn.thread_id = ((res.get("thread") or {}).get("id")) or req.resume_thread
        tparams = {"threadId": turn.thread_id, "input": [{"type": "text", "text": prompt}]}
        if req.output_schema:
            tparams["outputSchema"] = json.loads(Path(req.output_schema).read_text(encoding="utf-8"))
        res = client.request("turn/start", tparams, turn.handle)
        turn.turn_id = ((res.get("turn") or {}).get("id"))
        interrupted = False
        while not turn.done:
            try:
                msg = client.read()
            except KeyboardInterrupt:
                if interrupted or not turn.turn_id:
                    raise
                interrupted = True
                client.send({"id": "interrupt", "method": "turn/interrupt",
                             "params": {"threadId": turn.thread_id, "turnId": turn.turn_id}})
                continue
            if msg is None:
                turn.error = turn.error or "the app-server exited during the turn"
                break
            turn.handle(msg)
    except RuntimeError as exc:
        turn.error = str(exc)
    finally:
        client.close()
        if transcript:
            transcript.close()
    result.duration_s = time.monotonic() - started
    result.thread_id = turn.thread_id
    result.final_message = turn.final
    result.usage = turn.usage
    result.blocked = list(turn.blocked)
    if stderr_path and stderr_path.is_file():
        err = stderr_path.read_text(encoding="utf-8", errors="replace")
        for b in blocked_from_stderr(err):
            if b not in result.blocked:
                result.blocked.append(b)
        result.stderr_tail = "\n".join([l for l in err.split("\n") if l.strip()][-5:])
    result.error = turn.error
    result.exit_code = 0 if not turn.error else 1
    result.streamed = turn.streamed
    return result

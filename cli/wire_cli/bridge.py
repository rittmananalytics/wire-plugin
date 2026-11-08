"""The Wire bridge: Claude (and any Anthropic-hosted model) for Codex.

Codex speaks only the Responses API. Anthropic's own OpenAI-compatible
endpoint is Chat Completions and not for production, so the bridge runs a
LiteLLM proxy (which translates Responses API calls to the Anthropic Messages
API with prompt caching) behind a small shim that removes what LiteLLM cannot
map: Codex sends tool specs of type `namespace` (its tool-search feature), and
LiteLLM's Anthropic mapper raises on any tool type but `function`.

    wire bridge start [--port 4100]     start LiteLLM and the shim, print the Codex settings
    wire bridge stop
    wire bridge status

The codex harness uses it when the provider is `wirebridge`: it passes the
provider settings per run (`-c model_providers.wirebridge.*`), so nothing is
written to the person's ~/.codex/config.toml. Keys come from the environment
(ANTHROPIC_API_KEY from ~/.wire/secrets.env). The shim listens on localhost
only.
"""

from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path(os.environ.get("WIRE_HOME", Path.home() / ".wire"))
BRIDGE_DIR = HOME / "bridge"
VENV = HOME / "bridge-venv"
SHIM_PORT = 4100
LITELLM_PORT = 4101
KEEP_TOOL_TYPES = {"function"}
# Responses API request fields LiteLLM passes through and the Anthropic API
# rejects as extra inputs (seen live: client_metadata). Removed by the shim.
DROP_REQUEST_KEYS = ("client_metadata", "prompt_cache_key", "safety_identifier", "store", "service_tier", "include", "truncation", "metadata")
MODELS = ("claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5", "claude-fable-5-1")

LITELLM_CONFIG = """# Written by `wire bridge start`. Keys come from the environment.
model_list:
{models}
litellm_settings:
  enable_anthropic_prompt_caching: true
  drop_params: true
"""


def litellm_config_text(models=MODELS) -> str:
    entries = "\n".join(
        f"  - model_name: {m}\n    litellm_params:\n      model: anthropic/{m}\n      api_key: os.environ/ANTHROPIC_API_KEY"
        for m in models)
    return LITELLM_CONFIG.format(models=entries)


def codex_provider_overrides(port: int = SHIM_PORT) -> list:
    """The -c overrides that make Codex use the bridge for one run."""
    return [
        "-c", 'model_providers.wirebridge.name="Wire bridge (Claude via LiteLLM)"',
        "-c", f'model_providers.wirebridge.base_url="http://127.0.0.1:{port}/v1"',
        "-c", 'model_providers.wirebridge.wire_api="responses"',
        "-c", 'model_providers.wirebridge.env_key="WIRE_BRIDGE_KEY"',
    ]


# ---------------------------------------------------------------- the shim

def rewrite_request(body: bytes) -> tuple:
    """(body, dropped tool types) with unsupported tool specs removed."""
    try:
        data = json.loads(body)
    except ValueError:
        return body, []
    changed = False
    for key in DROP_REQUEST_KEYS:
        if key in data:
            data.pop(key, None)
            changed = True
    # Anthropic's 5.x models refuse a conversation that ends with an assistant
    # turn ("assistant message prefill"); Codex's input can end with one (a
    # reasoning or message item after tool output). Close it with a user turn.
    items = data.get("input")
    if isinstance(items, list) and items:
        reordered = reorder_tool_groups(items)
        if reordered != items:
            data["input"] = items = reordered
            changed = True
        last = items[-1]
        ends_with_user = isinstance(last, dict) and (
            last.get("type") == "function_call_output"
            or (last.get("type", "message") == "message" and last.get("role", "user") == "user"))
        if not ends_with_user:
            # Anything else at the end (a reasoning item, an assistant message, a
            # compaction summary, an item reference) reads as an assistant turn.
            items.append({"type": "message", "role": "user",
                          "content": [{"type": "input_text", "text": "Continue."}]})
            changed = True
    tools = data.get("tools")
    if not isinstance(tools, list):
        return (json.dumps(data).encode("utf-8") if changed else body), []
    kept, dropped = [], []
    for t in tools:
        if isinstance(t, dict) and t.get("type") in KEEP_TOOL_TYPES:
            kept.append(t)
        else:
            dropped.append(str((t or {}).get("type")) if isinstance(t, dict) else "?")
    if not dropped and not changed:
        return body, []
    data["tools"] = kept
    if not kept:
        data.pop("tools", None)
        data.pop("tool_choice", None)
    return json.dumps(data).encode("utf-8"), dropped


def reorder_tool_groups(items: list) -> list:
    """Codex can place an assistant message between a function_call and its
    function_call_output. The Anthropic API needs the tool result to follow
    the tool use directly, and LiteLLM's translation of the interleaved form
    ended with an assistant turn (seen live: prefill rejected after the third
    attempt). Assistant messages and reasoning inside such a group move in
    front of the group's first function_call."""
    out = []
    group_calls, group_between, pending = [], [], 0
    for item in items:
        t = item.get("type") if isinstance(item, dict) else None
        if t == "function_call":
            group_calls.append(item)
            pending += 1
            continue
        if pending and t in ("message", "reasoning") and (t == "reasoning" or item.get("role") == "assistant"):
            group_between.append(item)
            continue
        if t == "function_call_output" and pending:
            if group_calls:
                out.extend(group_between)
                out.extend(group_calls)
                group_between, group_calls = [], []
            out.append(item)
            pending -= 1
            continue
        # anything else closes an open group as it stands
        out.extend(group_between)
        out.extend(group_calls)
        group_between, group_calls, pending = [], [], 0
        out.append(item)
    out.extend(group_between)
    out.extend(group_calls)
    return out


class ShimHandler(BaseHTTPRequestHandler):
    upstream_port = LITELLM_PORT
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quiet; the bridge log has what matters
        sys.stderr.write("shim: " + (fmt % args) + "\n")

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        dropped = []
        if self.command == "POST" and self.path.startswith("/v1/responses"):
            body, dropped = rewrite_request(body)
            if dropped:
                sys.stderr.write(f"shim: dropped tool types {sorted(set(dropped))}\n")
        conn = http.client.HTTPConnection("127.0.0.1", self.upstream_port, timeout=600)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length", "transfer-encoding")}
        headers["Content-Length"] = str(len(body))
        conn.request(self.command, self.path, body=body, headers=headers)
        resp = conn.getresponse()
        if resp.status >= 400 and self.path.startswith("/v1/responses"):
            try:
                tail = json.loads(body).get("input", [])[-3:]
                sys.stderr.write("shim: upstream %d; last input items: %s\n" % (
                    resp.status, [(i.get("type"), i.get("role")) for i in tail if isinstance(i, dict)]))
            except Exception:  # noqa: BLE001 - diagnostics only
                pass
        self.send_response(resp.status)
        chunked = False
        for k, v in resp.getheaders():
            if k.lower() in ("transfer-encoding", "content-length", "connection"):
                chunked = chunked or (k.lower() == "transfer-encoding" and "chunked" in v.lower())
                continue
            self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            self.wfile.write(b"%x\r\n" % len(chunk) + chunk + b"\r\n")
            self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()
        conn.close()

    def do_POST(self):
        self._forward()

    def do_GET(self):
        self._forward()


def serve_shim(port: int = SHIM_PORT, upstream: int = LITELLM_PORT) -> None:
    ShimHandler.upstream_port = upstream
    server = ThreadingHTTPServer(("127.0.0.1", port), ShimHandler)
    server.daemon_threads = True
    server.serve_forever()


# ---------------------------------------------------------------- lifecycle

def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _pid_file(name: str) -> Path:
    return BRIDGE_DIR / f"{name}.pid"


def start(env: dict, port: int = SHIM_PORT, out=print) -> int:
    if not env.get("ANTHROPIC_API_KEY"):
        out("ANTHROPIC_API_KEY is not set; put it in ~/.wire/secrets.env (see wire/cli/README.md).")
        return 1
    litellm = VENV / "bin" / "litellm"
    if not litellm.is_file():
        out(f"LiteLLM is not installed at {VENV}. Install it with:")
        out(f"  python3 -m venv {VENV} && {VENV}/bin/pip install 'litellm[proxy]'")
        return 1
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    (BRIDGE_DIR / "litellm.yaml").write_text(litellm_config_text(), encoding="utf-8")
    run_env = dict(env)
    run_env.setdefault("WIRE_BRIDGE_KEY", "local")
    if not _port_open(LITELLM_PORT):
        log = open(BRIDGE_DIR / "litellm.log", "a")
        p = subprocess.Popen([str(litellm), "--config", str(BRIDGE_DIR / "litellm.yaml"), "--host", "127.0.0.1", "--port", str(LITELLM_PORT)],
                             stdout=log, stderr=subprocess.STDOUT, env=run_env, start_new_session=True)
        _pid_file("litellm").write_text(str(p.pid))
        for _ in range(60):
            if _port_open(LITELLM_PORT):
                break
            time.sleep(1)
    if not _port_open(port):
        log = open(BRIDGE_DIR / "shim.log", "a")
        p = subprocess.Popen([sys.executable, __file__, "--serve", str(port), str(LITELLM_PORT)],
                             stdout=log, stderr=subprocess.STDOUT, env=run_env, start_new_session=True)
        _pid_file("shim").write_text(str(p.pid))
        for _ in range(20):
            if _port_open(port):
                break
            time.sleep(0.5)
    ok = _port_open(LITELLM_PORT) and _port_open(port)
    out(f"bridge: litellm on 127.0.0.1:{LITELLM_PORT} {'up' if _port_open(LITELLM_PORT) else 'DOWN'}; shim on 127.0.0.1:{port} {'up' if _port_open(port) else 'DOWN'}")
    out("Use it: wire <command> <release> --harness codex --provider wirebridge --model claude-sonnet-5-5")
    out("Models: " + ", ".join(MODELS))
    return 0 if ok else 1


def stop(out=print) -> int:
    stopped = []
    for name in ("shim", "litellm"):
        pf = _pid_file(name)
        if pf.is_file():
            try:
                os.killpg(int(pf.read_text().strip()), signal.SIGTERM)
                stopped.append(name)
            except (OSError, ValueError):
                pass
            pf.unlink(missing_ok=True)
    out("bridge: stopped " + (", ".join(stopped) if stopped else "nothing (not running)"))
    return 0


def status(out=print) -> int:
    out(f"bridge: litellm {'up' if _port_open(LITELLM_PORT) else 'down'} (127.0.0.1:{LITELLM_PORT}); shim {'up' if _port_open(SHIM_PORT) else 'down'} (127.0.0.1:{SHIM_PORT})")
    return 0 if _port_open(SHIM_PORT) else 1


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--serve":
        serve_shim(int(sys.argv[2]), int(sys.argv[3]))

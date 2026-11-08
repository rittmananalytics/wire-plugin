"""The harness interface: run a prompt in a directory, return what happened.

One adapter per agent runtime. The CLI never reads a transcript: every
adapter returns the same RunResult (final message, token usage, the calls a
hook blocked, exit code, duration), so the record is written the same way
whichever harness ran the step.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

BLOCKED_RE = re.compile(r"Command blocked by PreToolUse hook: (.*?)(?:\. Command: .*)?$")


@dataclass
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    cost_usd: float | None = None

    @property
    def total(self) -> int:
        return int(self.input_tokens) + int(self.output_tokens)

    def tokens_cell(self) -> str:
        return str(self.total) if self.total else "n/a"

    def cost_cell(self) -> str:
        return f"${self.cost_usd:.2f}" if self.cost_usd is not None else "n/a"


@dataclass
class RunResult:
    harness: str
    exit_code: int = 0
    final_message: str = ""
    usage: Usage = field(default_factory=Usage)
    blocked: list = field(default_factory=list)
    duration_s: float = 0.0
    thread_id: str | None = None
    error: str | None = None
    argv: list = field(default_factory=list)
    events_path: str | None = None
    stderr_tail: str = ""
    streamed: bool = False  # the reply was shown as it was written (RunRequest.on_text)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.error


@dataclass
class RunRequest:
    prompt: str
    cwd: Path
    env: dict
    model: str | None = None
    provider: str | None = None
    sandbox: str = "workspace-write"
    output_schema: Path | None = None
    log_dir: Path | None = None
    label: str = "run"
    mcp: dict = field(default_factory=dict)  # MCP servers for this run: key -> URL (wire_cli/mcp.py)
    resume_thread: str | None = None  # continue this conversation (codex exec resume, claude --resume)
    wire_tools: bool = False  # start Wire's own tools server for this run (tools_server.py)
    write_paths: list = field(default_factory=list)  # a lane: only these are writable (an OS sandbox profile)
    # A person watching (ROADMAP.md phase 2). With on_text the reply is shown as it is
    # written; on_activity gets one line per command, edit or tool call as it starts;
    # with ask the agent can put a question to the person inside the turn. Lanes and
    # unattended runs leave all three unset.
    on_text: Callable | None = None
    on_activity: Callable | None = None
    ask: Callable | None = None


class Harness:
    name = "base"

    def run(self, req: RunRequest) -> RunResult:  # pragma: no cover - interface
        raise NotImplementedError


def blocked_from_stderr(text: str) -> list:
    out = []
    for line in (text or "").split("\n"):
        m = BLOCKED_RE.search(line)
        if m:
            out.append(m.group(1).strip())
    return out


def parse_report(final_message: str) -> dict | None:
    """The lane report (a JSON object) in a final message, or None."""
    text = (final_message or "").strip()
    if not text:
        return None
    candidates = [text]
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        candidates.insert(0, m.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            obj = json.loads(c)
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


class Timer:
    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *exc):
        self.seconds = time.monotonic() - self.start


def get_harness(name: str) -> Harness:
    if name == "codex":
        from .codex import CodexHarness
        return CodexHarness()
    if name == "claude":
        from .claude import ClaudeHarness
        return ClaudeHarness()
    if name == "fake":
        from .fake import FakeHarness
        return FakeHarness()
    raise ValueError(f"unknown harness {name!r}; one of codex, claude, fake")

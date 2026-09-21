#!/usr/bin/env python3
"""Wire Framework — execution-log metrics backfill (Claude Code Stop hook).

Fires after each turn ends (invoked by hooks/wire-metrics.sh). Reads the
session transcript named in the hook payload, finds the most recent /wire:*
command invocation, sums the measured token usage from that point to the end
of the turn, estimates its cost, and backfills the Duration / Tokens /
Cost (USD) cells of the most recent row of the project's execution_log.md.

Contract (specs/utils/execution_log.md — Metrics Backfill):
  - Only the metric cells of the final data row are ever rewritten, and only
    when that row's Command cell matches the command found in the transcript.
  - Duration is filled only if still `n/a` (the workflow usually measured it).
  - Rows without the metric columns (legacy shapes) are left untouched.
  - Token counts come only from transcript `usage` records — never estimated.
  - Unknown model → Tokens filled, Cost stays `n/a`.

Stdlib only. Never raises to the caller: main() catches everything and
exits 0 so the hook can never block or fail a command.
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Anthropic API prices, USD per million tokens, as of 2026-09.
# (input, output, cache_read). Cache writes are charged at 1.25x input.
# Matched by substring against the transcript's model id, first match wins,
# so more specific ids must come before their prefixes.
PRICING = [
    ("claude-haiku-4-5", (1.00, 5.00, 0.10)),
    ("claude-sonnet-4-6", (3.00, 15.00, 0.30)),
    ("claude-sonnet-5", (2.00, 10.00, 0.20)),
    ("claude-opus-4", (5.00, 25.00, 0.50)),
    ("claude-opus-5", (5.00, 25.00, 0.50)),
    ("claude-fable-5-1", (10.00, 50.00, 0.25)),
    ("claude-fable-5", (10.00, 50.00, 1.00)),
    ("claude-mythos-5", (10.00, 50.00, 1.00)),
]

CACHE_WRITE_MULTIPLIER = 1.25
COMMAND_RE = re.compile(r"/wire:[A-Za-z0-9_-]+")
NA = "n/a"
# Only a log written recently can belong to the turn that just ended.
MAX_LOG_AGE_SECONDS = 30 * 60


def _text_of(content):
    """Flatten a transcript message content field (string or block list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def _parse_ts(value):
    """ISO-8601 timestamp string → epoch seconds, or None."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def read_transcript(path):
    """Parse a transcript JSONL file into a list of dict entries."""
    entries = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                entries.append(entry)
    return entries


def extract_run(entries):
    """Find the last /wire: command in the transcript and measure the run.

    Returns {command, tokens, usage, model, duration_seconds} or None when
    the transcript holds no /wire: invocation. Usage is summed over every
    assistant message from the command's user message to the end.
    """
    anchor = None
    for i, entry in enumerate(entries):
        if entry.get("type") != "user":
            continue
        message = entry.get("message") or {}
        text = _text_of(message.get("content"))
        match = None
        for match in COMMAND_RE.finditer(text):
            pass  # keep the last command token in this message
        if match:
            anchor = (i, match.group(0), _parse_ts(entry.get("timestamp")))
    if anchor is None:
        return None

    start_index, command, start_ts = anchor
    usage_total = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    model = None
    last_ts = start_ts
    seen_usage = False
    for entry in entries[start_index:]:
        ts = _parse_ts(entry.get("timestamp"))
        if ts is not None:
            last_ts = ts
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message") or {}
        usage = message.get("usage") or {}
        if not isinstance(usage, dict) or not usage:
            continue
        seen_usage = True
        for key in usage_total:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                usage_total[key] += int(value)
        if isinstance(message.get("model"), str):
            model = message["model"]
    if not seen_usage:
        return None

    duration = None
    if start_ts is not None and last_ts is not None and last_ts >= start_ts:
        duration = int(last_ts - start_ts)
    return {
        "command": command,
        "tokens": sum(usage_total.values()),
        "usage": usage_total,
        "model": model,
        "duration_seconds": duration,
    }


def compute_cost(model, usage):
    """Estimated USD cost of a usage dict, or None for an unknown model."""
    if not model:
        return None
    rates = None
    for key, value in PRICING:
        if key in model:
            rates = value
            break
    if rates is None:
        return None
    input_rate, output_rate, cache_read_rate = rates
    cost = (
        usage.get("input_tokens", 0) * input_rate
        + usage.get("output_tokens", 0) * output_rate
        + usage.get("cache_read_input_tokens", 0) * cache_read_rate
        + usage.get("cache_creation_input_tokens", 0)
        * input_rate
        * CACHE_WRITE_MULTIPLIER
    ) / 1_000_000
    return round(cost, 2)


def format_duration(seconds):
    if seconds is None:
        return NA
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


def update_log_text(text, run):
    """Backfill the metric cells of the last data row of an execution log.

    Returns the updated text, or None when nothing may be changed: no
    seven-plus-column row (legacy shape), or a Command cell that does not
    match the run's command.
    """
    lines = text.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= {"-", " "} or cells[0] == "Timestamp":
            return None  # reached the separator or header: no data rows
        # Metric columns are the last three; they exist only in the
        # nine-column shape (or eight for pre-By/Session rows was never
        # shipped with metrics, so require at least 9).
        if len(cells) < 9:
            return None
        if cells[1] != run["command"]:
            return None
        duration_cell, tokens_cell, cost_cell = cells[-3], cells[-2], cells[-1]
        if duration_cell == NA:
            duration_cell = format_duration(run["duration_seconds"])
        tokens_cell = str(run["tokens"])
        cost = compute_cost(run["model"], run["usage"])
        cost_cell = NA if cost is None else f"${cost:.2f}"
        cells[-3], cells[-2], cells[-1] = duration_cell, tokens_cell, cost_cell
        lines[i] = "| " + " | ".join(cells) + " |"
        return "\n".join(lines)
    return None


def find_log_file(cwd, now=None, max_age=MAX_LOG_AGE_SECONDS):
    """Most recently modified execution_log.md under cwd's .wire tree(s)."""
    now = time.time() if now is None else now
    best = None
    root = Path(cwd)
    for wire_dir in [root / ".wire"] + [p for p in root.glob("*/.wire")]:
        if not wire_dir.is_dir():
            continue
        for log in wire_dir.rglob("execution_log.md"):
            try:
                mtime = log.stat().st_mtime
            except OSError:
                continue
            if now - mtime > max_age:
                continue
            if best is None or mtime > best[0]:
                best = (mtime, log)
    return best[1] if best else None


def main():
    try:
        payload = json.load(sys.stdin)
        transcript_path = payload.get("transcript_path")
        cwd = payload.get("cwd") or "."
        if not transcript_path or not Path(transcript_path).is_file():
            return 0
        run = extract_run(read_transcript(transcript_path))
        if run is None:
            return 0
        log_file = find_log_file(cwd)
        if log_file is None:
            return 0
        text = log_file.read_text(encoding="utf-8")
        updated = update_log_text(text, run)
        if updated is not None and updated != text:
            log_file.write_text(updated, encoding="utf-8")
    except Exception:
        pass  # a metrics hook must never block or fail the command
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The release record, written by the CLI alone (director rule 6).

status.md keys are updated in place, never re-dumped (execution_log.md rule 8),
and the file is checked afterwards with scripts/status_file.py. Log rows are
appended in the nine-column form of specs/utils/execution_log.md, with the
timestamp rule (never backwards) and the Detail rules (no pipes, 120 chars).
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TS_FORMAT = "%Y-%m-%d %H:%MZ"
CLAIM_FORMAT = "%Y-%m-%d %H:%M"
LOG_HEADER = ("# Execution Log\n\n"
              "| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |\n"
              "|-----------|---------|--------|--------|----|---------|----------|--------|------------|\n")
RECORD_FILES = ("status.md", "execution_log.md")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ts(now: datetime | None = None) -> str:
    return (now or utc_now()).strftime(TS_FORMAT)


def claim_ts(now: datetime | None = None) -> str:
    return (now or utc_now()).strftime(CLAIM_FORMAT)


def duration_text(seconds: float) -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s // 3600}h {(s % 3600) // 60:02d}m"


def git_user(repo: Path) -> str:
    try:
        out = subprocess.run(["git", "config", "--get", "user.name"], cwd=str(repo),
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    return out or "unknown"


def git_branch(repo: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo),
                              capture_output=True, text=True, timeout=10).stdout.strip() or "HEAD"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


# ---------------------------------------------------------------- front matter editing

def _front_matter_lines(text: str) -> tuple[list[str], int]:
    """(lines, index of the closing --- line) or (lines, -1)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return lines, -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines, i
    return lines, -1


def update_artifact_outcome(text: str, artifact: str, action: str, value: str) -> str:
    """Set artifacts.<artifact>.<action> in place. Handles the flow form
    (`  dbt: {generate: complete, validate: pass}`) and the block form
    (`  dbt:` then `    generate: complete`). Raises KeyError when the
    artifact is not in the front matter."""
    lines, end = _front_matter_lines(text)
    if end < 0:
        raise KeyError("status.md has no front matter")
    art_re = re.compile(rf"^  {re.escape(artifact)}:\s*(.*)$")
    rng = list(range(1, end))
    # A 3.x status keeps the artifacts in a fenced block in the body: edit it there.
    if not any(re.match(r"^artifacts:", lines[i]) for i in rng):
        block = _body_block_lines(lines)
        if block:
            art_re = re.compile(rf"^({re.escape(artifact)}:\s*)(.*)$")
            for i in block:
                m = art_re.match(lines[i])
                if not m:
                    continue
                head, rest = m.group(1), m.group(2)
                if rest.startswith("{"):
                    key_re = re.compile(rf"(\b{re.escape(action)}:\s*)([^,}}]+)")
                    if key_re.search(rest):
                        rest = key_re.sub(lambda mm: mm.group(1) + value, rest, count=1)
                    else:
                        inner = rest.strip()[1:-1].strip()
                        rest = "{" + (inner + ", " if inner else "") + f"{action}: {value}" + "}"
                    lines[i] = head + rest  # the original alignment is kept
                    return "\n".join(lines)
                j = i + 1
                while j < len(lines) and lines[j].startswith("  "):
                    if re.match(rf"^  {re.escape(action)}:", lines[j]):
                        lines[j] = f"  {action}: {value}"
                        return "\n".join(lines)
                    j += 1
                lines.insert(i + 1, f"  {action}: {value}")
                return "\n".join(lines)
            raise KeyError(f"artifact {artifact!r} is not in status.md's artifacts block")
    for i in rng:
        m = art_re.match(lines[i])
        if not m:
            continue
        rest = m.group(1)
        if rest.startswith("{"):
            key_re = re.compile(rf"(\b{re.escape(action)}:\s*)([^,}}]+)")
            if key_re.search(rest):
                rest = key_re.sub(lambda mm: mm.group(1) + value, rest, count=1)
            else:
                inner = rest.strip()[1:-1].strip()
                rest = "{" + (inner + ", " if inner else "") + f"{action}: {value}" + "}"
            lines[i] = f"  {artifact}: {rest}"
            return "\n".join(lines)
        # block form: the indented keys that follow
        j = i + 1
        while j < end and lines[j].startswith("    "):
            if re.match(rf"^    {re.escape(action)}:", lines[j]):
                lines[j] = f"    {action}: {value}"
                return "\n".join(lines)
            j += 1
        lines.insert(i + 1, f"    {action}: {value}")
        return "\n".join(lines)
    raise KeyError(f"artifact {artifact!r} is not in status.md")


def _body_block_lines(lines: list) -> list:
    """Line indices inside the body's fenced artifacts block (3.x), or []."""
    start = None
    for i, l in enumerate(lines):
        if re.match(r"^##\s+Artifacts?(?:\s+Status)?\s*$", l):
            start = i
            break
    if start is None:
        return []
    open_i = next((i for i in range(start + 1, len(lines)) if re.match(r"^```ya?ml\s*$", lines[i])), None)
    if open_i is None:
        return []
    close_i = next((i for i in range(open_i + 1, len(lines)) if lines[i].startswith("```")), None)
    return list(range(open_i + 1, close_i)) if close_i else []


def set_top_key(text: str, key: str, value: str) -> str:
    """Set a top-level scalar key of the front matter in place, or add it
    before the closing ---."""
    lines, end = _front_matter_lines(text)
    if end < 0:
        return text
    for i in range(1, end):
        if re.match(rf"^{re.escape(key)}:", lines[i]):
            lines[i] = f'{key}: "{value}"'
            return "\n".join(lines)
    lines.insert(end, f'{key}: "{value}"')
    return "\n".join(lines)


CLAIM_KEYS = ("user", "session_id", "branch", "claimed_at", "last_write")


def _yq(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_claim(text: str, claim: dict) -> str:
    """Write agents.coordinator_session in place: replace the block's known
    keys, replace a null, or add the agents block before the closing ---."""
    lines, end = _front_matter_lines(text)
    if end < 0:
        return text
    block = [f"  coordinator_session:"] + [f"    {k}: {_yq(claim[k])}" for k in CLAIM_KEYS if k in claim]
    agents_i = next((i for i in range(1, end) if re.match(r"^agents:", lines[i])), None)
    if agents_i is None:
        lines[end:end] = ["agents:", "  mode: orchestrated"] + block
        return "\n".join(lines)
    # the extent of the agents block
    j = agents_i + 1
    while j < end and (lines[j].startswith("  ") or not lines[j].strip()):
        j += 1
    cs_i = next((i for i in range(agents_i + 1, j) if re.match(r"^  coordinator_session:", lines[i])), None)
    if cs_i is None:
        lines[agents_i + 1:agents_i + 1] = block
        return "\n".join(lines)
    if not re.match(r"^  coordinator_session:\s*$", lines[cs_i]):
        # `coordinator_session: null` (or inline): replace the line
        lines[cs_i:cs_i + 1] = block
        return "\n".join(lines)
    k = cs_i + 1
    while k < j and lines[k].startswith("    "):
        k += 1
    existing = lines[cs_i + 1:k]
    for key in CLAIM_KEYS:
        if key not in claim:
            continue
        idx = next((n for n, l in enumerate(existing) if re.match(rf"^    {key}:", l)), None)
        if idx is None:
            existing.append(f"    {key}: {_yq(claim[key])}")
        else:
            existing[idx] = f"    {key}: {_yq(claim[key])}"
    lines[cs_i + 1:k] = existing
    return "\n".join(lines)


def refresh_last_write(text: str, when: str) -> str:
    lines, end = _front_matter_lines(text)
    for i in range(1, max(end, 0)):
        if re.match(r"^    last_write:", lines[i]):
            lines[i] = f"    last_write: {_yq(when)}"
            return "\n".join(lines)
    return text


def set_last_orchestrated(text: str, when: str) -> str:
    lines, end = _front_matter_lines(text)
    for i in range(1, max(end, 0)):
        if re.match(r"^  last_orchestrated:", lines[i]):
            lines[i] = f"  last_orchestrated: {_yq(when)}"
            return "\n".join(lines)
    return text


def next_parked_id(text: str) -> str:
    ids = [int(m) for m in re.findall(r"^\s+-\s+id:\s*PD-(\d+)", text, re.M)]
    return f"PD-{(max(ids) + 1) if ids else 1}"


def append_parked_decision(text: str, artifact: str, question: str, when: str, kind: str = "ruling") -> tuple[str, str]:
    """Add a parked decision to status.md's parked_decisions block in place
    (the Claude mod's /wire-park does the same). Returns (text, id)."""
    lines, end = _front_matter_lines(text)
    if end < 0:
        return text, ""
    pid = next_parked_id(text)
    item = [f"  - id: {pid}", f"    artifact: {artifact}", f"    kind: {kind}",
            f"    question: {_yq(question)}", f"    parked_at: {_yq(when)}"]
    key = next((i for i in range(1, end) if re.match(r"^parked_decisions:", lines[i])), None)
    if key is None:
        lines[end:end] = ["parked_decisions:"] + item
        return "\n".join(lines), pid
    if re.match(r"^parked_decisions:\s*(\[\s*\]|null)?\s*$", lines[key]) and not re.match(r"^parked_decisions:\s*$", lines[key]):
        lines[key] = "parked_decisions:"
    j = key + 1
    while j < end and (lines[j].startswith(" ") or not lines[j].strip()):
        j += 1
    while j > key + 1 and not lines[j - 1].strip():
        j -= 1
    lines[j:j] = item
    return "\n".join(lines), pid


# ---------------------------------------------------------------- the log

def ensure_log(path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LOG_HEADER, encoding="utf-8")


def _rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.split("\n"):
        if line.startswith("|") and not line.startswith("|--") and "Timestamp" not in line:
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def last_timestamp(text: str) -> str | None:
    rows = _rows(text)
    return rows[-1][0] if rows and rows[-1] else None


def clean_detail(detail: str) -> str:
    d = (detail or "").replace("|", "—").replace("\n", " ").strip()
    return d if len(d) <= 120 else d[:117] + "..."


def append_log_row(path: Path, command: str, result: str, detail: str, by: str, session: str,
                   duration: str = "n/a", tokens: str = "n/a", cost: str = "n/a",
                   now: datetime | None = None) -> str:
    """Append one row. The timestamp never goes backwards: a row whose time is
    before the last row's takes the last row's time (execution_log.md rule 6)."""
    ensure_log(path)
    text = path.read_text(encoding="utf-8")
    when = ts(now)
    last = last_timestamp(text)
    if last and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}Z$", last) and last > when:
        when = last
    row = f"| {when} | {command} | {result} | {clean_detail(detail)} | {by} | {session} | {duration} | {tokens} | {cost} |"
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + row + "\n", encoding="utf-8")
    return row


def backfill_metrics(text: str, command: str, tokens: str, duration: str, cost: str = "n/a") -> str:
    """Fill the Tokens, Duration and Cost cells of the last row for `command`
    whose Tokens cell is n/a (the Claude plugin's metrics hook does the same)."""
    lines = text.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if not line.startswith("|") or line.startswith("|--") or "Timestamp" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9 or not cells[1].startswith(command):
            continue
        if cells[7] != "n/a":
            return text
        if cells[6] == "n/a":
            cells[6] = duration
        cells[7] = tokens
        if cells[8] == "n/a":
            cells[8] = cost
        lines[i] = "| " + " | ".join(cells) + " |"
        return "\n".join(lines)
    return text


def is_record_path(rel: str, release: str) -> bool:
    rel = rel.replace("\\", "/")
    return any(rel == f".wire/releases/{release}/{f}" for f in RECORD_FILES)

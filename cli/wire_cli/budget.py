"""The release budget at dispatch and in the lanes (ROADMAP.md phase 5), the
same rules as the Wire mod (packaging/claude-plugin/hooks/register.ts,
hooks/wire/lanes.ts):

- warehouse_spend: none | estimate_required | cap:<amount in USD>
- the spend ledger, `.wire/releases/<release>/lanes/_spend.jsonl`, one line per
  warehouse call or dbt run: {lane, tool, bytes, usd, timestamp}. Written by the
  lane hook (BigQuery and Snowflake MCP calls) and by Wire's dbt tool, always in
  the main repository (WIRE_SPEND_LEDGER), never in a lane's worktree.
- past the cap, warehouse calls are refused and the CLI parks a budget decision
- one dbt build per warehouse project at a time (a lock in .wire/local/)

BigQuery on-demand analysis is priced at USD 6.25 per TiB, as in the mod.
"""

from __future__ import annotations

import fcntl
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

USD_PER_TIB = 6.25
BYTES_RE = re.compile(r'"?(?:totalBytesProcessed|totalBytesBilled|total_bytes_processed|bytes_billed|bytes_processed|bytes_scanned)"?\s*[:=]\s*"?(\d+)')
BUILD_SLOT_WAIT_S = 600


def bytes_to_usd(n: int) -> float:
    return round(n / 2 ** 40 * USD_PER_TIB, 4)


def bytes_billed_of(text: str) -> int:
    """Bytes billed in a tool result's text (BigQuery or Snowflake); the largest figure."""
    nums = [int(m) for m in BYTES_RE.findall(text or "")]
    return max(nums) if nums else 0


def cap_of(warehouse_spend: str | None) -> float | None:
    m = re.match(r"^\s*cap:\s*\$?([0-9]+(?:\.[0-9]+)?)\s*$", str(warehouse_spend or ""))
    return float(m.group(1)) if m else None


def ledger_path(repo: Path, release: str) -> Path:
    return repo / ".wire" / "releases" / release / "lanes" / "_spend.jsonl"


def record(ledger: Path, lane: str, tool: str, n_bytes: int) -> dict:
    row = {"lane": lane, "tool": tool, "bytes": int(n_bytes), "usd": bytes_to_usd(n_bytes),
           "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(row) + "\n")
    return row


def spent(ledger: Path) -> dict:
    """{bytes, usd} so far in a ledger."""
    total_b, total_u = 0, 0.0
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            total_b += int(r.get("bytes") or 0)
            total_u += float(r.get("usd") or 0)
    return {"bytes": total_b, "usd": round(total_u, 4)}


def cap_refusal(usd: float, cap: float, release: str) -> str:
    return (f"budget-blocked: warehouse spend for {release} is ${usd:.2f}, past cap:{cap:g}. "
            "A parked decision (kind budget) is raised in status.md; no further warehouse call runs until the director rules.")


def budget_question(usd: float, cap: float) -> str:
    return f"Warehouse spend is ${usd:.2f} against cap:{cap:g}. Raise the cap, or stop the warehouse work?"


class BuildSlot:
    """One dbt build per warehouse project at a time, across lanes: an exclusive
    lock on .wire/local/build-slot-<project>.lock, waited for up to ten minutes."""

    def __init__(self, repo: Path, project: str, wait_s: int = BUILD_SLOT_WAIT_S):
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", project or "default")
        self.path = repo / ".wire" / "local" / f"build-slot-{safe}.lock"
        self.wait_s = wait_s
        self.fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(self.path, "w")
        deadline = time.time() + self.wait_s
        while True:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.time() >= deadline:
                    self.fh.close()
                    self.fh = None
                    raise TimeoutError(f"the build slot for {self.path.stem[len('build-slot-'):]} stayed held for "
                                       f"{self.wait_s // 60} minutes")
                time.sleep(2)

    def __exit__(self, *exc):
        if self.fh:
            fcntl.flock(self.fh, fcntl.LOCK_UN)
            self.fh.close()
        return False

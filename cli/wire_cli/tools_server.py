"""Wire's own tools for the agent, as an MCP server over stdio
(ROADMAP.md phase 3: "Wire inside the agent process").

`wire tools-server --repo <repo>` is started by the agent for each run the
Wire CLI makes (both harnesses), so a step asks Wire for what it would
otherwise read and parse itself, and gets a short answer:

- wire_status   a release's artifact states, runnable set, parked decisions
                and next action, from Studio's resolver (the same answer as
                `wire status`)
- wire_gate     the precondition gate's decision for one command
- wire_lint     the conventions check on files (lint_conventions.py), findings only
- dbt           a dbt command with a compact result: counts by status and the
                failures with their messages, not dbt's full log (the pattern
                dbt's own Wizard measured: about 150 tokens against 1,300)

Under `warehouse_spend: none` (WIRE_LANE_WAREHOUSE_SPEND, set by the CLI for a
lane) the dbt tool refuses commands that query the warehouse.

Built as an MCP server rather than as Rust tools inside the forked agent:
the same tools reach Claude Code and Codex alike, and nothing here has to be
rebased on Codex. The protocol is MCP's JSON-RPC over newline-delimited stdio.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTOCOL = "2025-06-18"
DBT_ALLOWED = ("parse", "compile", "ls", "list", "build", "run", "test", "seed", "snapshot", "show", "debug", "deps")
DBT_QUERIES = ("build", "run", "test", "seed", "snapshot", "show")

TOOLS = [
    {"name": "wire_status", "description": "A Wire release's artifact states, runnable set, parked decisions and next action, computed by Wire's resolver. Prefer this to reading status.md yourself.",
     "inputSchema": {"type": "object", "properties": {"release": {"type": "string", "description": "the release folder under .wire/releases/"}}, "required": ["release"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "wire_gate", "description": "Whether Wire's precondition gate allows a command on a release now, and why not when it refuses.",
     "inputSchema": {"type": "object", "properties": {"release": {"type": "string"}, "command": {"type": "string", "description": "a Wire command name, e.g. dbt-generate"}}, "required": ["release", "command"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "wire_lint", "description": "Wire's naming and style conventions check (dbt, LookML, Cube, Airflow) on files you wrote. Returns findings only.",
     "inputSchema": {"type": "object", "properties": {"paths": {"type": "array", "items": {"type": "string"}, "description": "files, relative to the repository"}}, "required": ["paths"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "dbt", "description": "Run a dbt command in the repository and get a compact result: counts by status and each failure with its message. Use instead of running dbt in the shell.",
     "inputSchema": {"type": "object", "properties": {"args": {"type": "string", "description": "the dbt arguments, e.g. \"build --select stg_orders+\""}}, "required": ["args"]},
     "annotations": {"readOnlyHint": False, "destructiveHint": False}},
]


def text_result(text: str, error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": error}


# ---------------------------------------------------------------- the tools

def wire_status(repo: Path, root: Path, release: str) -> dict:
    from . import framework as fw
    from .orchestrator import read_release
    framework, _split, _rulings, resolve = fw.load_studio(root)
    status, _text, decisions, _rel, problems = read_release(root, repo, release)
    if problems:
        return text_result("status file problems: " + "; ".join(problems), True)
    r = resolve(framework, status, decisions)
    lines = [f"release {release} ({status.get('release_type') or status.get('project_type')})"]
    for g in r["graph"]:
        st = r["states"][g["id"]]
        if st != "not applicable":
            lines.append(f"  {g['id']}: {st}")
    lines.append("runnable now: " + (", ".join(r["order"]) or "nothing"))
    parked = [d for d in (status.get("parked_decisions") or []) if isinstance(d, dict)]
    for d in parked:
        lines.append(f"parked {d.get('id')}: {d.get('question')} ({d.get('artifact')})")
    gate = fw.load_script(root, "wire_gate")
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    nxt = gate.next_action(framework, str(repo), release, split_fm, read_rulings, resolve)
    lines.append(f"next: {nxt.get('next') or nxt.get('kind')} ({nxt.get('reason')})")
    return text_result("\n".join(lines))


def wire_gate(repo: Path, root: Path, release: str, command: str) -> dict:
    from . import framework as fw
    gate = fw.load_script(root, "wire_gate")
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    g = gate.gate(framework, str(repo), release, fw.normalise_command(command), split_fm, read_rulings, resolve)
    return text_result(f"{g['decision']}: {g.get('reason', '')}")


def domain_of(path: str) -> str | None:
    p = path.replace("\\", "/")
    if p.endswith(".lkml"):
        return "lookml"
    if re.search(r"(^|/)(models|snapshots|seeds|macros|tests)/.*\.(sql|ya?ml)$", p):
        return "dbt"
    if re.search(r"(^|/)(cubes?|model/cubes|model/views)/.*\.(ya?ml|js)$", p):
        return "cube"
    if re.search(r"(^|/)dags/.*\.py$", p):
        return "airflow"
    return None


def wire_lint(repo: Path, root: Path, paths: list) -> dict:
    script = root / "scripts" / "lint_conventions.py"
    out = []
    for rel in paths:
        domain = domain_of(rel)
        if not domain:
            out.append(f"{rel}: no convention domain (dbt, LookML, Cube, Airflow files only)")
            continue
        convention = repo / ".wire" / "conventions" / f"{domain}.yml"
        if not convention.is_file():
            convention = root / "conventions" / f"{domain}.yml"
        try:
            proc = subprocess.run([sys.executable, str(script), "--domain", domain, "--convention", str(convention),
                                   "--path", str(repo / rel), "--format", "json"],
                                  capture_output=True, text=True, timeout=60, cwd=str(repo))
            findings = (json.loads(proc.stdout or "{}") or {}).get("findings", [])
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            out.append(f"{rel}: lint did not run ({exc})")
            continue
        if not findings:
            out.append(f"{rel}: clean ({domain})")
        for f in findings[:20]:
            out.append(f"{rel}:{f.get('line', '?')} {f.get('severity', '')} {f.get('rule', '')}: {f.get('message', '')}".strip())
        if len(findings) > 20:
            out.append(f"{rel}: {len(findings) - 20} more")
    return text_result("\n".join(out) or "no files")


def summarise_run_results(path: Path) -> list:
    """Counts by status and the non-passing nodes with their messages."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    counts: dict = {}
    bad = []
    for r in data.get("results") or []:
        st = str(r.get("status"))
        counts[st] = counts.get(st, 0) + 1
        if st not in ("success", "pass"):
            node = str(r.get("unique_id", "?")).split(".", 2)[-1]
            msg = " ".join(str(r.get("message") or "").split())[:240]
            bad.append(f"  {st}: {node}: {msg}")
    head = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    return [f"results: {head or 'none'}"] + bad[:25] + ([f"  ({len(bad) - 25} more)"] if len(bad) > 25 else [])


def dbt_project_name(repo: Path) -> str:
    p = repo / "dbt_project.yml"
    if p.is_file():
        m = re.search(r"^name:\s*['\"]?([A-Za-z0-9_]+)", p.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return "default"


def run_results_bytes(path: Path) -> int:
    """Bytes the warehouse billed for a dbt run (adapter_response, BigQuery and Snowflake)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    total = 0
    for r in data.get("results") or []:
        a = r.get("adapter_response") or {}
        total += int(a.get("bytes_billed") or a.get("bytes_processed") or a.get("bytes_scanned") or 0)
    return total


def dbt(repo: Path, args: str, env: dict) -> dict:
    try:
        argv = shlex.split(args or "")
    except ValueError as exc:
        return text_result(f"could not read the arguments: {exc}", True)
    if not argv or argv[0] not in DBT_ALLOWED:
        return text_result(f"dbt {argv[0] if argv else ''}: not offered here (allowed: {', '.join(DBT_ALLOWED)})", True)
    from . import budget
    spend_setting = (env.get("WIRE_LANE_WAREHOUSE_SPEND") or "").strip()
    if argv[0] in DBT_QUERIES and spend_setting == "none":
        return text_result(f"budget-blocked: warehouse_spend: none. dbt {argv[0]} queries the warehouse; "
                           "change the budget in status.md, or report it as budget-blocked.", True)
    cap = budget.cap_of(spend_setting)
    ledger = Path(env["WIRE_SPEND_LEDGER"]) if env.get("WIRE_SPEND_LEDGER") else None
    if argv[0] in DBT_QUERIES and cap is not None and ledger is not None:
        usd = budget.spent(ledger)["usd"]
        if usd > cap:
            return text_result(budget.cap_refusal(usd, cap, env.get("WIRE_LANE_RELEASE", "the release")), True)
    target = repo / "target" / "run_results.json"
    before = target.stat().st_mtime if target.is_file() else None
    project = dbt_project_name(repo)
    main_repo = ledger.parents[4] if ledger is not None else repo
    try:
        if argv[0] in DBT_QUERIES:
            # rule 2: one build per warehouse project at a time, across lanes
            with budget.BuildSlot(main_repo, project):
                proc = subprocess.run(["dbt", *argv], capture_output=True, text=True, cwd=str(repo), env=env, timeout=3600)
        else:
            proc = subprocess.run(["dbt", *argv], capture_output=True, text=True, cwd=str(repo), env=env, timeout=3600)
    except FileNotFoundError:
        return text_result("dbt is not installed on this machine's PATH", True)
    except subprocess.TimeoutExpired:
        return text_result("dbt did not finish within an hour", True)
    except TimeoutError as exc:
        return text_result(f"Wire rule 2 (one build per project): {exc}. Report the contention.", True)
    if argv[0] in DBT_QUERIES and ledger is not None and target.is_file() and target.stat().st_mtime != before:
        n = run_results_bytes(target)
        if n:
            budget.record(ledger, env.get("WIRE_LANE_LABEL", "dbt"), f"dbt {argv[0]}", n)
    lines = [f"dbt {' '.join(argv)}: exit {proc.returncode}"]
    if target.is_file() and target.stat().st_mtime != before:
        lines += summarise_run_results(target)
    if argv[0] in ("ls", "list") and proc.returncode == 0:
        nodes = [l for l in proc.stdout.splitlines() if l.strip() and not re.match(r"^\d\d:\d\d:\d\d", l)]
        lines += nodes[:200] + ([f"({len(nodes) - 200} more)"] if len(nodes) > 200 else [])
    if proc.returncode != 0:
        tail = [l for l in (proc.stdout + "\n" + proc.stderr).splitlines() if re.search(r"error|Error|ERROR|fail", l)][-15:]
        lines += tail
    return text_result("\n".join(lines), proc.returncode != 0)


# ---------------------------------------------------------------- the protocol

def handle(msg: dict, repo: Path, root: Path, env: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # a notification
    if method == "initialize":
        from . import __version__
        requested = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
        result = {"protocolVersion": requested, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "wire", "version": __version__}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        p = msg.get("params") or {}
        name, a = p.get("name"), p.get("arguments") or {}
        try:
            if name == "wire_status":
                result = wire_status(repo, root, str(a.get("release", "")))
            elif name == "wire_gate":
                result = wire_gate(repo, root, str(a.get("release", "")), str(a.get("command", "")))
            elif name == "wire_lint":
                result = wire_lint(repo, root, list(a.get("paths") or []))
            elif name == "dbt":
                result = dbt(repo, str(a.get("args", "")), env)
            else:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
        except Exception as exc:  # noqa: BLE001 - a tool failure is a result, never a dead server
            result = text_result(f"{name} failed: {exc}", True)
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method {method} not found"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def serve(repo: Path, root: Path, env: dict | None = None, stdin=None, stdout=None) -> int:
    env = dict(os.environ if env is None else env)
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for raw in stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        reply = handle(msg, repo, root, env)
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()
    return 0

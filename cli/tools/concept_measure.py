#!/usr/bin/env python3
"""Measure one leg of the 5.0 concept run (wire#408 item 5). Deterministic.

    concept_measure.py --repo <copy> --release <release> --task a|b --leg <name> \
        [--reference <path>] [--base <git ref>] [--out <json>]

Reads what the leg left behind and prints one JSON object:

  record      the last log row for the task's command (result, tokens, duration,
              harness and model from the detail), the status outcome written,
              status_file problems, hook refusals counted from the lane log
  output      task a: the data model specification (bytes, Grain lines, Mermaid
              erDiagram present, model names found) and overlap with the reference
              specification's model names; task b: SQL files written, model names,
              overlap with the reference model list, lint_conventions findings
              (dbt domain, --new-project), hooks' PostToolUse blocks (lint notes)

Nothing here calls a model. Overlap is a name-level measure (what the leg chose
to build against what the engagement built), not a quality judgement.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WIRE = HERE.parents[2]
MODEL_RE = re.compile(r"\b((?:base|stg|int|wh)_[a-z0-9]+(?:_[a-z0-9]+)*)\b")
TASKS = {
    "a": {"command": "/wire:data_model-generate", "artifact": "data_model", "action": "generate"},
    "b": {"command": "/wire:dbt-generate", "artifact": "dbt", "action": "generate"},
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True).stdout


def last_row(log_text: str, command: str) -> dict | None:
    for line in reversed(log_text.split("\n")):
        if line.startswith("| 20") and f"| {command}" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 9:
                return {"timestamp": cells[0], "command": cells[1], "result": cells[2], "detail": cells[3],
                        "by": cells[4], "session": cells[5], "duration": cells[6], "tokens": cells[7], "cost": cells[8]}
    return None


def status_outcome(status_text: str, artifact: str, action: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(artifact)}:\s*\{{(.*?)\}}", status_text, re.M)
    if m:
        mm = re.search(rf"\b{action}:\s*([^,}}\s]+)", m.group(1))
        return mm.group(1) if mm else None
    m = re.search(rf"^\s*{re.escape(artifact)}:\s*$((?:\n\s+\S.*)+)", status_text, re.M)
    if m:
        mm = re.search(rf"^\s+{action}:\s*(\S+)", m.group(1), re.M)
        return mm.group(1) if mm else None
    return None


def hook_counts(lane_log_dir: Path, label: str) -> dict:
    out = {"pre_deny": 0, "post_block": 0, "calls": 0, "deny_reasons": []}
    candidates = sorted(lane_log_dir.glob(f"{label}-*.hooks.jsonl")) or [lane_log_dir / f"{label}.hooks.jsonl"]
    p = candidates[-1]
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").split("\n"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        out["calls"] += 1
        if e.get("decision") == "deny":
            out["pre_deny"] += 1
            if e.get("reason"):
                out["deny_reasons"].append((e.get("reason", "")[:160], e.get("command", "")[:120]))
        if e.get("decision") == "block":
            out["post_block"] += 1
    return out


def names_in(text: str) -> set:
    return set(MODEL_RE.findall(text))


def measure_a(repo: Path, release: str, reference: Path | None) -> dict:
    spec = repo / ".wire" / "releases" / release / "design" / "data_model_specification.md"
    out = {"file": str(spec.relative_to(repo)), "present": spec.is_file()}
    if not spec.is_file():
        candidates = list((repo / ".wire" / "releases" / release / "design").glob("*.md")) if (repo / ".wire" / "releases" / release / "design").is_dir() else []
        out["design_files"] = [c.name for c in candidates]
        return out
    text = spec.read_text(encoding="utf-8", errors="replace")
    names = names_in(text)
    out.update({"bytes": len(text), "grain_lines": len(re.findall(r"^\s*(?:\*\*)?Grain(?:\*\*)?:", text, re.M)),
                "er_diagram": "erDiagram" in text, "model_names": sorted(names), "model_count": len(names)})
    if reference and reference.is_file():
        ref = names_in(reference.read_text(encoding="utf-8", errors="replace"))
        out["reference_model_count"] = len(ref)
        out["overlap"] = sorted(names & ref)
        out["overlap_ratio_of_reference"] = round(len(names & ref) / len(ref), 2) if ref else None
    return out


def measure_b(repo: Path, release: str, reference: Path | None, base: str) -> dict:
    changed = []
    if base:
        for l in git(repo, "diff", "--name-status", f"{base}...HEAD").split("\n"):
            parts = l.split("\t")
            if len(parts) >= 2 and parts[0][:1] in ("A", "M", "R"):
                changed.append(parts[-1].strip())
    # Models in the project's models/ tree, or under the release's artifacts (where a
    # lane that could not write models/ put them).
    def is_model(p: str) -> bool:
        return (p.startswith("models/") or "/artifacts/dbt/" in p) and ".wire/local" not in p
    sql = sorted(p for p in changed if is_model(p) and p.endswith(".sql"))
    yml = sorted(p for p in changed if is_model(p) and p.endswith((".yml", ".yaml")))
    names = {Path(p).stem for p in sql}
    in_project = sum(1 for p in sql if p.startswith("models/"))
    out = {"sql_files": sql, "yml_files": yml, "model_names": sorted(names), "model_count": len(names),
           "in_project_models_tree": in_project, "tests_added": sorted(p for p in changed if p.startswith("tests/"))}
    if reference and reference.is_file():
        ref = names_in(reference.read_text(encoding="utf-8", errors="replace"))
        out["reference_model_count"] = len(ref)
        out["overlap"] = sorted(names & ref)
        out["overlap_ratio_of_reference"] = round(len(names & ref) / len(ref), 2) if ref else None
    lint = WIRE / "scripts" / "lint_conventions.py"
    conv = repo / ".wire" / "conventions" / "dbt.yml"
    if not conv.is_file():
        conv = WIRE / "conventions" / "dbt.yml"
    findings = {"errors": 0, "warnings": 0, "by_rule": {}}
    for f in sql + yml:
        proc = subprocess.run([sys.executable, str(lint), "--domain", "dbt", "--convention", str(conv), "--path", f,
                               "--format", "json", "--new-project"], cwd=str(repo), capture_output=True, text=True)
        try:
            rep = json.loads(proc.stdout or "{}")
        except ValueError:
            continue
        findings["errors"] += int(rep.get("errors", 0))
        findings["warnings"] += int(rep.get("warnings", 0))
        for fd in rep.get("findings", []):
            findings["by_rule"][fd.get("rule", "?")] = findings["by_rule"].get(fd.get("rule", "?"), 0) + 1
    out["lint"] = findings
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--release", required=True)
    ap.add_argument("--task", required=True, choices=sorted(TASKS))
    ap.add_argument("--leg", required=True)
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--base", help="git ref the leg started from (task b: the files it added)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    task = TASKS[args.task]
    repo = args.repo.resolve()
    rel_dir = repo / ".wire" / "releases" / args.release
    log = (rel_dir / "execution_log.md").read_text(encoding="utf-8", errors="replace") if (rel_dir / "execution_log.md").is_file() else ""
    status = (rel_dir / "status.md").read_text(encoding="utf-8", errors="replace")
    problems = subprocess.run([sys.executable, str(WIRE / "scripts" / "status_file.py"), "check", str(rel_dir)],
                              capture_output=True, text=True)
    row = last_row(log, task["command"])
    record = {
        "log_row": row,
        "status_outcome": status_outcome(status, task["artifact"], task["action"]),
        "status_file_ok": problems.returncode == 0,
        "hooks": hook_counts(repo / ".wire" / "local" / "lane-logs", task["artifact"]),
        "head": git(repo, "rev-parse", "--short", "HEAD").strip(),
        "merge_commits": len([l for l in git(repo, "log", "--merges", "--format=%s", "-5").split("\n") if "wire: merge lane" in l]),
    }
    output = measure_a(repo, args.release, args.reference) if args.task == "a" else measure_b(repo, args.release, args.reference, args.base or "")
    result = {"leg": args.leg, "task": args.task, "command": task["command"], "record": record, "output": output}
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

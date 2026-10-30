#!/usr/bin/env python3
"""Tested-in-dev evidence for a branch's changed files (wire#380, C5).

Plain script, no AI call, no cloud call. The command spec
(specs/utils/dev_test_evidence.md) gathers the inputs: the PR-head copy of
each changed file, the copy deployed to dev (fetched to a scratch folder),
the upload time, the last parse time and any import error, and the DAG runs
after the upload (from Cloud Logging or the Airflow API). This script turns
them into a verdict per file and overall: yes, partially or no, each with
its reasons.

Input JSON:
  {"environment": "dev",
   "files": [{"path": "dags/orders_load.py", "kind": "dag" | "support",
              "dag_ids": ["orders_load"],        # kind dag
              "used_by": ["orders_load"],        # kind support: DAGs that read it
              "head_path": "head/dags/orders_load.py",  # or head_sha256
              "dev_path": "dev/dags/orders_load.py",    # or dev_sha256; null: not in dev
              "uploaded_at": "2026-10-20T10:00:00Z",
              "parse": {"last_parsed_at": "...", "import_error": null}}],
   "runs": [{"dag_id": "orders_load", "run_id": "...", "state": "success",
             "start": "...", "tasks": [{"task_id": "load", "map_index": 0,
                                         "state": "success"}]}]}

head_path and dev_path are read relative to the input file. Their line
endings are normalised (CRLF and CR to LF) before hashing, so a copy made on
another system still matches. A precomputed *_sha256 must be of the
normalised text.

Per file, in order:
  no         the dev copy is missing or differs from the PR head; an import
             error is recorded; the latest run after the upload failed, or
             a task in it failed.
  partially  no parse recorded after the upload; no run after the upload; a
             run still going; a task instance skipped or not run; no task
             records; a support file with no DAG named that uses it.
  yes        none of the above: the dev copy is the PR head, it parsed after
             the upload, and the latest run after the upload succeeded with
             every task instance, mapped ones included, in success.
Overall: no if any file is no; partially if any file is partially; else yes.

Usage:
  python3 dev_test_evidence.py <input.json> [--format json|markdown]
Exit code: 0 yes, 1 partially or no (the verdict is in the output either
way; the exit code is for scripts).
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

ORDER = {"yes": 0, "partially": 1, "no": 2}
FAILED_TASK_STATES = {"failed", "upstream_failed"}
RUNNING_STATES = {"running", "queued", "scheduled", "restarting", "up_for_retry", "deferred"}


def normalised_sha256(path):
    with open(path, "rb") as fh:
        data = fh.read()
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def ts(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def worst(verdicts):
    return max(verdicts, key=lambda v: ORDER[v]) if verdicts else "yes"


def _sha(entry, which, base):
    if entry.get(f"{which}_sha256"):
        return entry[f"{which}_sha256"]
    rel = entry.get(f"{which}_path")
    if not rel:
        return None
    path = rel if os.path.isabs(rel) else os.path.join(base, rel)
    return normalised_sha256(path) if os.path.isfile(path) else None


def run_verdict(dag_id, runs, uploaded):
    """The verdict and reason from a DAG's latest run after the upload."""
    after = [r for r in runs if r.get("dag_id") == dag_id
             and (uploaded is None or (ts(r.get("start")) and ts(r.get("start")) >= uploaded))]
    if not after:
        return "partially", f"{dag_id}: no run after the upload"
    run = max(after, key=lambda r: ts(r.get("start")))
    rid, state = run.get("run_id", "?"), run.get("state")
    tasks = run.get("tasks") or []
    failed = [t for t in tasks if t.get("state") in FAILED_TASK_STATES]
    if state == "failed" or failed:
        names = ", ".join(_task_name(t) for t in failed) or "no task named"
        return "no", f"{dag_id}: run {rid} failed ({names})"
    if state in RUNNING_STATES:
        return "partially", f"{dag_id}: run {rid} is still {state}"
    if state != "success":
        return "partially", f"{dag_id}: run {rid} ended {state or 'with no state'}"
    if not tasks:
        return "partially", f"{dag_id}: run {rid} succeeded but no task records were given"
    not_done = [t for t in tasks if t.get("state") != "success"]
    mapped = sum(1 for t in tasks if t.get("map_index") is not None and t["map_index"] >= 0)
    if not_done:
        names = ", ".join(f"{_task_name(t)} {t.get('state') or 'not run'}" for t in not_done)
        return "partially", f"{dag_id}: run {rid} succeeded but {len(not_done)} task instance(s) did not: {names}"
    return "yes", f"{dag_id}: run {rid} succeeded, {len(tasks)} task instance(s) ({mapped} mapped) all success"


def _task_name(t):
    mi = t.get("map_index")
    return f"{t.get('task_id')}[{mi}]" if mi is not None and mi >= 0 else str(t.get("task_id"))


def file_verdict(entry, runs, base):
    reasons, verdicts = [], []
    head, dev = _sha(entry, "head", base), _sha(entry, "dev", base)
    if dev is None:
        return {"file": entry["path"], "verdict": "no", "reasons": ["not found in dev"]}
    if head is None:
        return {"file": entry["path"], "verdict": "no", "reasons": ["PR-head copy not given"]}
    if head != dev:
        return {"file": entry["path"], "verdict": "no", "reasons": ["dev copy differs from the PR head"]}
    reasons.append("dev copy matches the PR head")
    uploaded = ts(entry.get("uploaded_at"))
    if uploaded is None:
        verdicts.append("partially")
        reasons.append("upload time unknown")

    kind = entry.get("kind", "dag")
    if kind == "dag":
        parse = entry.get("parse") or {}
        if parse.get("import_error"):
            return {"file": entry["path"], "verdict": "no",
                    "reasons": reasons + [f"import error: {parse['import_error']}"]}
        parsed = ts(parse.get("last_parsed_at"))
        if parsed is None or (uploaded and parsed < uploaded):
            verdicts.append("partially")
            reasons.append("no parse recorded after the upload")
        else:
            reasons.append("parsed after the upload")
        dag_ids = entry.get("dag_ids") or []
        if not dag_ids:
            verdicts.append("partially")
            reasons.append("no DAG id given for this file")
    else:
        dag_ids = entry.get("used_by") or []
        if not dag_ids:
            verdicts.append("partially")
            reasons.append("no DAG named that uses this file")
    for dag_id in dag_ids:
        v, why = run_verdict(dag_id, runs, uploaded)
        verdicts.append(v)
        reasons.append(why)
    return {"file": entry["path"], "verdict": worst(verdicts), "reasons": reasons}


def evaluate(doc, base):
    runs = doc.get("runs") or []
    files = [file_verdict(f, runs, base) for f in doc.get("files") or []]
    overall = worst([f["verdict"] for f in files]) if files else "no"
    return {"environment": doc.get("environment"), "overall": overall, "files": files}


def markdown(result):
    lines = [f"**Tested in dev ({result.get('environment') or 'dev'}): {result['overall']}**", "",
             "| File | Tested in dev | Evidence |", "|---|---|---|"]
    for f in result["files"]:
        lines.append(f"| `{f['file']}` | {f['verdict']} | {'; '.join(f['reasons'])} |")
    if not result["files"]:
        lines.append("| (no changed files given) | no | |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = ap.parse_args()
    with open(args.input) as fh:
        doc = json.load(fh)
    result = evaluate(doc, os.path.dirname(os.path.abspath(args.input)))
    print(json.dumps(result, indent=2) if args.format == "json" else markdown(result))
    return 0 if result["overall"] == "yes" else 1


if __name__ == "__main__":
    sys.exit(main())

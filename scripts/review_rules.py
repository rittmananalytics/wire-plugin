#!/usr/bin/env python3
"""Review rules for a pull request (wire#380, C6).

Plain script, no AI call. Turns a branch's rule findings and a ticket's
requirements into the two tables a PR body and a review carry:

  Rule findings   Each finding is `fixed`, `justified` (with a reason) or
                  `acknowledged`. A finding with no disposition, or justified
                  with no reason, is `open`. Findings never block: the review
                  lists them and the reviewer decides.
  Requirements    Each requirement is `met`, `not met` or `can't tell`, with
                  evidence. `met` with no evidence becomes `can't tell`. A
                  `not met` requirement is a deviation and is raised as a
                  question to the ticket owner, never decided by the script.

Input JSON:
  {"findings": [{"rule": "AF-005", "file": "dags/x.py", "line": 14,
                 "message": "...", "disposition": "justified", "reason": "..."}],
   "requirements": [{"id": "R1", "text": "...", "status": "met",
                     "evidence": "run manual__2026-10-20 succeeded"}]}

Usage:
  python3 review_rules.py <input.json> [--format json|markdown]
Exit code: always 0. Nothing here blocks a merge.
"""
import argparse
import json
import sys

DISPOSITIONS = ("fixed", "justified", "acknowledged")
STATUSES = ("met", "not met", "can't tell")


def classify_finding(f):
    disposition = str(f.get("disposition") or "").strip().lower()
    reason = str(f.get("reason") or "").strip()
    note = None
    if disposition not in DISPOSITIONS:
        disposition, note = "open", "needs a disposition: fixed, justified or acknowledged"
    elif disposition == "justified" and not reason:
        disposition, note = "open", "justified needs a reason"
    out = {"rule": f.get("rule"), "file": f.get("file"), "line": f.get("line"),
           "disposition": disposition, "reason": reason or None}
    if note:
        out["note"] = note
    return out


def classify_requirement(r):
    status = str(r.get("status") or "").strip().lower().replace("cant", "can't")
    evidence = str(r.get("evidence") or "").strip()
    note = None
    if status not in STATUSES:
        status, note = "can't tell", "no status given"
    elif status == "met" and not evidence:
        status, note = "can't tell", "met needs evidence"
    out = {"id": r.get("id"), "text": r.get("text", ""), "status": status, "evidence": evidence or None}
    if note:
        out["note"] = note
    return out


def evaluate(doc):
    findings = [classify_finding(f) for f in doc.get("findings") or []]
    requirements = [classify_requirement(r) for r in doc.get("requirements") or []]
    questions = [
        f"{r['id']} is not met ({r['evidence'] or 'no evidence given'}). "
        "Is this a deviation the ticket owner accepts, or should the change meet it?"
        for r in requirements if r["status"] == "not met"
    ]
    counts = {d: sum(1 for f in findings if f["disposition"] == d) for d in DISPOSITIONS + ("open",)}
    req_counts = {s: sum(1 for r in requirements if r["status"] == s) for s in STATUSES}
    return {"blocking": False, "findings": findings, "finding_counts": counts,
            "requirements": requirements, "requirement_counts": req_counts, "questions": questions}


def markdown(result):
    lines = ["### Rule findings (not blocking)", ""]
    if result["findings"]:
        lines += ["| Rule | Where | Disposition | Reason |", "|---|---|---|---|"]
        for f in result["findings"]:
            where = f"`{f['file']}`" + (f":{f['line']}" if f.get("line") else "")
            lines.append(f"| {f['rule']} | {where} | {f['disposition']} | {f.get('reason') or f.get('note') or ''} |")
    else:
        lines.append("No rule findings.")
    lines += ["", "### Requirements", ""]
    if result["requirements"]:
        lines += ["| Id | Requirement | Status | Evidence |", "|---|---|---|---|"]
        for r in result["requirements"]:
            lines.append(f"| {r['id']} | {r['text']} | {r['status']} | {r.get('evidence') or r.get('note') or ''} |")
    else:
        lines.append("No requirements given.")
    if result["questions"]:
        lines += ["", "### Questions for the ticket owner", ""]
        lines += [f"- {q}" for q in result["questions"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = ap.parse_args()
    with open(args.input) as fh:
        result = evaluate(json.load(fh))
    print(json.dumps(result, indent=2) if args.format == "json" else markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

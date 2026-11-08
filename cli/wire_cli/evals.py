"""`wire eval`: the same cases on any harness and model, graded without a model
(ROADMAP.md phase 6). The results gate model-routing.yaml: a model is routed
to a tier only after it has passed the suite.

A suite is YAML (wire/cli/evals/<name>.yaml):

    name: core
    fixture: tests/studio/fixture/repo     # under the framework root; copied, git-initialised
    release: 02-data-foundation
    cases:
      - id: status-runnable
        kind: exec                         # exec | typed | run
        prompt: "..."                      # exec: {release} is filled in
        command: requirements-validate     # typed
        expect:
          exit_in: [0]
          final_contains_all: [semantic_layer, orchestration]
          final_contains_any: [data_quality]
          final_regex: "(?i)^no\\b"
          final_not_contains: [status.md written]
          ran_line: true                   # typed: the reply ends with Ran:/Not run:
          log_rows_added_min: 1            # typed, run: rows added to execution_log.md
          no_rule_breaks: true             # run: no lane parked for rule 3 or rule 6
          status_changed: true             # run: status.md moved, or a decision parked
          final_not_regex: "..."           # the reply must not match
          final_order: [first, second]     # each appears, in this order (first occurrences)
          file_regex:                      # files the run wrote: each pattern found in the file
            models/staging/x.sql: ["order_pk"]
          files_absent: ["models/**/int_*__*.sql"]  # globs that must match no file after the run
          status_unchanged: true           # status.md is as it was before the run
          status_if_changed_not_regex: "..."  # if the run changed status.md, it must not match
        tier: judgment                     # the workload tier the case stands for (the tiers suite)
        files:                             # written into the fixture copy before the run
          docs/planted.md: "..."

`{release}` and `{framework}` (the framework root) are filled in prompts and
planted files. Every check is a plain comparison; a case passes when all of
its checks do.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def load_suite(path: Path) -> dict:
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("cases"):
        raise ValueError(f"{path} has no cases")
    return data


def prepare_fixture(root: Path, suite: dict, into: Path) -> Path:
    src = (root / suite["fixture"]).resolve()
    repo = into / "repo"
    shutil.copytree(src, repo, ignore=shutil.ignore_patterns(".git", "worktrees", "lane-logs"))
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.email=eval@wire", "-c", "user.name=Wire eval", "commit", "-qm", "fixture"]):
        subprocess.run(cmd, cwd=str(repo), capture_output=True)
    return repo


def log_rows(repo: Path, release: str) -> int:
    p = repo / ".wire" / "releases" / release / "execution_log.md"
    if not p.is_file():
        return 0
    return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if re.match(r"^\|\s*\d{4}-\d\d-\d\d", l))


def grade(expect: dict, outcome: dict) -> list:
    """The failed checks, as short strings; [] is a pass."""
    fails = []
    final = outcome.get("final", "") or ""
    low = final.lower()
    if "exit_in" in expect and outcome.get("exit") not in expect["exit_in"]:
        fails.append(f"exit {outcome.get('exit')} not in {expect['exit_in']}")
    for s in expect.get("final_contains_all", []):
        if str(s).lower() not in low:
            fails.append(f"reply lacks {s!r}")
    anyof = expect.get("final_contains_any", [])
    if anyof and not any(str(s).lower() in low for s in anyof):
        fails.append(f"reply has none of {anyof}")
    for s in expect.get("final_not_contains", []):
        if str(s).lower() in low:
            fails.append(f"reply has {s!r}")
    if expect.get("final_regex") and not re.search(expect["final_regex"], final, re.M):
        fails.append(f"reply does not match {expect['final_regex']!r}")
    if expect.get("ran_line") and not outcome.get("ran_line"):
        fails.append("no Ran: line")
    if "log_rows_added_min" in expect and outcome.get("log_rows_added", 0) < expect["log_rows_added_min"]:
        fails.append(f"{outcome.get('log_rows_added', 0)} log rows added, wanted {expect['log_rows_added_min']}")
    if expect.get("no_rule_breaks") and outcome.get("rule_breaks"):
        fails.append(f"rule breaks: {', '.join(outcome['rule_breaks'])}")
    if expect.get("status_changed") and not outcome.get("status_changed"):
        fails.append("status.md did not change")
    if expect.get("final_not_regex") and re.search(expect["final_not_regex"], final, re.M):
        fails.append(f"reply matches {expect['final_not_regex']!r}")
    order = expect.get("final_order") or []
    if order:
        at = [low.find(str(x).lower()) for x in order]
        if any(i < 0 for i in at):
            fails.append(f"reply lacks one of {order}")
        elif at != sorted(at):
            fails.append(f"reply has {order} out of order")
    if expect.get("status_unchanged") and outcome.get("status_changed"):
        fails.append("status.md was changed")
    pat = expect.get("status_if_changed_not_regex")
    if pat and outcome.get("status_changed") and re.search(pat, outcome.get("status_after") or "", re.M):
        fails.append(f"status.md was changed and matches {pat!r}")
    for pattern, hits in (outcome.get("present") or {}).items():
        if hits:
            fails.append(f"{pattern} should match no file, matched {', '.join(hits)}")
    files = outcome.get("files") or {}
    for path, patterns in (expect.get("file_regex") or {}).items():
        text = files.get(path)
        if text is None:
            fails.append(f"{path} not written")
            continue
        for pat in patterns:
            if not re.search(pat, text, re.M | re.I):
                fails.append(f"{path} does not match {pat!r}")
    return fails


def fill(text: str, release: str, root: Path) -> str:
    return text.replace("{release}", release).replace("{framework}", str(root))


class Capture:
    def __init__(self):
        self.lines = []

    def __call__(self, *a):
        self.lines.append(" ".join(str(x) for x in a))

    @property
    def text(self):
        return "\n".join(self.lines)


def run_case(case: dict, repo: Path, release: str, flags: list, env: dict, root: Path | None = None) -> dict:
    from .main import main
    kind = case.get("kind", "exec")
    root = root or Path(__file__).resolve().parents[2]
    for rel, content in (case.get("files") or {}).items():
        target = repo / fill(rel, release, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fill(str(content), release, root), encoding="utf-8")
    before_rows = log_rows(repo, release)
    status_p = repo / ".wire" / "releases" / release / "status.md"
    before_status = status_p.read_text(encoding="utf-8") if status_p.is_file() else ""
    cap = Capture()
    t0 = time.time()
    run_env = dict(env)
    run_env.update({"WIRE_NO_BANNER": "1", "WIRE_TELEMETRY": "false", "WIRE_COMMIT_RECORD": "false"})
    if kind == "exec":
        argv = ["exec", fill(case["prompt"], release, root), "--repo", str(repo), "--json"] + flags
    elif kind == "typed":
        argv = [case["command"], release, "--repo", str(repo)] + flags
    elif kind == "run":
        argv = ["run", release, "--repo", str(repo), "--yes", "--once", "--no-interaction", "--take-over"] + flags
    else:
        raise ValueError(f"unknown case kind {kind}")
    rc = main(argv, out=cap, env=run_env)
    elapsed = time.time() - t0
    text = cap.text
    final, tokens = text, 0
    if kind == "exec":
        try:
            data = json.loads(text[text.index("{"):])
            final = data.get("final_message") or ""
            u = data.get("usage") or {}
            tokens = int(u.get("input_tokens") or 0) + int(u.get("output_tokens") or 0)
        except ValueError:
            pass
    else:
        m = re.search(r"Metrics filled in: (\d+) tokens", text)
        tokens = int(m.group(1)) if m else 0
    breaks = re.findall(r"(single writer|tree ownership)", text)
    after_status = status_p.read_text(encoding="utf-8") if status_p.is_file() else ""
    files = {}
    for rel in ((case.get("expect") or {}).get("file_regex") or {}):
        p = repo / fill(rel, release, root)
        if p.is_file():
            files[rel] = p.read_text(encoding="utf-8", errors="replace")
    present = {}
    for pattern in ((case.get("expect") or {}).get("files_absent") or []):
        present[pattern] = sorted(str(q.relative_to(repo)) for q in repo.glob(fill(pattern, release, root)))
    return {"files": files, "present": present, "exit": rc, "final": final, "tokens": tokens, "seconds": round(elapsed, 1),
            "ran_line": bool(re.search(r"(^|\n)\s*\**(Ran|Not run):", text)),
            "log_rows_added": log_rows(repo, release) - before_rows,
            "rule_breaks": sorted(set(breaks)), "status_changed": after_status != before_status,
            "status_after": after_status}


def run_suite(root: Path, suite_path: Path, flags: list, env: dict, out=print, only: list | None = None) -> dict:
    suite = load_suite(suite_path)
    release = suite["release"]
    results = []
    with tempfile.TemporaryDirectory() as td:
        for case in suite["cases"]:
            if only and case["id"] not in only:
                continue
            # a fresh copy per case: cases never see each other's writes
            case_dir = Path(td) / case["id"]
            case_dir.mkdir()
            repo = prepare_fixture(root, suite, case_dir)
            outcome = run_case(case, repo, release, flags, env, root)
            fails = grade(case.get("expect") or {}, outcome)
            results.append({"id": case["id"], "kind": case.get("kind", "exec"), "tier": case.get("tier"), "pass": not fails, "fails": fails,
                            "tokens": outcome["tokens"], "seconds": outcome["seconds"], "exit": outcome["exit"],
                            "final": (outcome["final"] or "")[:1000]})
            out(f"  {case['id']:<28} {'pass' if not fails else 'FAIL'}  {outcome['seconds']:>6}s  {outcome['tokens']:>8} tokens"
                + ("" if not fails else "  " + "; ".join(fails)))
    return {"suite": suite.get("name", suite_path.stem), "when": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
            "flags": flags, "results": results, "passed": sum(1 for r in results if r["pass"]), "total": len(results)}


def tier_summary(report: dict) -> dict:
    """tier -> (passed, total), for the cases that name a tier."""
    out: dict = {}
    for r in report["results"]:
        if r.get("tier"):
            p, t = out.get(r["tier"], (0, 0))
            out[r["tier"]] = (p + (1 if r["pass"] else 0), t + 1)
    return out


def table_row(report: dict) -> str:
    who = " ".join(report["flags"]) or "defaults"
    cells = " | ".join(("pass" if r["pass"] else "FAIL") for r in report["results"])
    tokens = sum(r["tokens"] for r in report["results"])
    secs = sum(r["seconds"] for r in report["results"])
    return f"| {report['when']} | {who} | {report['passed']}/{report['total']} | {cells} | {tokens} | {secs:.0f}s |"


def command(root: Path, args, env: dict, out=print) -> int:
    suite_path = Path(args.suite) if args.suite and Path(args.suite).is_file() else \
        Path(__file__).resolve().parents[1] / "evals" / f"{args.suite or 'core'}.yaml"
    if not suite_path.is_file():
        out(f"no suite at {suite_path}")
        return 2
    flags = []
    for key in ("harness", "model", "provider"):
        if getattr(args, key, None):
            flags += [f"--{key}", getattr(args, key)]
    out(f"Eval {suite_path.stem} ({' '.join(flags) or 'defaults'})")
    report = run_suite(root, suite_path, flags, env, out, only=args.case)
    out(f"{report['passed']}/{report['total']} passed")
    if args.record:
        rec_dir = Path(args.record)
        rec_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (rec_dir / f"{report['suite']}-{stamp}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        out(f"Recorded in {rec_dir}; table row: {table_row(report)}")
    return 0 if report["passed"] == report["total"] else 1

#!/usr/bin/env python3
"""wire_checks.py: Wire's checks on one pull request, for CI (wire-hosted-agents
phase B, step 5 of the pods ticket flow).

A plain script, no AI call, no cloud call. It runs the two deterministic
checks Wire already has over the files a pull request adds or changes, and
nothing else, so a pull request never fails on a file it did not touch:

  records       status_file.py on each changed release status.md and ticket
                record (.wire/releases/<release>/iterations/<ticket>.md):
                a key written twice, or YAML that does not parse.
  conventions   lint_conventions.py on each changed file that belongs to a
                domain (dbt, dbtcharts, lookml, cube, airflow, data_apps),
                with the client's .wire/conventions/<domain>.yml as it is on
                the base branch when there is one, else Wire's. Only error
                findings fail. Warnings are listed. A pull request that changes
                .wire/conventions/ is checked against the base branch's rules
                and the change is named in the summary for the reviewer.

A problem already on the base branch does not fail the pull request. In a
file the pull request changed (not added), a finding counts only when it is
on a line the pull request added or changed. A finding with no line counts
only in an added or renamed file. Other findings are listed as warnings
marked "already on the base branch".

Which domain a changed file belongs to:

  dbt         .sql .yml .yaml .csv under models/ snapshots/ seeds/ macros/ of
              a folder holding dbt_project.yml
  dbtcharts   .yml .yaml under charts/ of a dbt project, and dbt_charts.yml
  lookml      any .lkml file
  cube        .yml .yaml under a model/ or schema/ folder whose text has
              `cubes:` or `cube(` (as Wire's lint-on-write hook decides)
  airflow     .py .sql .yml .yaml under a dags/ folder
  data_apps   .js under <data_apps_path>/<slug>/: a folder named data_apps,
              or the path a release status.md (data_apps_path) or
              .wire/engagement/context.md (data_apps: path:) names

A path with a folder lint_conventions.py never walks (target, dbt_packages,
node_modules and the others in its SKIPPED_DIRS) or a folder starting with
"." is in no domain, so installed packages and build output are not checked.

Usage:
  python3 wire_checks.py --repo <client repo> --base <base ref or sha>
      [--json <out.json>] [--summary <out.md>] [--annotations]

--base is the pull request's base (GitHub: github.event.pull_request.base.sha).
The changed files are those between the merge base of --base and HEAD.
--summary appends a Markdown report (GitHub: $GITHUB_STEP_SUMMARY).
--annotations prints GitHub ::error and ::warning lines for each finding.

Exit 0 when nothing fails, 1 when a record problem or a convention error is
found in a changed file, 2 on a usage error or when git cannot give the
changed files. Stdlib plus PyYAML (which both checks need).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRAMEWORK = HERE.parent
CHECK_NAME = "Wire checks"

DBT_DIRS = ("models", "snapshots", "seeds", "macros")
EXT = {
    "dbt": (".sql", ".yml", ".yaml", ".csv"),
    "dbtcharts": (".yml", ".yaml"),
    "lookml": (".lkml",),
    "cube": (".yml", ".yaml"),
    "airflow": (".py", ".sql", ".yml", ".yaml"),
    "data_apps": (".js",),
}


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


# The folders lint_conventions.py's folder walk skips (its SKIPPED_DIRS):
# build output and installed packages, never the project's own code.
SKIPPED_DIRS = {"target", "dbt_packages", "dbt_modules", "node_modules", "logs", "__pycache__"}


def merge_base_of(repo, base):
    return git(["merge-base", base, "HEAD"], repo).strip()


def changed_files(repo, merge_base):
    """{path: status} for paths (relative to the repo, posix, unquoted) added
    ('A'), changed ('M') or renamed or copied ('R') between merge_base and
    HEAD. Deleted files are left out."""
    out = git(["diff", "--name-status", "-z", "--diff-filter=ACMR", merge_base, "HEAD"], repo)
    tokens = out.split("\0")
    files, i = {}, 0
    while i < len(tokens) and tokens[i]:
        status = tokens[i][0]
        if status in "RC":
            files[tokens[i + 2]] = "A" if status == "C" else "R"
            i += 3
        else:
            files[tokens[i + 1]] = status
            i += 2
    return dict(sorted(files.items()))


def changed_lines(repo, merge_base, rel):
    """The line numbers of rel at HEAD that the pull request added or changed."""
    out = git(["diff", "-U0", "--no-color", merge_base, "HEAD", "--", rel], repo)
    lines = set()
    for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", out, re.M):
        start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        lines.update(range(start, start + count))
    return lines


def counts(finding, status, lines):
    """Whether a finding is the pull request's: anywhere in an added file; on an
    added or changed line of a changed file; with no line, in a renamed file."""
    if status == "A":
        return True
    line = finding.get("line")
    if not line:
        return status == "R"
    return line in lines


def _ancestor_with(repo, rel, names):
    """The nearest folder above rel (inside repo) holding one of names, as a
    posix path relative to repo ('' for the root), or None."""
    parts = Path(rel).parts[:-1]
    for i in range(len(parts), -1, -1):
        folder = Path(repo, *parts[:i])
        if any((folder / n).is_file() for n in names):
            return "/".join(parts[:i])
    return None


def data_apps_paths(repo):
    """Where Data Apps live (the data_app generate spec's data_apps_path): any
    path a release status.md or .wire/engagement/context.md names. A folder
    named data_apps counts as well (the default, <bi_project_path>/data_apps)."""
    paths = set()
    wire = Path(repo, ".wire")
    texts = [p.read_text(encoding="utf-8", errors="replace") for p in sorted(wire.glob("releases/*/status.md"))]
    context = wire / "engagement" / "context.md"
    if context.is_file():
        text = context.read_text(encoding="utf-8", errors="replace")
        texts.append(text)
        for m in re.finditer(r"^\s*data_apps:\s*\n\s+path:\s*['\"]?([^'\"#\s]+)", text, re.M):
            paths.add(m.group(1))
    for text in texts:
        for m in re.finditer(r"^\s*data_apps_path:\s*['\"]?([^'\"#\s]+)", text, re.M):
            if m.group(1) not in ("null", "~"):
                paths.add(m.group(1))
    return {p.strip("/") for p in paths if p.strip("/")}


def domain_of(repo, rel, apps_paths=None):
    """The convention domain a changed file belongs to, or None."""
    p = Path(rel)
    name, suffix, parts = p.name, p.suffix.lower(), p.parts
    if any(part.startswith(".") or part in SKIPPED_DIRS for part in parts[:-1]):
        return None
    if suffix == ".lkml":
        return "lookml"
    if name == "dbt_charts.yml":
        return "dbtcharts"
    project = _ancestor_with(repo, rel, ("dbt_project.yml",))
    if project is not None:
        inner = Path(rel).relative_to(project).parts if project else parts
        if inner and inner[0] == "charts" and suffix in EXT["dbtcharts"]:
            return "dbtcharts"
        if inner and inner[0] in DBT_DIRS and suffix in EXT["dbt"]:
            return "dbt"
    if suffix in EXT["cube"] and ({"model", "schema"} & set(parts[:-1])):
        text = Path(repo, rel).read_text(encoding="utf-8", errors="replace")
        if re.search(r"\bcube\s*\(|^\s*cubes:\s*$", text, re.M):
            return "cube"
    if "dags" in parts[:-1] and suffix in EXT["airflow"]:
        return "airflow"
    if suffix in EXT["data_apps"] and len(parts) >= 3:
        folder = "/".join(parts[:-2])
        if parts[-3] == "data_apps" or folder in (apps_paths if apps_paths is not None else data_apps_paths(repo)):
            return "data_apps"
    return None


def is_record(rel):
    """A release status.md or a ticket record: the files status_file.py checks."""
    p = Path(rel)
    if not p.parts or p.parts[0] != ".wire" or p.suffix != ".md":
        return False
    if p.name == "status.md":
        return "engagement" not in p.parts
    return p.parent.name == "iterations" and not p.name.endswith(".execution_log.md")


def convention_for(repo, domain, merge_base=None, workdir=None):
    """(path, client?) of the convention a domain is linted with: the client's
    .wire/conventions/<domain>.yml as it is at merge_base (so a pull request
    cannot change the rules it is checked against), else Wire's. Without
    merge_base, the file in the working tree."""
    rel = f".wire/conventions/{domain}.yml"
    if merge_base is None:
        client = Path(repo, rel)
        if client.is_file():
            return client, True
        return FRAMEWORK / "conventions" / f"{domain}.yml", False
    show = subprocess.run(["git", "show", f"{merge_base}:{rel}"], cwd=repo, capture_output=True, text=True)
    if show.returncode == 0:
        out = Path(workdir or tempfile.mkdtemp(prefix="wire-checks-"), f"{domain}.yml")
        out.write_text(show.stdout, encoding="utf-8")
        return out, True
    return FRAMEWORK / "conventions" / f"{domain}.yml", False


def check_records(repo, files):
    sys.path.insert(0, str(HERE))
    import status_file  # noqa: E402  (beside this script in both layouts)

    problems = []
    for rel in files:
        for p in status_file.check_text(Path(repo, rel).read_text(encoding="utf-8", errors="replace"), rel):
            problems.append({"file": rel, "line": p.get("line"), "first": p.get("first"), "message": p["message"]})
    return problems


def lint(repo, domain, rel, base, convention):
    cmd = [sys.executable, str(HERE / "lint_conventions.py"), "--domain", domain, "--convention", str(convention),
           "--path", str(Path(repo, rel)), "--changed-from", base, "--format", "json"]
    run = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    if run.returncode == 2 or not run.stdout.strip():
        return [{"rule": "lint", "severity": "error", "file": rel, "line": None,
                 "message": f"the {domain} convention lint could not run: {(run.stderr or run.stdout).strip()[:300]}"}]
    report = json.loads(run.stdout)
    out = []
    for f in report.get("findings", []):
        out.append({"rule": f.get("rule"), "severity": f.get("severity"), "file": rel,
                    "line": f.get("line"), "message": f.get("message")})
    return out


def run_checks(repo, base):
    merge_base = merge_base_of(repo, base)
    files = changed_files(repo, merge_base)
    records = [f for f in files if is_record(f)]
    apps_paths = data_apps_paths(repo)
    linted = {}
    for rel in files:
        d = domain_of(repo, rel, apps_paths)
        if d:
            linted.setdefault(d, []).append(rel)
    lines = {rel: changed_lines(repo, merge_base, rel) for rel, st in files.items() if st != "A" and (rel in records or any(rel in v for v in linted.values()))}

    problems, pre_existing = [], []
    for p in check_records(repo, records):
        changed = lines.get(p["file"], set())
        # A key written twice is the pull request's when it wrote either copy.
        ours = counts(p, files[p["file"]], changed) or (p.get("first") in changed)
        (problems if ours else pre_existing).append(p)

    findings, conventions = [], {}
    with tempfile.TemporaryDirectory(prefix="wire-checks-") as workdir:
        for domain, rels in sorted(linted.items()):
            convention, client = convention_for(repo, domain, merge_base, workdir)
            conventions[domain] = "client" if client else "wire"
            for rel in rels:
                for f in lint(repo, domain, rel, base, convention):
                    if f["severity"] == "error" and not counts(f, files[rel], lines.get(rel, set())):
                        f = {**f, "severity": "warning", "pre_existing": True}
                    findings.append(f)
    for p in pre_existing:
        findings.append({"rule": "release_record", "severity": "warning", "file": p["file"], "line": p.get("line"),
                         "message": p["message"], "pre_existing": True})
    errors = [f for f in findings if f["severity"] == "error"]
    return {
        "check": CHECK_NAME,
        "base": base,
        "merge_base": merge_base,
        "changed_files": len(files),
        "records_checked": records,
        "linted": {d: rels for d, rels in sorted(linted.items())},
        "conventions": conventions,
        "conventions_changed": [f for f in files if f.startswith(".wire/conventions/")],
        "record_problems": problems,
        "findings": findings,
        "errors": len(errors) + len(problems),
        "warnings": len(findings) - len(errors),
        "result": "fail" if errors or problems else "pass",
    }


def markdown(report):
    lines = [f"## {CHECK_NAME}: {'failed' if report['result'] == 'fail' else 'passed'}", ""]
    lines.append(f"{report['changed_files']} changed file(s). {len(report['records_checked'])} release record(s) checked. "
                 + (", ".join(f"{len(v)} {d} file(s) ({report['conventions'][d]} conventions)" for d, v in report["linted"].items())
                    or "No file in a convention domain.") )
    if report.get("conventions_changed"):
        lines += ["", "This pull request changes " + ", ".join(report["conventions_changed"])
                  + ". It was checked against the base branch's rules. A reviewer should agree the rule change."]
    if report["record_problems"]:
        lines += ["", "### Release records", "", "| File | Line | Problem |", "|---|---|---|"]
        lines += [f"| {p['file']} | {p.get('line') or ''} | {p['message']} |" for p in report["record_problems"]]
    if report["findings"]:
        lines += ["", "### Conventions", "", "| Severity | Rule | File | Line | Finding |", "|---|---|---|---|---|"]
        for f in sorted(report["findings"], key=lambda f: (f["severity"] != "error", f["file"], f.get("line") or 0)):
            note = " (already on the base branch)" if f.get("pre_existing") else ""
            lines.append(f"| {f['severity']} | {f['rule']} | {f['file']} | {f.get('line') or ''} | {f['message']}{note} |")
    lines += ["", "Errors fail the check. Warnings are for the reviewer."]
    return "\n".join(lines) + "\n"


def annotations(report):
    out = []
    for p in report["record_problems"]:
        out.append(f"::error file={p['file']},line={p.get('line') or 1}::{p['message']}")
    for f in report["findings"]:
        level = "error" if f["severity"] == "error" else "warning"
        out.append(f"::{level} file={f['file']},line={f.get('line') or 1}::[{f['rule']}] {f['message']}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", required=True)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--summary")
    ap.add_argument("--annotations", action="store_true")
    args = ap.parse_args(argv)
    repo = os.path.abspath(args.repo)
    try:
        report = run_checks(repo, args.base)
    except subprocess.CalledProcessError as e:
        print(f"{CHECK_NAME}: git could not give the changed files against {args.base}: {(e.stderr or '').strip()}. "
              "Check out with fetch-depth: 0.", file=sys.stderr)
        return 2
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write(markdown(report))
    if args.annotations:
        print("\n".join(annotations(report)))
    print(markdown(report))
    return 1 if report["result"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())

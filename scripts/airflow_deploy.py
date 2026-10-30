#!/usr/bin/env python3
"""Deploy target check for Airflow DAG files (wire#380, C3).

Plain script, no AI call, no network call except the copy commands `run`
executes. Reads the client's environment file
(.wire/engagement/airflow_environments.yml, schema in
wire/schemas/airflow-environments-schema.md) and decides, file by file,
whether a file may be copied to a target environment.

  check  Allow or refuse each file, with the reason. Exit 1 if any refused.
  plan   Print one copy command per file. Copies nothing. Refuses to plan if
         any file is refused.
  run    Run the plan, one file at a time, only when every file is allowed.
         Stops on the first failed copy. --dry-run prints the plan only.

A deploy never syncs a folder (no rsync) and never deletes.

Usage:
  python3 airflow_deploy.py check <env-file> <target> <file>... [--repo PATH] [--format json]
  python3 airflow_deploy.py plan  <env-file> <target> <file>... [--repo PATH]
  python3 airflow_deploy.py run   <env-file> <target> <file>... [--repo PATH] [--dry-run] [--gcloud BIN]

Files are repo-relative paths. --repo is the repository root (default: the
current directory).
"""
import argparse
import ast
import json
import os
import posixpath
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


def load_env_file(path):
    with open(path) as fh:
        doc = yaml.safe_load(fh) or {}
    if not isinstance(doc, dict) or not isinstance(doc.get("environments"), list) or not doc["environments"]:
        raise ValueError(f"{path}: no environments listed")
    names = [e.get("name") for e in doc["environments"] if isinstance(e, dict)]
    if len(names) != len(set(names)) or None in names:
        raise ValueError(f"{path}: every environment needs a unique name")
    if not isinstance(doc.get("deploy"), dict):
        raise ValueError(f"{path}: no deploy section (deploy.allowed, deploy.forbidden)")
    return doc


def _bucket(env):
    b = str(env.get("bucket") or "").strip()
    return b[5:] if b.startswith("gs://") else b


def _folder(value, default):
    v = str(value if value is not None else default).strip().strip("/")
    return v + "/" if v else ""


def target_refusal(doc, target):
    """Why the target itself is refused, or None."""
    env = next((e for e in doc["environments"] if e.get("name") == target), None)
    if env is None:
        return f"target '{target}' is not an environment in the file"
    deploy = doc.get("deploy") or {}
    if target in (deploy.get("forbidden") or []):
        return f"target '{target}' is in deploy.forbidden"
    if target not in (deploy.get("allowed") or []):
        return f"target '{target}' is not in deploy.allowed"
    if not _bucket(env):
        return f"environment '{target}' has no bucket"
    return None


def path_refusal(path):
    if not path or path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
        return "absolute path; give a path relative to the repo root"
    if ".." in re.split(r"[\\/]", path):
        return "path contains '..'"
    return None


def _protected_match(path, entries):
    for entry in entries or []:
        p = str(entry.get("path") or "")
        if not p:
            continue
        if (p.endswith("/") and path.startswith(p)) or path == p:
            return entry
    return None


def dag_ids_in(text):
    """DAG ids a Python file defines, read with ast. Unparseable: empty."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in ("DAG", "dag"):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    ids.add(node.args[0].value)
                for kw in node.keywords:
                    if kw.arg == "dag_id" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        ids.add(kw.value.value)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
                if name == "dag" and not (isinstance(dec, ast.Call)
                                          and any(kw.arg == "dag_id" for kw in dec.keywords)):
                    ids.add(node.name)
    return ids


def tracked_files(repo):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return {p for p in out.stdout.split("\0") if p}


def check(doc, target, files, repo):
    """One result per file: {file, allowed, reason, destination}."""
    refused_target = target_refusal(doc, target)
    env = next((e for e in doc["environments"] if e.get("name") == target), {})
    repo_root = _folder(env.get("repo_root"), "dags/")
    prefix = _folder(env.get("dags_prefix"), "dags/")
    bucket = _bucket(env)
    protected = doc.get("protected") or {}
    tracked = tracked_files(repo)
    results = []
    for raw in files:
        path = raw.replace("\\", "/")
        reason = path_refusal(raw) or refused_target
        dest = None
        if reason is None:
            path = posixpath.normpath(path)
            if not path.startswith(repo_root):
                reason = f"outside the environment's repo_root '{repo_root}'"
        if reason is None:
            dest = f"gs://{bucket}/{prefix}{path[len(repo_root):]}"
            bucket_path = f"{prefix}{path[len(repo_root):]}"
            hit = _protected_match(path, protected.get("paths")) or \
                _protected_match(bucket_path, protected.get("paths"))
            if hit:
                reason = f"protected path '{hit['path']}': {hit.get('reason', 'no reason given')}"
        full = os.path.join(repo, path)
        if reason is None and not os.path.isfile(full):
            reason = "file does not exist"
        if reason is None and tracked is None:
            reason = "not a git repository; cannot confirm the file is tracked"
        if reason is None and path not in tracked:
            reason = "not tracked by git"
        if reason is None and path.endswith(".py"):
            with open(full, encoding="utf-8") as fh:
                ids = dag_ids_in(fh.read())
            for entry in protected.get("dag_ids") or []:
                if entry.get("dag_id") in ids:
                    reason = f"defines protected DAG '{entry['dag_id']}': {entry.get('reason', 'no reason given')}"
                    break
        results.append({"file": raw, "allowed": reason is None, "reason": reason or "allowed",
                        "destination": dest if reason is None else None})
    return results


def copy_command(gcloud, file, destination):
    return [gcloud, "storage", "cp", file, destination]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["check", "plan", "run"])
    ap.add_argument("env_file")
    ap.add_argument("target")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--dry-run", action="store_true", help="run only: print the plan, copy nothing")
    ap.add_argument("--gcloud", default="gcloud", help="the gcloud binary (tests pass a stand-in)")
    args = ap.parse_args()

    try:
        doc = load_env_file(args.env_file)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    results = check(doc, args.target, args.files, args.repo)
    refused = [r for r in results if not r["allowed"]]

    if args.action == "check":
        if args.format == "json":
            print(json.dumps({"target": args.target, "results": results,
                              "allowed": len(results) - len(refused), "refused": len(refused)}, indent=2))
        else:
            for r in results:
                if r["allowed"]:
                    print(f"  ALLOW   {r['file']} -> {r['destination']}")
                else:
                    print(f"  REFUSE  {r['file']}: {r['reason']}")
            print(f"\n{len(results) - len(refused)} allowed, {len(refused)} refused (target: {args.target})")
        return 1 if refused else 0

    if refused:
        for r in refused:
            print(f"  REFUSE  {r['file']}: {r['reason']}")
        print(f"\nNothing copied: {len(refused)} file(s) refused. Fix or drop them and check again.")
        return 1

    commands = [copy_command(args.gcloud, os.path.join(args.repo, r["file"]) if args.repo != "." else r["file"],
                             r["destination"]) for r in results]
    if args.action == "plan" or args.dry_run:
        for c in commands:
            print(" ".join(c))
        print(f"\n{len(commands)} file(s), one copy each. Nothing deleted, no folder synced."
              + (" Dry run: nothing copied." if args.action == "run" else ""))
        return 0

    for c, r in zip(commands, results):
        proc = subprocess.run(c, capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
            print(f"  FAILED  {r['file']}: {detail}")
            print("Stopped. Files after this one were not copied.")
            return 1
        print(f"  COPIED  {r['file']} -> {r['destination']}")
    print(f"\n{len(commands)} file(s) copied to {args.target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

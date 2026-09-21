#!/usr/bin/env python3
"""
agents_schema_secrets.py — derive the two Agents Schema secrets from a dbt
profile, set them on the GitHub repository, and optionally publish.

The reusable dbt-labs/agents_schema workflows need two repository secrets:

  WAREHOUSE_CREDENTIALS  the destination credentials as YAML (type, project or
                         account, and the key or password)
  DBT_PROFILES_YML       a dbt profiles.yml, only when the dbt job has to build
                         target/manifest.json itself (managed dbt parse)

Both already exist, in a different shape, in the consultant's ~/.dbt/profiles.yml
for the target the release builds with. This script reads that one profile and
target and produces both values, so a consultant who owns the repository does not
have to retype a service-account key into a browser. Three rules hold throughout:

  1. Nothing secret is ever printed or written to a file. Values travel from the
     profile to `gh secret set` on stdin, and to the publish as an environment
     variable of a child process. --dry-run prints only names, shapes and lengths.
  2. DBT_PROFILES_YML is the ONE profile and the ONE target, never the whole file.
     A consultant's profiles.yml commonly holds other clients' credentials.
  3. The script does nothing unless asked: --check reports what is derivable,
     --set-secrets sets them, --publish runs the release's run.sh with
     WAREHOUSE_CREDENTIALS in the environment. /wire:agents_schema-generate asks
     the consultant which of these to do before calling it.

Supported profile shapes (the ones the agents-schema CLI accepts):

  bigquery    method: service-account-json with keyfile_json, or
              method: service-account with keyfile (a path; read at run time)
  snowflake   password, or private_key_path (+ private_key_passphrase)
  databricks  host, http_path, catalog, token

Requires PyYAML: run as `uv run --with pyyaml python3 agents_schema_secrets.py ...`
or with any interpreter that has it.

Usage:
    python3 agents_schema_secrets.py --profiles-yml ~/.dbt/profiles.yml --profile acme --target prod --check
    python3 agents_schema_secrets.py ... --repo owner/repo --set-secrets [--warehouse-only] [--dry-run]
    python3 agents_schema_secrets.py ... --publish .wire/releases/<r>/dev/agents_schema/run.sh [--dry-run]

Exit codes: 0 ok; 1 usage or profile error; 3 the target's credential shape is not
one the agents-schema CLI accepts (nothing can be derived).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("error: PyYAML is required (run with `uv run --with pyyaml python3 ...`)", file=sys.stderr)
    sys.exit(1)

SUPPORTED = ("bigquery", "snowflake", "databricks")


def load_target(profiles_path: Path, profile: str, target: str | None) -> tuple[dict, str]:
    doc = yaml.safe_load(profiles_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or profile not in doc:
        available = ", ".join(sorted(k for k in (doc or {}) if k != "config")) or "none"
        raise SystemExit(f"error: profile {profile!r} not in {profiles_path} (available: {available})")
    prof = doc[profile]
    outputs = prof.get("outputs") or {}
    target = target or prof.get("target")
    if not target:
        if len(outputs) == 1:
            target = next(iter(outputs))
        else:
            raise SystemExit(f"error: profile {profile!r} has no default target; pass --target (available: {', '.join(sorted(outputs))})")
    if target not in outputs:
        raise SystemExit(f"error: target {target!r} not in profile {profile!r} (available: {', '.join(sorted(outputs))})")
    return outputs[target], target


def _expand(v):
    return os.path.expanduser(v) if isinstance(v, str) else v


def warehouse_credentials(out: dict) -> tuple[dict | None, str]:
    """(credentials dict, shape description) or (None, reason) when not derivable."""
    t = (out.get("type") or "").lower()
    if t == "bigquery":
        cred = None
        if isinstance(out.get("keyfile_json"), dict):
            cred, shape = out["keyfile_json"], "bigquery: inline service-account key (keyfile_json)"
        elif out.get("keyfile"):
            p = Path(_expand(out["keyfile"]))
            if not p.exists():
                return None, f"bigquery: keyfile {out['keyfile']} does not exist"
            cred, shape = json.loads(p.read_text(encoding="utf-8")), f"bigquery: service-account key file ({out['keyfile']})"
        else:
            return None, f"bigquery: method {out.get('method')!r} carries no key the agents-schema CLI can use (needs a service account)"
        d = {"type": "bigquery", "project_id": out.get("project") or cred.get("project_id")}
        if out.get("location"):
            d["location"] = out["location"]
        d["credentials_json"] = cred
        return d, shape
    if t == "snowflake":
        d = {"type": "snowflake", "account": out.get("account"), "user": out.get("user"),
             "warehouse": out.get("warehouse"), "database": out.get("database")}
        if out.get("role"):
            d["role"] = out["role"]
        if out.get("private_key_path"):
            p = Path(_expand(out["private_key_path"]))
            if not p.exists():
                return None, f"snowflake: private_key_path {out['private_key_path']} does not exist"
            d["private_key_pem"] = p.read_text(encoding="utf-8")
            if out.get("private_key_passphrase"):
                d["private_key_passphrase"] = out["private_key_passphrase"]
            return d, "snowflake: key-pair (private_key_path)"
        if out.get("password"):
            d["password"] = out["password"]
            return d, "snowflake: password"
        return None, f"snowflake: authenticator {out.get('authenticator', 'default')!r} carries no password or key the agents-schema CLI can use"
    if t == "databricks":
        if not out.get("token"):
            return None, "databricks: no token in the target (OAuth or other auth is not supported by the agents-schema CLI)"
        d = {"type": "databricks", "host": out.get("host"), "http_path": out.get("http_path"),
             "catalog": out.get("catalog"), "token": out["token"]}
        return d, "databricks: personal access token"
    return None, f"warehouse type {t!r} is not one Agents Schema publishes to ({', '.join(SUPPORTED)})"


def trimmed_profiles(profile: str, target: str, out: dict) -> dict:
    return {profile: {"target": target, "outputs": {target: out}}}


def describe(name: str, value: str) -> str:
    return f"{name}: {len(value)} chars, {len(value.splitlines())} lines"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profiles-yml", default=os.path.expanduser("~/.dbt/profiles.yml"))
    ap.add_argument("--profile", required=True)
    ap.add_argument("--target")
    ap.add_argument("--repo", help="owner/repo for gh secret set (default: the current repository)")
    ap.add_argument("--check", action="store_true", help="report what can be derived; sets nothing")
    ap.add_argument("--set-secrets", action="store_true", help="set WAREHOUSE_CREDENTIALS and DBT_PROFILES_YML on the repository")
    ap.add_argument("--warehouse-only", action="store_true", help="with --set-secrets: set WAREHOUSE_CREDENTIALS only (a LookML repository needs no dbt profile)")
    ap.add_argument("--publish", metavar="RUN_SH", help="run this run.sh with WAREHOUSE_CREDENTIALS in its environment")
    ap.add_argument("--dry-run", action="store_true", help="with --set-secrets or --publish: print what would happen, do nothing")
    ap.add_argument("--json", action="store_true", help="machine-readable output for --check")
    a = ap.parse_args(argv)

    out, target = load_target(Path(os.path.expanduser(a.profiles_yml)), a.profile, a.target)
    cred, shape = warehouse_credentials(out)
    result = {"profile": a.profile, "target": target, "type": (out.get("type") or "").lower(), "derivable": cred is not None, "shape": shape,
              "profiles_yml_profiles": 1, "profiles_yml_targets": 1}
    if cred is None:
        if a.json:
            print(json.dumps(result))
        else:
            print(f"not derivable: {shape}")
        return 3

    wh_yaml = yaml.safe_dump(cred, sort_keys=False)
    prof_yaml = yaml.safe_dump(trimmed_profiles(a.profile, target, out), sort_keys=False)
    result["secrets"] = {"WAREHOUSE_CREDENTIALS": {"chars": len(wh_yaml), "keys": sorted(cred)},
                         "DBT_PROFILES_YML": {"chars": len(prof_yaml), "profiles": [a.profile], "targets": [target]}}

    if a.check or (not a.set_secrets and not a.publish):
        print(json.dumps(result, indent=None if a.json else 2))
        return 0

    if a.set_secrets:
        repo_args = ["-R", a.repo] if a.repo else []
        pairs = [("WAREHOUSE_CREDENTIALS", wh_yaml)] + ([] if a.warehouse_only else [("DBT_PROFILES_YML", prof_yaml)])
        for name, value in pairs:
            if a.dry_run:
                print(f"would run: gh secret set {name} {' '.join(repo_args)}  <- stdin ({describe(name, value)})")
                continue
            r = subprocess.run(["gh", "secret", "set", name, *repo_args], input=value, text=True, capture_output=True)
            if r.returncode != 0:
                print(f"error: gh secret set {name} failed: {r.stderr.strip()}", file=sys.stderr)
                return 1
            print(f"set {name} ({describe(name, value)})")

    if a.publish:
        run_sh = Path(a.publish)
        if not run_sh.exists():
            print(f"error: {run_sh} not found", file=sys.stderr)
            return 1
        if a.dry_run:
            print(f"would run: WAREHOUSE_CREDENTIALS=<{len(wh_yaml)} chars> bash {run_sh}")
            return 0
        env = dict(os.environ, WAREHOUSE_CREDENTIALS=wh_yaml)
        env.setdefault("UV_PYTHON", "cpython-3.12-macos-aarch64-none" if sys.platform == "darwin" and os.uname().machine == "arm64" else "")
        if not env["UV_PYTHON"]:
            env.pop("UV_PYTHON")
        r = subprocess.run(["bash", str(run_sh)], env=env, text=True, capture_output=True)
        text = r.stdout + r.stderr
        if "private_key" in text.lower() or "password" in text.lower():
            text = "(output withheld: it contained a credential-like string)"
        print(text.strip())
        print(f"publish exit {r.returncode}")
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())

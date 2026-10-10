#!/usr/bin/env python3
"""
Route A: BigQuery job history for Looker Studio reports (wire#278, bi_migration,
pair looker_studio_to_omni).

Looker Studio labels every BigQuery job it runs with requestor=looker_studio,
looker_studio_report_id and looker_studio_datasource_id. This script reads those jobs
from INFORMATION_SCHEMA.JOBS and links each one to the chart that ran it: the column
aliases in the SQL carry the chart's field ids (qt_...), which are the concept names in
report.json.

Two steps, so the linking is testable without BigQuery:

    fetch   runs the query with the bq CLI and writes jobs_raw.json (needs
            bigquery.jobs.listAll on the billing project: BigQuery Resource Viewer)
    link    reads jobs_raw.json and report.json and writes chart_sql.json. No network call.
            Deterministic: same input, byte-identical output.

Usage:
    python3 wire/scripts/looker_studio_jobs.py fetch --billing-project P --location US
        --report-id R [--days 180] --out <dir>
    python3 wire/scripts/looker_studio_jobs.py link --jobs <dir>/jobs_raw.json
        --report <extract_dir>/report.json --out <dir>

The billing project and location come from Route C recordings (recordings.json,
bigquery_job), or from the data source owner. Jobs live in the billing project, which
can differ from the project that holds the tables.

Limits: BigQuery charts only; only charts that ran a query inside the retention window
(up to 180 days); results served from Looker Studio's own cache leave no job.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

VERSION = "1.0.0"
FIELD_ID = re.compile(r"(?<![A-Za-z0-9])qt_[a-z0-9]+")   # aliases look like t0_qt_usi31e057d
SAFE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def jobs_sql(project: str, location: str, report_id: str, days: int) -> str:
    for v in (project, location, report_id):
        if not SAFE.match(v):
            raise ValueError(f"unsafe identifier: {v!r}")
    region = f"region-{location.lower()}"
    return f"""
SELECT job_id, creation_time, user_email, cache_hit, total_bytes_processed, query,
  (SELECT value FROM UNNEST(labels) WHERE key = 'looker_studio_report_id') AS report_id,
  (SELECT value FROM UNNEST(labels) WHERE key = 'looker_studio_datasource_id') AS datasource_id,
  ARRAY(SELECT CONCAT(t.project_id, '.', t.dataset_id, '.', t.table_id) FROM UNNEST(referenced_tables) t) AS referenced_tables
FROM `{project}`.`{region}`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {int(days)} DAY)
  AND job_type = 'QUERY'
  AND EXISTS (SELECT 1 FROM UNNEST(labels) WHERE key = 'looker_studio_report_id' AND value = '{report_id}')
ORDER BY creation_time
""".strip()


def fetch(a) -> int:
    sql = jobs_sql(a.billing_project, a.location, a.report_id, a.days)
    cmd = ["bq", f"--project_id={a.billing_project}", "query", "--nouse_legacy_sql", "--format=json",
           "--max_rows=1000000", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr or res.stdout, file=sys.stderr)
        if "jobs.listAll" in (res.stderr + res.stdout) or "Access Denied" in (res.stderr + res.stdout):
            print("Route A needs bigquery.jobs.listAll on the billing project (BigQuery Resource Viewer).",
                  file=sys.stderr)
        return 2
    rows = json.loads(res.stdout or "[]")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "jobs_raw.json").write_text(json.dumps({"billing_project": a.billing_project, "location": a.location,
                                                   "report_id": a.report_id, "days": a.days, "rows": rows},
                                                  indent=1, sort_keys=True) + "\n")
    print(f"{len(rows)} jobs -> {out / 'jobs_raw.json'}")
    return 0


def concept_owners(report: dict):
    owners = {}
    comps = [(p["id"], c) for p in report["pages"] for c in p["components"]] + \
            [(None, c) for c in report["report_components"]]
    for page_id, c in comps:
        for f in c.get("dimensions", []) + c.get("metrics", []) + c.get("chart_fields", []):
            if f.get("name"):
                owners.setdefault(f["name"], set()).add((page_id, c["id"]))
    return owners


def link(jobs: dict, report: dict) -> dict:
    owners = concept_owners(report)
    rows = sorted(jobs.get("rows", []), key=lambda r: (str(r.get("creation_time")), str(r.get("job_id"))))
    per_component, unlinked, per_ds = {}, [], {}
    for r in rows:
        ids = sorted(set(FIELD_ID.findall(r.get("query") or "")))
        comps = sorted({o for i in ids for o in owners.get(i, ())}, key=lambda x: (x[0] or "", x[1]))
        ds = r.get("datasource_id")
        d = per_ds.setdefault(ds, {"jobs": 0, "last_run": None, "referenced_tables": set()})
        d["jobs"] += 1
        d["last_run"] = str(r.get("creation_time"))
        rt = r.get("referenced_tables") or []
        d["referenced_tables"].update(rt if isinstance(rt, list) else [rt])
        job = {"job_id": r.get("job_id"), "creation_time": str(r.get("creation_time")),
               "cache_hit": r.get("cache_hit") in (True, "true"), "datasource_id": ds, "field_ids": ids}
        if not comps:
            unlinked.append(job)
            continue
        for page_id, cid in comps:
            e = per_component.setdefault(cid, {"page_id": page_id, "component_id": cid, "jobs": 0,
                                               "first_run": job["creation_time"], "last_run": None,
                                               "latest_sql": None, "latest_job_id": None, "datasource_ids": set()})
            e["jobs"] += 1
            e["last_run"] = job["creation_time"]
            e["latest_sql"] = r.get("query")
            e["latest_job_id"] = r.get("job_id")
            e["datasource_ids"].add(ds)
    comps_out = []
    for cid in sorted(per_component):
        e = per_component[cid]
        e["datasource_ids"] = sorted(x for x in e["datasource_ids"] if x)
        comps_out.append(e)
    all_data = sorted(c["id"] for p in report["pages"] for c in p["components"] if c["kind"] == "data")
    return {
        "linker": {"name": "looker_studio_jobs", "version": VERSION},
        "report_id": report["report"]["id"],
        "billing_project": jobs.get("billing_project"),
        "location": jobs.get("location"),
        "window_days": jobs.get("days"),
        "counts": {"jobs": len(rows), "components_with_sql": len(comps_out),
                   "data_components": len(all_data),
                   "data_components_without_jobs": len([c for c in all_data if c not in per_component]),
                   "unlinked_jobs": len(unlinked)},
        "components": comps_out,
        "datasources": [{"datasource_id": k, "jobs": v["jobs"], "last_run": v["last_run"],
                         "referenced_tables": sorted(v["referenced_tables"])}
                        for k, v in sorted(per_ds.items(), key=lambda x: x[0] or "")],
        "components_without_jobs": [c for c in all_data if c not in per_component],
        "unlinked_jobs": unlinked,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--billing-project", required=True)
    f.add_argument("--location", required=True, help="BigQuery location, for example US, EU or europe-west2")
    f.add_argument("--report-id", required=True)
    f.add_argument("--days", type=int, default=180)
    f.add_argument("--out", required=True)
    l = sub.add_parser("link")
    l.add_argument("--jobs", required=True)
    l.add_argument("--report", required=True)
    l.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return fetch(a)
    doc = link(json.loads(Path(a.jobs).read_text()), json.loads(Path(a.report).read_text()))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "chart_sql.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    c = doc["counts"]
    print(f"{c['jobs']} jobs linked to {c['components_with_sql']} of {c['data_components']} data components -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

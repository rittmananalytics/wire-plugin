#!/usr/bin/env python3
"""
Looker Studio audit catalogs (wire#278, bi_migration, pair looker_studio_to_omni).

Reads the report.json files written by looker_studio_extract.py (and, when Route A
ran, each report's chart_sql.json) and writes the two catalogs the audit, the plan and
the register share:

    content_catalog.csv      one row per report, page and component, with a translation class
    datasource_catalog.csv   one row per data source and blend, with a translation class

Deterministic: same input, byte-identical output. No network or AI call. The classes are
the rule in wire/bi_pairs/looker_studio_to_omni/translation_guide.md; this script is the
only place it is applied, so the audit, the plan and the tests cannot disagree.

Usage:
    python3 wire/scripts/looker_studio_catalog.py --reports <dir>/<id>/report.json [...]
        [--chart-sql <dir>/<id>/chart_sql.json ...] --namespace <client_slug> --out <dir>

Component classes:
    mechanical   a supported chart type, on a data source the plan can map, with no
                 chart-level formula and no comparison period
    assisted     a supported chart type that needs a decision: a chart-level calculated
                 field, a comparison period, a blend, a combo or bullet chart, a control
    redesign     a chart type with no Omni equivalent (community visualisations and others)
    drop         decorative shapes, lines and images; text boxes (recreated by hand)
Data source classes:
    map          BigQuery table or view: the Omni model can read the same table
    assisted     BigQuery custom SQL: becomes a dbt model or an Omni SQL view
    pipeline     community connector, Google product connector or Sheets: no known
                 warehouse copy; the plan raises a pipeline task
    blocked      definition not read (Edit access refused, or not captured)
A component on a pipeline or blocked data source carries that in `blocked_by`; its own
class still describes the chart.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from looker_studio_extract import leaf_datasources  # noqa: E402

VERSION = "1.0.0"

# Looker Studio component type -> (Omni chart, class). content_mapping.md documents it.
CHART_TYPES = {
    "kpi-metric": ("kpi", "mechanical"),
    "simple-table": ("table", "mechanical"),
    "pivot-table": ("table_pivot", "mechanical"),
    "simple-barchart": ("bar", "mechanical"),
    "simple-columnchart": ("bar", "mechanical"),
    "simple-linechart": ("line", "mechanical"),
    "simple-areachart": ("area", "mechanical"),
    "simple-piechart": ("pie", "mechanical"),
    "simple-scatterchart": ("scatter", "mechanical"),
    "simple-combochart": ("combo", "assisted"),
    "bulletchart": ("kpi", "assisted"),
    "simple-geochart": ("map", "assisted"),
    "geo-map": ("map", "assisted"),
}
DS_CLASS = {"bigquery_table": "map", "bigquery_custom_sql": "assisted", "community_connector": "pipeline",
            "google_sheets": "pipeline", "other": "pipeline", "multiple": "assisted"}

CONTENT_COLUMNS = ["object_type", "object_uri", "report_id", "page_id", "component_id", "name", "section",
                   "hidden", "component_type", "kind", "omni_chart", "dataset_kind", "dataset_id",
                   "grid_x", "grid_y", "grid_w", "grid_h", "chart_formulas", "has_comparison",
                   "jobs", "last_run", "usage_source", "translation_class", "reason", "blocked_by"]
DS_COLUMNS = ["object_type", "object_uri", "id", "name", "connector", "access", "project", "dataset",
              "table", "billing_project", "field_count", "calculated_count", "used_by_components",
              "used_by_reports", "used_by_blends", "translation_class", "reason"]


def ds_class(d: dict):
    if d["access"] == "refused":
        return "blocked", "Edit access to the data source refused"
    if d["access"] != "read":
        return "blocked", "data source definition not captured"
    conn = (d.get("connection") or {}).get("connector", "other")
    cls = DS_CLASS.get(conn, "pipeline")
    reason = {"map": "warehouse table", "assisted": "custom SQL: move into dbt or an Omni SQL view",
              "pipeline": f"{conn}: no known warehouse copy, load into the warehouse first"}[cls]
    if conn == "community_connector" and (d["connection"] or {}).get("sql"):
        reason = "community connector running its own SQL: reproduce that query in the warehouse"
    return cls, reason


def component_class(c: dict, blend_ids: set):
    kind = c["kind"]
    if kind == "decorative":
        return None, "drop", "decorative"
    if kind == "text":
        return None, "drop", "text box, recreate by hand"
    if kind == "control":
        return None, "assisted", "control becomes an Omni dashboard control"
    omni, cls = CHART_TYPES.get(c["type"], (None, "redesign"))
    if omni is None:
        return None, "redesign", f"chart type {c['type']} has no Omni mapping"
    reasons = []
    if cls == "assisted":
        reasons.append(f"{c['type']} maps to the closest Omni chart")
    formulas = [f for f in c.get("metrics", []) + c.get("dimensions", []) + c.get("chart_fields", []) if f.get("formula")]
    if formulas:
        reasons.append("chart-level calculated field")
    if c.get("comparison"):
        reasons.append("comparison period")
    if (c.get("dataset") or {}).get("id") in blend_ids:
        reasons.append("blend becomes a modelled join")
    if reasons:
        cls = "assisted"
    return omni, cls, "; ".join(reasons)


def build(reports, chart_sql, namespace):
    content, sources = [], {}
    for r in reports:
        rid = r["report"]["id"]
        base = f"lookerstudio:{namespace}:report:{rid}"
        jobs = {c["component_id"]: c for c in (chart_sql.get(rid) or {}).get("components", [])}
        usage_source = "bigquery_jobs" if rid in chart_sql else "unavailable"
        blend_ids = {b["id"] for b in r["blends"]}
        ds_by_id = {d["id"]: d for d in r["datasources"]}
        dcls = {d["id"]: ds_class(d)[0] for d in r["datasources"]}
        content.append({"object_type": "report", "object_uri": base, "report_id": rid, "name": r["report"]["name"],
                        "usage_source": usage_source, "translation_class": "", "reason": f"revision {r['report']['revision']}"})
        comps = [(None, None, c) for c in r["report_components"]] + \
                [(p["id"], p, c) for p in r["pages"] for c in p["components"]]
        for p in r["pages"]:
            content.append({"object_type": "page", "object_uri": f"{base}/page:{p['id']}", "report_id": rid,
                            "page_id": p["id"], "name": p["name"], "section": p["section"] or "",
                            "hidden": "true" if p["hidden"] else "false", "usage_source": usage_source,
                            "translation_class": "", "reason": "" if p.get("defined", True) else "page not defined"})
        for page_id, p, c in comps:
            omni, cls, reason = component_class(c, blend_ids)
            ds = (c.get("dataset") or {}).get("id")
            blocked = ""
            if ds in blend_ids:
                b = next(x for x in r["blends"] if x["id"] == ds)
                leafs = sorted(set(leaf_datasources(b["tree"])))
                bad = sorted({dcls.get(x, "blocked") for x in leafs} & {"pipeline", "blocked"})
                blocked = ",".join(bad)
            elif ds and dcls.get(ds) in ("pipeline", "blocked"):
                blocked = dcls[ds]
            elif ds and ds not in ds_by_id and cls not in ("drop",):
                blocked = "blocked"
            j = jobs.get(c["id"], {})
            g = c["grid"]
            uri = f"{base}/page:{page_id}/component:{c['id']}" if page_id else f"{base}/component:{c['id']}"
            content.append({
                "object_type": "component", "object_uri": uri, "report_id": rid, "page_id": page_id or "",
                "component_id": c["id"], "name": "", "section": "",
                "hidden": "" if p is None else ("true" if p["hidden"] else "false"),
                "component_type": c["type"], "kind": c["kind"], "omni_chart": omni or "",
                "dataset_kind": "" if not ds else ("blend" if ds in blend_ids else "datasource"),
                "dataset_id": ds or "", "grid_x": g["x"], "grid_y": g["y"], "grid_w": g["w"], "grid_h": g["h"],
                "chart_formulas": sum(1 for f in c.get("metrics", []) + c.get("dimensions", []) + c.get("chart_fields", [])
                                      if f.get("formula")),
                "has_comparison": "true" if c.get("comparison") else "false",
                "jobs": j.get("jobs", 0 if usage_source == "bigquery_jobs" else "unknown"),
                "last_run": j.get("last_run") or ("" if usage_source == "bigquery_jobs" else "unknown"),
                "usage_source": usage_source, "translation_class": cls, "reason": reason, "blocked_by": blocked,
            })
        for d in r["datasources"]:
            e = sources.setdefault(d["id"], {"d": d, "reports": set(), "components": 0, "blends": 0})
            e["reports"].add(rid)
            e["components"] += d.get("used_by_components", 0)
            e["blends"] += d.get("used_by_blends", 0)
            if e["d"]["access"] != "read" and d["access"] == "read":
                e["d"] = d
        for b in r["blends"]:
            content.append({"object_type": "blend", "object_uri": f"{base}/blend:{b['id']}", "report_id": rid,
                            "name": b["name"], "dataset_id": b["id"], "dataset_kind": "blend",
                            "translation_class": "assisted", "reason": "blend becomes a modelled join",
                            "usage_source": usage_source})
    ds_rows = []
    for ds_id in sorted(sources):
        e = sources[ds_id]
        d = e["d"]
        conn = d.get("connection") or {}
        cls, reason = ds_class(d)
        ds_rows.append({
            "object_type": "datasource", "object_uri": f"lookerstudio:{namespace}:datasource:{ds_id}", "id": ds_id,
            "name": d.get("name") or d.get("alias") or "", "connector": conn.get("connector", ""),
            "access": d["access"], "project": conn.get("project") or "", "dataset": conn.get("dataset") or "",
            "table": conn.get("table") or "", "billing_project": conn.get("billing_project") or "",
            "field_count": len(d["fields"]), "calculated_count": sum(1 for f in d["fields"] if f.get("calculated")),
            "used_by_components": e["components"], "used_by_reports": len(e["reports"]), "used_by_blends": e["blends"],
            "translation_class": cls, "reason": reason,
        })
    return content, ds_rows


def write_csv(rows, columns) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in columns})
    return buf.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reports", nargs="+", required=True)
    ap.add_argument("--chart-sql", nargs="*", default=[])
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    reports = sorted((json.loads(Path(p).read_text()) for p in a.reports), key=lambda r: r["report"]["id"])
    chart_sql = {}
    for p in a.chart_sql:
        doc = json.loads(Path(p).read_text())
        chart_sql[doc["report_id"]] = doc
    content, ds_rows = build(reports, chart_sql, a.namespace)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "content_catalog.csv").write_text(write_csv(content, CONTENT_COLUMNS))
    (out / "datasource_catalog.csv").write_text(write_csv(ds_rows, DS_COLUMNS))
    by = {}
    for r in content:
        if r["object_type"] == "component":
            by[r["translation_class"]] = by.get(r["translation_class"], 0) + 1
    dby = {}
    for r in ds_rows:
        dby[r["translation_class"]] = dby.get(r["translation_class"], 0) + 1
    print(f"components {dict(sorted(by.items()))}; data sources {dict(sorted(dby.items()))} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

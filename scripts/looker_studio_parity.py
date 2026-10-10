#!/usr/bin/env python3
"""
Route C: Looker Studio chart recordings to parity contracts (wire#278, bi_migration,
pair looker_studio_to_omni).

When a report page loads, Looker Studio fetches each chart's data with a
batchedDataV2 call. looker_studio_capture.py keeps those responses in <capture>/data/.
This script turns each recorded chart result into:

    recordings/<key>/source.csv       the rows the chart displayed (main period)
    recordings/<key>/compare.csv      the comparison period rows, when the chart has one
    recordings/<key>/totals.csv       the totals row, when the chart has one
    recordings/<key>/contract.yaml    a test contract for wire/scripts/bi_parity.py, with the
                                      date range and time zone the recording used
    recordings.json                   index: one entry per recording, with the BigQuery job
                                      link (billing project, location, job id) for BigQuery charts

The contract's target_object is left empty: /wire:omni-content-generate fills it when
the Omni tile exists. The source CSV is the expected result for every connector,
including ones with no query log (community connectors, GA4, Google Ads, Sheets).

Deterministic: same capture and report.json, byte-identical output. No network or AI call.

Usage:
    python3 wire/scripts/looker_studio_parity.py --capture <capture_dir>/<report_id>
        --report <extract_dir>/report.json --out <dir> [--namespace <client_slug>]

Decoding rules (observed in captures):
    - A column lists only its non-null values; nullIndex lists the row positions that are null.
    - Column types: doubleColumn, stringColumn, dateColumn (and any other *Column, kept as text).
    - viewTags.compareIndex 0 is the main period, 1 the comparison period; isTotals marks the
      totals row; isMin and isMax subsets are axis helpers and are not kept.
    - dateRanges are YYYYMMDD integers; timezone is the report's time zone.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from looker_studio_extract import read_capture_file  # noqa: E402

VERSION = "1.0.0"
JOB_URL = re.compile(r"project=([^&]+)&j=bq:([^:]+):([^&\s\"]+)")


def decode_column(col: dict, size: int):
    kind = next((k for k in sorted(col) if k.endswith("Column")), None)
    values = list((col.get(kind) or {}).get("values", [])) if kind else []
    nulls = set(col.get("nullIndex", []))
    out, it = [], iter(values)
    for i in range(size):
        out.append(None if i in nulls else next(it, None))
    return kind, out


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)


def to_csv(header, rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow([fmt(v) for v in r])
    return buf.getvalue()


def table(subset: dict):
    td = subset.get("dataset", {}).get("tableDataset", {})
    size = td.get("size", 0) or 0
    names = [c.get("name") for c in td.get("columnInfo", [])]
    cols, kinds = [], []
    for col in td.get("column", []):
        k, vals = decode_column(col, size)
        kinds.append(k)
        cols.append(vals)
    rows = [[c[i] for c in cols] for i in range(size)] if cols else []
    return names, kinds, rows, td.get("totalCount")


def component_index(report: dict):
    idx = {}
    for p in report["pages"]:
        for c in p["components"]:
            idx[c["id"]] = (p["id"], c)
    for c in report["report_components"]:
        idx[c["id"]] = (None, c)
    return idx


def labels_for(comp: dict, names):
    known = {f.get("name"): f for f in comp.get("dimensions", []) + comp.get("metrics", []) + comp.get("chart_fields", [])}
    out, seen = [], {}
    for n in names:
        f = known.get(n, {})
        lab = f.get("label") if f.get("label") not in (None, "", "-") else (f.get("source_field") or n)
        lab = re.sub(r"[^A-Za-z0-9]+", "_", lab).strip("_").lower() or n
        if lab in seen:
            seen[lab] += 1
            lab = f"{lab}_{seen[lab]}"
        else:
            seen[lab] = 1
        out.append(lab)
    return out


def recordings(cap: Path, report: dict):
    idx = component_index(report)
    meta = json.loads((cap / "meta.json").read_text()) if (cap / "meta.json").exists() else {}
    per_component = {}
    for f in sorted((cap / "data").glob("*batchedDataV2*")) if (cap / "data").is_dir() else []:
        header, body = read_capture_file(f)
        if header.get("status") != 200 or not body:
            continue
        req = json.loads(header.get("post") or "{}")
        for rq, rs in zip(req.get("dataRequest", []), body.get("dataResponse", [])):
            ctx = rq.get("requestContext", {}).get("reportContext", {})
            cid = ctx.get("componentId")
            spec = rq.get("datasetSpec", {})
            dims = {d.get("name") for d in spec.get("queryFields", []) if "aggregation" not in d.get("dataTransformation", {})
                    and "textFormula" not in d.get("dataTransformation", {})}
            subsets = {}
            job = None
            for sub in rs.get("dataSubset", []):
                tags = sub.get("viewTags", {})
                if tags.get("isMin") or tags.get("isMax"):
                    continue
                role = "totals" if tags.get("isTotals") else ("compare" if tags.get("compareIndex", 0) else "source")
                if role == "totals" and tags.get("compareIndex", 0):
                    continue
                subsets[role] = table(sub)
                m = JOB_URL.search(sub.get("biJobUrl", "") or "")
                if m and role == "source":
                    job = {"billing_project": m.group(1), "location": m.group(2), "job_id": m.group(3)}
            if "source" not in subsets:
                continue
            ranges = [{"start": r.get("startDate"), "end": r.get("endDate")} for r in spec.get("dateRanges", [])]
            sig = json.dumps([spec.get("queryFields"), spec.get("filters"), spec.get("dateRanges")], sort_keys=True)
            per_component.setdefault(cid, {})[sig] = {
                "component_id": cid, "page_id": ctx.get("pageId"), "display_type": ctx.get("displayType"),
                "datasource_ids": [d.get("datasourceId") for d in spec.get("dataset", [])],
                "date_ranges": ranges, "timezone": spec.get("timezone"),
                "filter_count": len(spec.get("filters", [])), "dimension_names": sorted(dims),
                "subsets": subsets, "bigquery_job": job,
            }
    out = []
    for cid in sorted(per_component, key=lambda x: x or ""):
        for n, sig in enumerate(sorted(per_component[cid]), 1):
            rec = per_component[cid][sig]
            page_id, comp = idx.get(cid, (rec["page_id"], {}))
            rec["key"] = f"{rec['page_id']}__{cid}__{n}"
            rec["component"] = comp
            rec["captured_at"] = meta.get("captured_at")
            out.append(rec)
    return out


def contract(rec: dict, report_id: str, namespace: str, labels, dims, row_limit):
    measures = {lab: {"comparator": "floating_tolerance", "absolute_tolerance": 0.000001,
                      "relative_tolerance": 0.000001}
                for lab, is_dim in zip(labels, dims) if not is_dim}
    r = rec["date_ranges"][0] if rec["date_ranges"] else {}
    return {
        "test_id": rec["key"],
        "source_object": f"lookerstudio:{namespace}:report:{report_id}/page:{rec['page_id']}/component:{rec['component_id']}",
        "target_object": "",
        "baseline": "",
        "execution": {
            "principal": "",
            "timezone": rec["timezone"],
            "data_snapshot": rec["captured_at"],
            "date_range": {"start": r.get("start"), "end": r.get("end")},
            "limit": row_limit,
            "cache_policy": "bypass",
        },
        "comparison": {
            "row_semantics": "multiset",
            "key_fields": [lab for lab, is_dim in zip(labels, dims) if is_dim],
            "field_map": {},
            "measures": measures,
            "expected_rows": "nonzero",
            "tile_sorted": bool(rec["component"].get("sort")),
        },
        "source_evidence": {
            "route": "C",
            "datasource_ids": rec["datasource_ids"],
            "bigquery_job": rec["bigquery_job"],
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--namespace", default="client")
    a = ap.parse_args(argv)
    cap, out = Path(a.capture), Path(a.out)
    report = json.loads(Path(a.report).read_text())
    recs = recordings(cap, report)
    index = []
    for rec in recs:
        names, kinds, rows, total = rec["subsets"]["source"]
        labels = labels_for(rec["component"], names)
        dims = [n in rec["dimension_names"] for n in names]
        d = out / "recordings" / rec["key"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "source.csv").write_text(to_csv(labels, rows))
        for role in ("compare", "totals"):
            if role in rec["subsets"]:
                n2, _, r2, _ = rec["subsets"][role]
                (d / f"{role}.csv").write_text(to_csv(labels_for(rec["component"], n2), r2))
        row_limit = rec["component"].get("row_limit")
        c = contract(rec, report["report"]["id"], a.namespace, labels, dims, row_limit)
        (d / "contract.yaml").write_text(yaml.safe_dump(c, sort_keys=True, allow_unicode=True))
        index.append({
            "key": rec["key"], "page_id": rec["page_id"], "component_id": rec["component_id"],
            "display_type": rec["display_type"], "datasource_ids": rec["datasource_ids"],
            "date_ranges": rec["date_ranges"], "timezone": rec["timezone"], "rows": len(rows),
            "total_count": total, "columns": labels, "column_types": kinds,
            "has_comparison": "compare" in rec["subsets"], "has_totals": "totals" in rec["subsets"],
            "truncated": bool(row_limit) and len(rows) >= row_limit,
            "bigquery_job": rec["bigquery_job"],
        })
    out.mkdir(parents=True, exist_ok=True)
    doc = {"builder": {"name": "looker_studio_parity", "version": VERSION},
           "report_id": report["report"]["id"], "captured_at": report["report"].get("captured_at"),
           "recordings": index}
    (out / "recordings.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    bq = sum(1 for r in index if r["bigquery_job"])
    print(f"{len(index)} recordings ({bq} with a BigQuery job link) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

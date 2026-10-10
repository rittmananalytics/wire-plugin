#!/usr/bin/env python3
"""
Metric catalogue builder for Looker Studio estates (wire#278, bi_migration, pair looker_studio_to_omni).

Reads one or more report.json files from looker_studio_extract.py, collects every
calculated field (data-source level and chart level), normalises each formula, and
groups the definitions by metric name. Each group gets a candidate class:

    same_definition              every copy has the same normalised formula: merge into one
    same_shape_different_fields  same calculation, different input fields: an alias, or a
                                 different thing with the same name (for example paid and
                                 organic CTR). Needs a ruling
    conflict                     different calculations under one name. Needs a ruling

It also lists findings that change numbers silently:

    sum_of_ratio                 a chart sums a calculated field that divides one row value by
                                 another (a sum of row ratios, not a ratio of sums)

Deterministic: same input, byte-identical output. No AI call. The class is a candidate:
the agent proposes and the client rules in /wire:metric-catalogue-review. The script
never resolves a conflict.

Usage:
    python3 wire/scripts/looker_studio_metrics.py --reports r1/report.json [r2/report.json ...] --out <dir>

Writes <dir>/metric_catalogue.json and <dir>/metric_catalogue.csv.

Normalisation (documented in wire/bi_pairs/looker_studio_to_omni/translation_guide.md):
    1. Drop table namespaces (t0., t1.).
    2. Lower-case field names; upper-case function names.
    3. IFNULL(x, 0) and COALESCE(x, 0) inside SUM, AVG, MIN or MAX become x
       (those aggregates ignore nulls, so the result only differs when every row is null).
    4. Collapse whitespace to one space, and remove it around operators, commas and brackets.
The shape of a formula is its normalised text with every field name replaced by f and
every number by n.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"
FUNC = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
NS = re.compile(r"\bt\d+\.")
IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_.]*\b")
NUMBER = re.compile(r"\b\d+(\.\d+)?\b")
NULL_WRAP = re.compile(r"(SUM|AVG|MIN|MAX)\((?:IFNULL|COALESCE)\(([^(),]+),0\)\)")
AGG_FUNCS = {"SUM", "AVG", "COUNT", "COUNT_DISTINCT", "MIN", "MAX", "MEDIAN", "PERCENTILE", "APPROX_COUNT_DISTINCT"}
KEYWORDS = {"CASE", "WHEN", "THEN", "ELSE", "END", "AND", "OR", "NOT", "IN", "IS", "NULL", "TRUE", "FALSE", "LIKE"}


def normalise(formula: str) -> str:
    s = NS.sub("", formula or "")
    funcs = {m.group(1).upper() for m in FUNC.finditer(s)}
    strings = []

    def keep_string(m):
        strings.append(m.group(0))
        return f"\x00{len(strings) - 1}\x00"

    s = re.sub(r"'[^']*'|\"[^\"]*\"", keep_string, s)

    def case(m):
        w = m.group(0)
        return w.upper() if w.upper() in funcs or w.upper() in KEYWORDS else w.lower()

    s = IDENT.sub(case, s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*([()+\-*/,=<>!])\s*", r"\1", s)
    prev = None
    while prev != s:
        prev = s
        s = NULL_WRAP.sub(r"\1(\2)", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: strings[int(m.group(1))], s)


def shape(norm: str) -> str:
    funcs = {m.group(1) for m in FUNC.finditer(norm)}
    s = re.sub(r"'[^']*'|\"[^\"]*\"", "\x00", norm)
    s = IDENT.sub(lambda m: m.group(0) if m.group(0) in funcs or m.group(0) in KEYWORDS else "f", s)
    s = NUMBER.sub("n", s)
    return s.replace("\x00", "s")


def name_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (label or "").lower())


def is_row_ratio(formula: str) -> bool:
    """A division with no aggregate function: evaluated per row."""
    norm = normalise(formula)
    if "/" not in norm:
        return False
    return not any(f in AGG_FUNCS for f in (m.group(1) for m in FUNC.finditer(norm)))


def collect(report: dict):
    rid = report["report"]["id"]
    defs, findings = [], []
    ds_fields = {}
    for d in report["datasources"]:
        for f in d["fields"]:
            ds_fields[(d["id"], f["name"])] = f
            if f.get("calculated") and f.get("formula"):
                defs.append({"report_id": rid, "scope": "datasource", "location": d["id"],
                             "field": f["name"], "label": f["label"], "formula": f["formula"]})
    comps = [(p["id"], c) for p in report["pages"] for c in p["components"]] + \
            [(None, c) for c in report["report_components"]]
    for page_id, c in comps:
        ds = (c.get("dataset") or {}).get("id")
        for f in c.get("metrics", []) + c.get("dimensions", []) + c.get("chart_fields", []):
            if f.get("formula"):
                label = f.get("label") if f.get("label") not in (None, "", "-") else None
                defs.append({"report_id": rid, "scope": "chart", "location": f"{page_id}/{c['id']}",
                             "field": f.get("name"), "label": label, "formula": f["formula"]})
        for f in c.get("metrics", []):
            src = ds_fields.get((ds, f.get("source_field")))
            if f.get("aggregation") == 6 and src and src.get("formula") and is_row_ratio(src["formula"]):
                findings.append({"finding": "sum_of_ratio", "report_id": rid,
                                 "location": f"{page_id}/{c['id']}", "datasource_id": ds,
                                 "field": src["name"], "label": src["label"], "formula": src["formula"]})
    return defs, findings


def catalogue(reports):
    defs, findings = [], []
    for r in reports:
        d, f = collect(r)
        defs += d
        findings += f
    for d in defs:
        d["normalised"] = normalise(d["formula"])
        d["shape"] = shape(d["normalised"])
    groups = {}
    for d in defs:
        key = name_key(d["label"]) or f"unnamed:{d['normalised']}"
        groups.setdefault(key, []).append(d)
    out = []
    for key in sorted(groups):
        g = sorted(groups[key], key=lambda d: (d["report_id"], d["scope"], d["location"], d["field"] or ""))
        forms = sorted({d["normalised"] for d in g})
        shapes = sorted({d["shape"] for d in g})
        if len(forms) == 1:
            cls = "same_definition"
        elif len(shapes) == 1:
            cls = "same_shape_different_fields"
        else:
            cls = "conflict"
        labels = sorted({d["label"] for d in g if d["label"]})
        out.append({
            "key": key,
            "labels": labels,
            "candidate_class": cls,
            "definition_count": len(g),
            "report_count": len({d["report_id"] for d in g}),
            "formulas": [{"normalised": f,
                          "count": sum(1 for d in g if d["normalised"] == f),
                          "examples": sorted({d["formula"] for d in g if d["normalised"] == f})[:3]}
                         for f in forms],
            "definitions": [{k: d[k] for k in ("report_id", "scope", "location", "field", "label", "formula")}
                            for d in g],
        })
    findings.sort(key=lambda f: (f["finding"], f["report_id"], f["location"], f["field"] or ""))
    classes = {}
    for g in out:
        classes[g["candidate_class"]] = classes.get(g["candidate_class"], 0) + 1
    return {
        "builder": {"name": "looker_studio_metrics", "version": VERSION},
        "reports": sorted(r["report"]["id"] for r in reports),
        "counts": {"definitions": len(defs), "groups": len(out), "groups_by_class": dict(sorted(classes.items())),
                   "copied_definitions": sum(g["definition_count"] for g in out
                                             if g["candidate_class"] == "same_definition" and g["definition_count"] > 1),
                   "findings": len(findings)},
        "groups": out,
        "findings": findings,
    }


def to_csv(cat: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["key", "labels", "candidate_class", "definition_count", "report_count", "distinct_formulas",
                "normalised_formulas", "ruling", "canonical_formula", "target_name"])
    for g in cat["groups"]:
        w.writerow([g["key"], "; ".join(g["labels"]), g["candidate_class"], g["definition_count"],
                    g["report_count"], len(g["formulas"]), " | ".join(f["normalised"] for f in g["formulas"]),
                    "", "", ""])
    return buf.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reports", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    reports = [json.loads(Path(p).read_text()) for p in a.reports]
    cat = catalogue(reports)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metric_catalogue.json").write_text(json.dumps(cat, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "metric_catalogue.csv").write_text(to_csv(cat))
    c = cat["counts"]
    print(f"{c['definitions']} definitions in {c['groups']} groups {c['groups_by_class']}; "
          f"{c['findings']} findings -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

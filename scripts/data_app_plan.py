#!/usr/bin/env python3
"""Widget plan for a Looker Data App from the approved mockup chain (wire#387).

The fixed part of /wire:data_app-generate and -validate, so two people working
from the same approved catalog produce the same plan, and so the gaps (a chart
type the runtime cannot draw, a field the semantic layer does not define) are
listed rather than guessed at.

    plan   catalog CSV (+ dashboard_spec.md, fields.json) -> plan.json
           One entry per catalog row: the widget, the chart type, the resolved
           fields, a stable widget id, and every unmapped or unresolved item.
    check  plan.json + app.js (+ fields.json) -> coverage report
           Every planned widget id is in the app, no extra ids, every fields
           literal in the app resolves, titles and filters match. Exit 1 on a
           missing or extra widget, an unresolved field or a model mismatch.

Stdlib only. No AI call, no network. Never reads a credential.

Usage:
    python3 data_app_plan.py plan --catalog design/dashboard_visualization_catalog.csv \\
        --spec design/dashboard_spec.md --fields dev/data_app/<slug>/fields.json \\
        --model <model> --explore <explore> --app <slug> --out dev/data_app/<slug>/plan.json
    python3 data_app_plan.py check --plan plan.json --app-js apps/<slug>/app.js \\
        [--fields fields.json] [--model <model>] [--explore <explore>]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Catalog chart_type (mockup vocabulary) -> (widget tag, app-chart type).
# Matching is case-insensitive and ignores surrounding whitespace, hyphens
# and underscores. Anything else is unmapped: an <app-grid> plus a listing.
CHART_MAP = {
    "kpi tile": ("app-kpi", None), "kpi": ("app-kpi", None),
    "single value": ("app-kpi", None), "stat": ("app-kpi", None),
    "line": ("app-chart", "line"), "spline": ("app-chart", "line"),
    "area": ("app-chart", "areaspline"), "areaspline": ("app-chart", "areaspline"),
    "bar": ("app-chart", "column"), "column": ("app-chart", "column"),
    "vertical bar": ("app-chart", "column"),
    "horizontal bar": ("app-chart", "bar"), "hbar": ("app-chart", "bar"),
    "doughnut": ("app-chart", "donut"), "donut": ("app-chart", "donut"),
    "pie": ("app-chart", "pie"),
    "table": ("app-grid", None), "grid": ("app-grid", None), "data table": ("app-grid", None),
    "scatter": ("app-chart", "scatter"),
    "funnel": ("app-chart", "funnel"),
    "treemap": ("app-chart", "treemap"),
    "gauge": ("app-chart", "gauge"),
    "text": ("section", None), "markdown": ("section", None), "note": ("section", None),
}
UNMAPPED_WIDGET = ("app-grid", None)
# Chart types whose segments can be clicked to cross-filter the page.
SEGMENTED = {"column", "bar", "pie", "donut", "treemap", "funnel", "pyramid"}
TAG_SHORT = {"app-kpi": "kpi", "app-chart": "chart", "app-grid": "grid", "section": "section"}


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s or "untitled"


def norm_chart_type(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", (text or "").strip().lower())).strip()


def split_names(cell: str) -> list[str]:
    if not cell:
        return []
    parts = re.split(r"[;,|\n]+", cell)
    return [p.strip() for p in parts if p.strip()]


def match_column(fieldnames: list[str], *needles: str) -> str | None:
    """Catalog column names vary slightly between runs (viz_catalog-generate
    Step 2 matches on substring); do the same."""
    for name in fieldnames:
        low = name.lower()
        if any(n in low for n in needles):
            return name
    return None


def load_fields(path: str | None) -> tuple[set[str], dict[str, str]]:
    """Field names (view.field) from fields.json. Accepts a JSON list of
    names, or any JSON structure in which objects carry a dotted "name" (the
    shape explore-model.py --json emits), or a text file with one name per
    line. Types are kept where an object carries "type"."""
    names: set[str] = set()
    types: dict[str, str] = {}
    if not path:
        return names, types
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if line and "." in line and not line.startswith("#"):
                names.add(line)
        return names, types

    def walk(node):
        if isinstance(node, str):
            if "." in node and " " not in node:
                names.add(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            name = node.get("name")
            if isinstance(name, str) and "." in name:
                names.add(name)
                t = node.get("type") or node.get("category")
                if isinstance(t, str):
                    types[name] = t
            for key, value in node.items():
                if key == "name":
                    continue
                walk(value)

    walk(data)
    return names, types


def resolve_field(name: str, fields: set[str]) -> tuple[str | None, str]:
    """Exact view.field match, else a bare name that exactly one field ends
    in. Returns (resolved name or None, reason)."""
    if not fields:
        return None, "no_field_list"
    if name in fields:
        return name, "exact"
    if "." in name:
        return None, "not_found"
    suffix = "." + name
    candidates = sorted(f for f in fields if f.endswith(suffix))
    if len(candidates) == 1:
        return candidates[0], "unique_suffix"
    return None, "ambiguous" if candidates else "not_found"


# ----------------------------------------------------------------------
# spec parsing (dashboard_spec.md)
# ----------------------------------------------------------------------

def section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if re.match(r"^##\s+", line):
            inside = line.strip().lower() == f"## {heading}".lower()
            continue
        if inside:
            out.append(line)
    return out


def parse_filters(spec_text: str) -> list[dict]:
    """`## Filter Dimensions`: a bullet or table row per filter. The name is
    the text before ':' or '(' (or the first table cell); the field is the
    first dotted token, else the text after ':'; a default follows the word
    'default'."""
    filters = []
    for raw in section(spec_text, "Filter Dimensions"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells or set("".join(cells)) <= set("-: "):
                continue
            if cells[0].lower() in ("filter", "name", "filter name"):
                continue
            name = cells[0]
            field_given = cells[1] if len(cells) > 1 else ""
            default = cells[2] if len(cells) > 2 else ""
        else:
            body = re.sub(r"^[-*]\s*|^\d+\.\s*", "", line)
            m = re.match(r"^\**([^:(*]+)\**\s*[:(]?\s*(.*)$", body)
            if not m:
                continue
            name = m.group(1).strip()
            rest = m.group(2).strip().rstrip(")")
            default = ""
            dm = re.search(r"default\s*[:=]?\s*[\"'`]?([^\"'`,;)]+)", rest, re.IGNORECASE)
            if dm:
                default = dm.group(1).strip()
                rest = rest[:dm.start()].strip(" ,;(")
            dotted = re.search(r"\b([a-z0-9_]+\.[a-z0-9_]+)\b", rest, re.IGNORECASE)
            field_given = dotted.group(1) if dotted else rest.split(",")[0].strip(" `")
        if not name:
            continue
        filters.append({"name": name, "field_given": field_given, "default": default})
    return filters


def parse_interaction(spec_text: str) -> dict:
    notes = {"tabs": [], "cross_filter": True, "drill": "", "presentation": ""}
    for raw in section(spec_text, "Interaction Notes"):
        line = raw.strip()
        m = re.match(r"^[-*]?\s*\**(tabs|cross-filter|cross filter|drill|presentation)\**\s*:\s*(.*)$",
                     line, re.IGNORECASE)
        if not m:
            continue
        key, value = m.group(1).lower().replace(" ", "-"), m.group(2).strip()
        if key == "tabs":
            notes["tabs"] = [] if value.lower() in ("", "none", "no") else [t.strip() for t in value.split(",") if t.strip()]
        elif key == "cross-filter":
            notes["cross_filter"] = value.lower() not in ("none", "no", "off", "false")
        elif key == "drill":
            notes["drill"] = "" if value.lower() in ("none", "no") else value
        elif key == "presentation":
            notes["presentation"] = value.split()[0].lower() if value else ""
    return notes


# ----------------------------------------------------------------------
# plan
# ----------------------------------------------------------------------

def read_catalog(path: str) -> tuple[list[dict], dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        cols = {
            "page": match_column(fieldnames, "page", "dashboard"),
            "name": match_column(fieldnames, "visualization", "visualisation", "name", "title"),
            "chart": match_column(fieldnames, "chart", "type"),
            "measures": match_column(fieldnames, "measure"),
            "dimensions": match_column(fieldnames, "dimension"),
        }
        missing = [k for k, v in cols.items() if v is None and k in ("name", "chart")]
        if missing:
            raise SystemExit(f"ERROR: catalog has no column for {missing} (columns: {fieldnames})")
        rows = []
        for i, row in enumerate(reader, start=2):
            rows.append({
                "line": i,
                "page": (row.get(cols["page"]) or "").strip() if cols["page"] else "",
                "name": (row.get(cols["name"]) or "").strip(),
                "chart_type": (row.get(cols["chart"]) or "").strip(),
                "measures": split_names(row.get(cols["measures"]) or "") if cols["measures"] else [],
                "dimensions": split_names(row.get(cols["dimensions"]) or "") if cols["dimensions"] else [],
            })
    return rows, cols


def build_plan(args) -> dict:
    rows, _ = read_catalog(args.catalog)
    pages = []
    for r in rows:
        if r["page"] and r["page"] not in pages:
            pages.append(r["page"])
    if args.app:
        rows = [r for r in rows if slugify(r["page"]) == args.app or not r["page"]]
        if not rows:
            raise SystemExit(f"ERROR: no catalog row has a dashboard_page matching --app {args.app} "
                             f"(pages: {[slugify(p) for p in pages]})")
        app = args.app
        title = next((r["page"] for r in rows if slugify(r["page"]) == args.app), args.app)
    else:
        app = slugify(pages[0]) if pages else "app"
        title = pages[0] if pages else app

    fields, types = load_fields(args.fields)
    spec_text = Path(args.spec).read_text(encoding="utf-8") if args.spec else ""
    interaction = parse_interaction(spec_text) if spec_text else parse_interaction("")

    widgets = []
    unmapped = []
    unresolved = []
    seen_ids: dict[str, int] = {}
    for r in rows:
        key = norm_chart_type(r["chart_type"])
        mapped = key in CHART_MAP
        tag, chart = CHART_MAP.get(key, UNMAPPED_WIDGET)
        base_id = f"da-{TAG_SHORT[tag]}-{slugify(r['name'])}"
        n = seen_ids.get(base_id, 0)
        seen_ids[base_id] = n + 1
        widget_id = base_id if n == 0 else f"{base_id}-{n}"
        resolved_fields = []
        widget_unresolved = []
        for kind, names in (("dimension", r["dimensions"]), ("measure", r["measures"])):
            for name in names:
                res, reason = resolve_field(name, fields)
                if res:
                    resolved_fields.append(res)
                else:
                    item = {"widget_id": widget_id, "kind": kind, "name": name, "reason": reason}
                    widget_unresolved.append(item)
                    unresolved.append(item)
        if tag == "section":
            resolved_fields = []
        entry = {
            "catalog_line": r["line"],
            "page": r["page"],
            "title": r["name"],
            "catalog_chart_type": r["chart_type"],
            "widget": tag,
            "chart_type": chart,
            "widget_id": widget_id,
            "mapped": mapped,
            "cross_filter": bool(interaction["cross_filter"] and chart in SEGMENTED),
            "fields": resolved_fields,
            "field_types": {f: types[f] for f in resolved_fields if f in types},
            "unresolved": [{"kind": u["kind"], "name": u["name"], "reason": u["reason"]} for u in widget_unresolved],
        }
        widgets.append(entry)
        if not mapped:
            unmapped.append({"widget_id": widget_id, "title": r["name"], "chart_type_given": r["chart_type"],
                             "written_as": "app-grid"})

    filters = []
    for f in parse_filters(spec_text) if spec_text else []:
        res, reason = resolve_field(f["field_given"], fields) if f["field_given"] else (None, "no_field")
        filters.append({"name": f["name"], "field_given": f["field_given"], "field": res,
                        "resolved": res is not None, "reason": reason, "default": f["default"]})

    plan = {
        "app": app,
        "title": title,
        "model": args.model,
        "explore": args.explore,
        "source": {"catalog": Path(args.catalog).name, "spec": Path(args.spec).name if args.spec else None,
                   "fields": Path(args.fields).name if args.fields else None},
        "interaction": interaction,
        "widgets": widgets,
        "filters": filters,
        "unmapped": unmapped,
        "unresolved_fields": unresolved,
        "counts": {
            "catalog_rows": len(rows),
            "widgets": len(widgets),
            "unmapped": len(unmapped),
            "unresolved_fields": len(unresolved),
            "filters": len(filters),
            "filters_unresolved": sum(1 for f in filters if not f["resolved"]),
            "fields_known": len(fields),
        },
    }
    return plan


# ----------------------------------------------------------------------
# check
# ----------------------------------------------------------------------

WIDGET_TAG_RE = re.compile(r"<(app-kpi|app-chart|app-grid)\b((?:[^>]|=>)*)>", re.DOTALL)
ID_RE = re.compile(r"""\bid\s*=\s*["'](da-[\w-]+)["']""")
ATTR_RE = r"""\b{attr}\s*=\s*["']([^"']*)["']"""
FIELDS_LITERAL_RE = re.compile(r"\bfields\s*:\s*\[([^\]]*)\]")
QUERY_FIELD_RE = re.compile(r"""\bquery-field\s*=\s*["']([^"']+)["']""")
STRING_RE = re.compile(r"""["'`]([^"'`]+)["'`]""")
MODEL_RES = [re.compile(r"""\blooker-model\s*=\s*["']([^"']+)["']"""),
             re.compile(r"""this\.lookerModel\s*=\s*["'`]([^"'`]+)["'`]""")]
EXPLORE_RES = [re.compile(r"""\bexplore\s*=\s*["']([^"']+)["']"""),
               re.compile(r"""this\.explore\s*=\s*["'`]([^"'`]+)["'`]""")]
SELECT_LABEL_RE = re.compile(r"""<app-select\b(?:[^>]|=>)*?\blabel\s*=\s*["']([^"']+)["']""", re.DOTALL)


def run_check(args) -> dict:
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    text = Path(args.app_js).read_text(encoding="utf-8")
    fields, _ = load_fields(args.fields)

    expected = {w["widget_id"]: w for w in plan["widgets"]}
    found_ids = ID_RE.findall(text)
    found = set(found_ids)
    duplicates = sorted({i for i in found_ids if found_ids.count(i) > 1})
    missing = sorted(set(expected) - found)
    extra = sorted(found - set(expected))

    title_mismatches = []
    for m in WIDGET_TAG_RE.finditer(text):
        attrs = m.group(2)
        idm = ID_RE.search(attrs)
        if not idm or idm.group(1) not in expected:
            continue
        w = expected[idm.group(1)]
        tm = re.search(ATTR_RE.format(attr="title"), attrs) or re.search(ATTR_RE.format(attr="label"), attrs)
        shown = tm.group(1).strip() if tm else None
        if shown != w["title"]:
            title_mismatches.append({"widget_id": w["widget_id"], "expected": w["title"], "found": shown})

    literal_fields: list[str] = []
    for fm in FIELDS_LITERAL_RE.finditer(text):
        literal_fields += [s.strip() for s in STRING_RE.findall(fm.group(1))]
    literal_fields += QUERY_FIELD_RE.findall(text)
    literal_fields = sorted(set(f for f in literal_fields if "." in f))
    unresolved = sorted(f for f in literal_fields if f not in fields) if fields else []

    model = args.model or plan.get("model")
    explore = args.explore or plan.get("explore")
    models_found = sorted({v for rx in MODEL_RES for v in rx.findall(text)})
    explores_found = sorted({v for rx in EXPLORE_RES for v in rx.findall(text)})
    model_mismatch = sorted(v for v in models_found if model and v != model)
    explore_mismatch = sorted(v for v in explores_found if explore and v != explore)

    spreads_dashboard_filters = "this.dashboardFilters" in text
    select_labels = {s.strip() for s in SELECT_LABEL_RE.findall(text)}
    filters_missing = []
    for f in plan.get("filters", []):
        if f["name"] in select_labels or spreads_dashboard_filters:
            continue
        filters_missing.append(f["name"])

    report = {
        "app": plan.get("app"),
        "widgets_expected": len(expected),
        "widgets_found": len(found & set(expected)),
        "missing": missing,
        "extra": extra,
        "duplicate_ids": duplicates,
        "title_mismatches": title_mismatches,
        "fields_in_app": literal_fields,
        "fields_unresolved": unresolved,
        "fields_checked": bool(fields),
        "models_found": models_found,
        "explores_found": explores_found,
        "model_mismatch": model_mismatch,
        "explore_mismatch": explore_mismatch,
        "spreads_dashboard_filters": spreads_dashboard_filters,
        "filters_missing": filters_missing,
        "plan_unmapped": plan.get("counts", {}).get("unmapped", 0),
        "plan_unresolved_fields": plan.get("counts", {}).get("unresolved_fields", 0),
    }
    critical = bool(missing or extra or duplicates or unresolved or model_mismatch or explore_mismatch
                    or report["plan_unmapped"] or report["plan_unresolved_fields"])
    report["pass"] = not critical
    return report


# ----------------------------------------------------------------------
# cli
# ----------------------------------------------------------------------

def dump(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="catalog -> plan.json")
    p.add_argument("--catalog", required=True)
    p.add_argument("--spec")
    p.add_argument("--fields")
    p.add_argument("--model")
    p.add_argument("--explore")
    p.add_argument("--app", help="dashboard_page slug to plan (default: the first page)")
    p.add_argument("--out", help="write plan.json here (default: stdout)")

    c = sub.add_parser("check", help="plan.json against app.js")
    c.add_argument("--plan", required=True)
    c.add_argument("--app-js", required=True)
    c.add_argument("--fields")
    c.add_argument("--model")
    c.add_argument("--explore")

    args = ap.parse_args(argv)
    if args.cmd == "plan":
        plan = build_plan(args)
        out = dump(plan)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(out, encoding="utf-8")
            c = plan["counts"]
            print(f"plan written: {args.out}  rows={c['catalog_rows']} widgets={c['widgets']} "
                  f"unmapped={c['unmapped']} unresolved_fields={c['unresolved_fields']} "
                  f"filters={c['filters']} ({c['filters_unresolved']} unresolved)")
        else:
            sys.stdout.write(out)
        return 0
    report = run_check(args)
    sys.stdout.write(dump(report))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

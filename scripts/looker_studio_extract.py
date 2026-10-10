#!/usr/bin/env python3
"""
Looker Studio report extractor (wire#278, bi_migration release type, pair looker_studio_to_omni).

Reads one capture folder written by looker_studio_capture.py and writes the report
definition as report.json (machine-readable) and report.md (a readable summary).
Deterministic: the same capture folder always produces byte-identical output.
No network call and no AI call. The agent running /wire:looker-studio-audit-generate
reads these files; it never hand-writes them.

Usage:
    python3 wire/scripts/looker_studio_extract.py --capture <capture_dir>/<report_id> --out <dir>
        [--report-uri-prefix lookerstudio]

Capture folder layout (written by the capture script):
    meta.json                                  capture record: url, captured_at, revision, pages,
                                               datasources, app_version, failed_pages
    report/NNNN_getReport.txt                  report definition
    report/NNNN_getSchema.txt                  field list per data source (one call per data source)
    datasources/<id>/NNNN_getBlockDatasource.txt   data source definition (needs Edit on the data source)
    data/NNNN_batchedDataV2.txt                optional chart data (Route C), read by looker_studio_parity.py

Each .txt file is one JSON header line ({"url", "status", "post"}) followed by the
response body, which may start with the anti-hijacking prefix )]}'.

What it relies on (observed in captures, app version 20261004_0802):
    - A published report keeps its definition in publishedReportRevision.reportConfig and
      leaves reportConfig.page empty; navigation stays in reportConfig.navigationInfo.
    - Components: componentConfig[] with type, attributeConfig.componentAttribute
      (top, left, width, height), propertyConfig.componentProperty (dataset, dimensions,
      metrics, sort, filters, dateRangeDimension) and conceptDefs[] (the chart's fields).
    - Report-level components (shown on every page) are in report.componentConfig.
    - Filters are resources (report.resource.filter) referenced by id from the report,
      page and component filter lists.
    - Blends are report.resource.dataViewResource entries; each holds a join tree
      (treeQueryBlockConfig.join with left, right and a numeric type).
    - Data source fields: createdBy 1 is a source column, 2 a user calculated field,
      3 a derived field. A formula that is a bare t0.<column> reference is not a calculation.

Enum codes are only named when confirmed against an independent source (the SQL Looker
Studio sent, or the editor UI). Every other code is kept as its raw number.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

# Confirmed codes only. See wire/bi_pairs/looker_studio_to_omni/property_mapping.md.
AGGREGATION_NAMES = {6: "SUM"}          # 6 checked against the SQL sent to BigQuery
JOIN_TYPE_NAMES = {2: "full_outer"}     # 2 checked against the blend editor

DECORATIVE_TYPES = {"shape", "generic-shape", "arrow", "line", "image-component"}
TEXT_TYPES = {"simple-description"}
CONTROL_TYPES = {"dimension-filter", "simple-daterangepicker", "data-control", "input-box",
                 "slider-control", "checkbox-control", "dropdown-control", "button-control"}

GRID_COLUMNS = 24                        # same grid as the looker_to_omni pair

SECRET_KEY = re.compile(r"(password|secret|token|api_?key|apikey|private|credential)", re.I)
BARE_COLUMN = re.compile(r"^\s*t\d+\.[A-Za-z0-9_]+\s*$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class CaptureError(Exception):
    """The capture does not have the structure this extractor knows. Fail loudly."""


# ---------------------------------------------------------------------------
# Reading capture files
# ---------------------------------------------------------------------------

def read_capture_file(path: Path):
    """Return (header, body) for one captured response. body is parsed JSON or None."""
    text = path.read_text(encoding="utf-8")
    head, _, body = text.partition("\n")
    header = json.loads(head)
    body = body.lstrip()
    if body.startswith(")]}'"):
        body = body[4:]
    try:
        parsed = json.loads(body) if body.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return header, parsed


def first(paths):
    paths = sorted(paths)
    return paths[0] if paths else None


def report_config(rep: dict):
    """Return (config, revision). Published reports keep pages in publishedReportRevision."""
    rc = rep.get("reportConfig")
    if rc is None:
        raise CaptureError("getReport response has no reportConfig")
    if rc.get("page"):
        return rc, "draft"
    pub = (rep.get("publishedReportRevision") or {}).get("reportConfig")
    if pub and pub.get("page"):
        return pub, "published"
    raise CaptureError("getReport has no pages in reportConfig or publishedReportRevision")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def plain_text(fragment: str) -> str:
    """HTML text box content to plain text: tags removed, entities decoded, spaces collapsed."""
    t = re.sub(r"<br\s*/?>|</(div|p|li)>", "\n", fragment or "", flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in t.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def agg(code):
    if code is None:
        return None, None
    return code, AGGREGATION_NAMES.get(code)


def redact(params):
    out = []
    for p in params or []:
        key = p.get("key", "")
        val = p.get("value")
        if SECRET_KEY.search(key):
            val = "<redacted>"
        out.append({"key": key, "value": val})
    return sorted(out, key=lambda x: x["key"])


def grid(layout: dict, canvas_width: int) -> dict:
    """Pixel position on the Looker Studio canvas to a 24-column grid cell.

    One grid unit is canvas_width / 24 pixels, horizontally and vertically, so the
    proportions of the page are kept. x and w are clamped to the 24 columns; every
    tile is at least 1 x 1. content_mapping.md documents the rule.
    """
    unit = canvas_width / GRID_COLUMNS
    x = int(round(layout["left"] / unit))
    w = max(1, int(round(layout["width"] / unit)))
    x = min(max(x, 0), GRID_COLUMNS - 1)
    w = min(w, GRID_COLUMNS - x)
    y = max(0, int(round(layout["top"] / unit)))
    h = max(1, int(round(layout["height"] / unit)))
    return {"x": x, "y": y, "w": w, "h": h}


# ---------------------------------------------------------------------------
# Report side
# ---------------------------------------------------------------------------

def concept(cd: dict) -> dict:
    qtt = cd.get("queryTimeTransformation", {})
    dt = qtt.get("dataTransformation", {})
    disp = qtt.get("displayTransformation", {})
    code, name = agg(dt.get("aggregation"))
    out = {
        "name": cd.get("name"),
        "source_field": dt.get("sourceFieldName"),
        "aggregation": code,
        "aggregation_name": name,
        "formula": dt.get("textFormula"),
        "label": disp.get("displayName"),
    }
    return out


def labeled(prop: dict, key: str):
    names = []
    for lc in (prop.get(key) or {}).get("labeledConcepts", []):
        names.extend(lc.get("value", {}).get("conceptNames", []))
    return names


def component(c: dict, canvas_width: int, order: int) -> dict:
    ctype = c.get("type", "")
    attr = c.get("attributeConfig", {}).get("componentAttribute", {})
    layout = {k: attr.get(k, 0) for k in ("left", "top", "width", "height")}
    layout["z"] = order
    prop = c.get("propertyConfig", {}).get("componentProperty", {})
    ds = prop.get("dataset") or {}
    if ctype in DECORATIVE_TYPES:
        kind = "decorative"
    elif ctype in TEXT_TYPES:
        kind = "text"
    elif ctype in CONTROL_TYPES or ctype.endswith("-control") or ctype.endswith("-filter"):
        kind = "control"
    elif ds.get("datasetId"):
        kind = "data"
    else:
        kind = "decorative"
    concepts = {cd.get("name"): concept(cd) for cd in c.get("conceptDefs", [])}
    out = {
        "id": c.get("componentId"),
        "type": ctype,
        "kind": kind,
        "layout": layout,
        "grid": grid(layout, canvas_width),
    }
    if kind in ("data", "control"):
        dims = labeled(prop, "dimensions")
        mets = labeled(prop, "metrics")
        out["dataset"] = {"type_code": ds.get("datasetType"), "id": ds.get("datasetId")}
        out["dimensions"] = [concepts.get(n, {"name": n}) for n in dims]
        out["metrics"] = [concepts.get(n, {"name": n}) for n in mets]
        out["chart_fields"] = [concepts[n] for n in sorted(concepts) if n not in dims and n not in mets]
        out["date_range_dimension"] = prop.get("dateRangeDimension")
        out["sort"] = [{"field": s.get("sortColumn"), "direction_code": s.get("sortDir")}
                       for s in prop.get("sort", [])]
        out["filter_ids"] = list(prop.get("filters", []))
        out["inherit_filters"] = prop.get("inheritFilters", True)
        if "row" in prop:
            out["row_limit"] = prop.get("row")
        if prop.get("compareDateDuration"):
            out["comparison"] = prop.get("compareDateDuration")
    if kind == "text":
        dp = prop.get("descriptionProperty", {})
        out["text"] = plain_text(dp.get("text", ""))
    return out


def walk_components(items, canvas_width, counter):
    out = []
    for c in items or []:
        out.append(component(c, canvas_width, counter[0]))
        counter[0] += 1
        out.extend(walk_components(c.get("componentConfig"), canvas_width, counter))
    return out


def nav_pages(nav: dict):
    """Pages in display order with section and hidden flag."""
    pages = []

    def visit(items, section):
        for it in items or []:
            if "page" in it:
                p = it["page"]
                pages.append({"id": p.get("pageId"), "name": p.get("displayName"),
                              "section": section, "hidden": bool(p.get("hiddenFromViewer"))})
            if "section" in it:
                s = it["section"]
                visit(s.get("navItems"), s.get("displayName"))

    visit(nav.get("navItems"), None)
    return pages


def filters(resource: dict):
    out = []
    for e in (resource.get("filter") or {}).get("entry", []):
        v = e.get("value", {})
        fe = v.get("filterDefinition", {}).get("filterExpression", {})
        dt = fe.get("queryTimeTransformation", {}).get("dataTransformation", {})
        out.append({
            "id": e.get("key"),
            "name": v.get("name"),
            "datasource_id": v.get("datasourceId"),
            "field": dt.get("sourceFieldName"),
            "condition": fe.get("filterConditionType"),
            "include": fe.get("include"),
            "values": fe.get("stringValues", []) or fe.get("numberValues", []),
        })
    return sorted(out, key=lambda f: f["id"] or "")


def join_tree(node: dict) -> dict:
    """Blend join tree: a leaf query on one data source, or a join of two subtrees."""
    if "join" in node:
        j = node["join"]
        code = j.get("type")
        keys = []
        for kp in j.get("joinKeyPair", []) or j.get("joinKeyPairs", []) or []:
            keys.append({k: (v.get("queryTimeTransformation", {}).get("dataTransformation", {})
                             .get("sourceFieldName") if isinstance(v, dict) else v)
                         for k, v in kp.items()})
        return {"join_type": code, "join_type_name": JOIN_TYPE_NAMES.get(code),
                "keys": keys, "left": join_tree(j.get("left", {})), "right": join_tree(j.get("right", {}))}
    q = node.get("query", node)
    fields = []
    for c in q.get("concepts", []):
        dt = c.get("queryTimeTransformation", {}).get("dataTransformation", {})
        code, name = agg(dt.get("aggregation"))
        fields.append({"name": c.get("id", {}).get("name"), "source_field": dt.get("sourceFieldName"),
                       "aggregation": code, "aggregation_name": name})
    drd = (q.get("dateRangeDimension") or {}).get("queryTimeTransformation", {}) \
        .get("dataTransformation", {}).get("sourceFieldName")
    return {"datasource_id": q.get("datasourceId"), "fields": fields, "date_range_field": drd}


def blends(resource: dict):
    out = []
    for e in (resource.get("dataViewResource") or {}).get("entry", []):
        bd = e.get("value", {}).get("blockDatasource", {})
        dsb = bd.get("datasourceBlock", {})
        tree = None
        for b in bd.get("blocks", []):
            t = b.get("treeQueryBlockConfig")
            if t:
                tree = join_tree(t)
        out.append({
            "id": e.get("key"),
            "name": dsb.get("name"),
            "output_fields": [{"name": f.get("field", {}).get("name"), "label": f.get("outputName"),
                               "source": f.get("queryTimeTransformation", {}).get("dataTransformation", {})
                               .get("sourceFieldName")} for f in dsb.get("fields", [])],
            "tree": tree,
        })
    return sorted(out, key=lambda b: b["id"] or "")


def leaf_datasources(tree):
    if not tree:
        return []
    if "join_type" in tree:
        return leaf_datasources(tree["left"]) + leaf_datasources(tree["right"])
    return [tree["datasource_id"]] if tree.get("datasource_id") else []


# ---------------------------------------------------------------------------
# Data source side
# ---------------------------------------------------------------------------

def connection(block: dict) -> dict:
    cc = block.get("connectorBlockConfig", {}).get("connectorConfig", {})
    if "bigQueryConnectorConfig" in cc:
        bq = cc["bigQueryConnectorConfig"]
        sql_key = next((k for k, v in sorted(bq.items())
                        if isinstance(v, str) and re.match(r"\s*(select|with)\b", v, re.I)), None)
        out = {"connector": "bigquery_custom_sql" if sql_key and not bq.get("tableId") else "bigquery_table",
               "project": bq.get("projectId"), "dataset": bq.get("datasetId"), "table": bq.get("tableId"),
               "billing_project": bq.get("billingProjectId"),
               "processing_location_code": bq.get("processingLocation")}
        if sql_key:
            out["sql"] = bq[sql_key]
            out["sql_key"] = sql_key
        return out
    if "appsScriptAddonConnectorConfig" in cc:
        a = cc["appsScriptAddonConnectorConfig"]
        params = redact(a.get("configParams"))
        out = {"connector": "community_connector", "deployment_id": a.get("deploymentId"), "params": params}
        q = next((p["value"] for p in params if p["key"].lower() in ("query", "sql", "custom_query")), None)
        if q:
            out["sql"] = q
        return out
    if "sheetsConfig" in cc:
        s = cc["sheetsConfig"]
        meta = s.get("meta", {})
        return {"connector": "google_sheets", "spreadsheet_id": s.get("key"), "sheet_id": s.get("sheetId"),
                "spreadsheet_name": meta.get("spreadsheetName"), "worksheet_name": meta.get("worksheetName")}
    keys = sorted(k for k in cc if k.endswith("Config"))
    return {"connector": "other", "datasource_type_code": cc.get("datasourceType"), "config_keys": keys}


def ds_fields_from_block(dsb: dict):
    out = []
    for f in dsb.get("fields", []):
        formula = f.get("textFormula")
        code, name = agg(f.get("defaultAggregationType"))
        calc = f.get("createdBy") == 2 or (bool(formula) and not BARE_COLUMN.match(formula)
                                           and formula.strip().upper() != "COUNT(1)")
        out.append({"name": f.get("field", {}).get("name"), "label": f.get("outputName"),
                    "data_type_code": f.get("dataType"), "default_aggregation": code,
                    "default_aggregation_name": name, "description": f.get("description") or "",
                    "calculated": calc, "formula": formula if calc else None,
                    "created_by_code": f.get("createdBy"), "enabled": f.get("enabled", True)})
    return sorted(out, key=lambda x: x["name"] or "")


def ds_fields_from_schema(schema: dict):
    out = []
    for kind in ("dimensions", "metrics"):
        for f in schema.get("schema", {}).get(kind, []):
            code, name = agg(f.get("defaultAggregation"))
            out.append({"name": f.get("name"), "label": f.get("displayName"),
                        "data_type_code": f.get("dataType"),
                        "warehouse_type": f.get("underlyingConnectorDataType"),
                        "default_aggregation": code, "default_aggregation_name": name,
                        "description": (f.get("lookerProperties") or {}).get("description", ""),
                        "calculated": None, "formula": None})
    return sorted(out, key=lambda x: x["name"] or "")


def datasource(cap: Path, ds_id: str, schemas: dict, aliases: dict) -> dict:
    out = {"id": ds_id, "alias": aliases.get(ds_id), "name": None, "access": "not_captured",
           "connection": None, "fields": [], "field_source": "none"}
    f = first((cap / "datasources" / ds_id).glob("*getBlockDatasource*")) \
        if (cap / "datasources" / ds_id).is_dir() else None
    if f:
        header, body = read_capture_file(f)
        if header.get("status") == 200 and body:
            rev = body.get("published") or body.get("draft")
            if not rev:
                raise CaptureError(f"getBlockDatasource for {ds_id} has no published or draft revision")
            dsb = rev.get("datasourceBlock", {})
            out["access"] = "read"
            out["name"] = dsb.get("name")
            conns = [connection(b) for b in rev.get("blocks", []) if b.get("type") == 2]
            out["connection"] = conns[0] if len(conns) == 1 else {"connector": "multiple", "parts": conns}
            out["fields"] = ds_fields_from_block(dsb)
            out["field_source"] = "getBlockDatasource"
            out["has_unpublished_changes"] = bool(body.get("draft")) and bool(body.get("published")) \
                and body["draft"] != body["published"]
        elif header.get("status") == 403:
            out["access"] = "refused"
    if out["field_source"] == "none" and ds_id in schemas:
        out["fields"] = ds_fields_from_schema(schemas[ds_id])
        out["field_source"] = "getSchema"
    return out


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------

def extract(cap: Path) -> dict:
    meta = json.loads((cap / "meta.json").read_text()) if (cap / "meta.json").exists() else {}
    rf = first((cap / "report").glob("*getReport*"))
    if not rf:
        raise CaptureError(f"no getReport response in {cap / 'report'}")
    header, rep = read_capture_file(rf)
    if header.get("status") != 200 or not rep:
        raise CaptureError(f"getReport returned status {header.get('status')}")
    cfg, revision = report_config(rep)
    rc = rep["reportConfig"]
    sh = rc.get("shareable", {})
    report = cfg.get("report", {})
    rattr = report.get("attributeConfig", {}).get("reportAttribute", {})
    canvas_width = rattr.get("width") or 1200
    resource = report.get("resource", {})

    schemas = {}
    for f in sorted((cap / "report").glob("*getSchema*")):
        h, b = read_capture_file(f)
        if h.get("status") == 200 and b:
            ds_id = json.loads(h.get("post") or "{}").get("datasourceId")
            if ds_id and ds_id not in schemas:
                schemas[ds_id] = b
    aliases = {a.get("datasourceId"): a.get("alias") for a in resource.get("datasourceAlias", [])}

    page_defs = {p.get("pageId"): p.get("page", {}) for p in cfg.get("page", [])}
    pages = []
    nav = nav_pages(rc.get("navigationInfo", {}))
    nav_ids = [p["id"] for p in nav]
    for p in nav + [{"id": pid, "name": None, "section": None, "hidden": None}
                    for pid in page_defs if pid not in nav_ids]:
        pd = page_defs.get(p["id"])
        if pd is None:
            p.update({"defined": False, "components": []})
            pages.append(p)
            continue
        pp = pd.get("propertyConfig", {}).get("pageProperty", {})
        pa = pd.get("attributeConfig", {}).get("pageAttribute", {})
        p.update({
            "defined": True,
            "name": p["name"] or pa.get("name"),
            "dataset_id": (pp.get("dataset") or {}).get("datasetId"),
            "date_range_dimension": pp.get("dateRangeDimension"),
            "filter_ids": list(pp.get("filters", [])),
            "groups": [{"id": g.get("groupId"), "components": list(g.get("componentId", [])),
                        "child_groups": list(g.get("childGroupId", []))} for g in pd.get("groupConfig", [])],
            "components": walk_components(pd.get("componentConfig"), canvas_width, [0]),
        })
        pages.append(p)

    report_components = walk_components(report.get("componentConfig"), canvas_width, [0])
    blend_list = blends(resource)
    blend_ids = {b["id"] for b in blend_list}

    used = {}
    for p in pages:
        for c in p["components"]:
            did = (c.get("dataset") or {}).get("id")
            if did:
                used.setdefault(did, set()).add(c["id"])
    for c in report_components:
        did = (c.get("dataset") or {}).get("id")
        if did:
            used.setdefault(did, set()).add(c["id"])
    ds_ids = set(k for k in used if UUID.match(k or ""))
    for b in blend_list:
        ds_ids.update(leaf_datasources(b["tree"]))
    for f in filters(resource):
        if f["datasource_id"]:
            ds_ids.add(f["datasource_id"])
    ds_ids.update(d for d in meta.get("datasources", []) if UUID.match(d or ""))
    ds_ids -= blend_ids

    in_blends = {}
    for b in blend_list:
        for leaf_id in set(leaf_datasources(b["tree"])):
            in_blends[leaf_id] = in_blends.get(leaf_id, 0) + 1
    datasources = []
    for ds_id in sorted(ds_ids):
        d = datasource(cap, ds_id, schemas, aliases)
        d["used_by_components"] = len(used.get(ds_id, ()))
        d["used_by_blends"] = in_blends.get(ds_id, 0)
        datasources.append(d)

    all_components = [c for p in pages for c in p["components"]] + report_components
    kinds = {}
    for c in all_components:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    connectors = {}
    for d in datasources:
        k = (d["connection"] or {}).get("connector", "unknown") if d["access"] == "read" else d["access"]
        connectors[k] = connectors.get(k, 0) + 1
    chart_calcs = sum(1 for c in all_components
                      for f in c.get("metrics", []) + c.get("dimensions", []) + c.get("chart_fields", [])
                      if f.get("formula"))
    ds_calcs = sum(1 for d in datasources for f in d["fields"] if f.get("calculated"))

    out = {
        "extractor": {"name": "looker_studio_extract", "version": VERSION},
        "report": {
            "id": sh.get("id"),
            "name": sh.get("name"),
            "revision": revision,
            "unpublished_changes": bool(rep.get("hasChangesToPublish")),
            "modified_date": sh.get("modifiedDate"),
            "app_version": meta.get("app_version"),
            "captured_at": meta.get("captured_at"),
            "canvas": {"width": canvas_width, "height": rattr.get("height"),
                       "navigation_code": rattr.get("viewModeNav"), "scale_code": rattr.get("viewModeScale")},
            "theme_id": report.get("propertyConfig", {}).get("reportProperty", {}).get("themeConfig"),
            "filter_ids": list(report.get("propertyConfig", {}).get("reportProperty", {}).get("filters", [])),
        },
        "pages": pages,
        "report_components": report_components,
        "filters": filters(resource),
        "blends": blend_list,
        "parameters": resource.get("parameterResource", []) + resource.get("unifiedParameterResource", []),
        "datasources": datasources,
        "coverage": {
            "pages_failed": sorted(meta.get("failed_pages", [])),
            "pages_without_definition": [p["id"] for p in pages if not p["defined"]],
            "datasources_refused": [d["id"] for d in datasources if d["access"] == "refused"],
            "datasources_not_captured": [d["id"] for d in datasources if d["access"] == "not_captured"],
            "datasources_without_fields": [d["id"] for d in datasources if not d["fields"]],
        },
        "counts": {
            "pages": len(pages),
            "pages_hidden": sum(1 for p in pages if p["hidden"]),
            "components": len(all_components),
            "components_by_kind": dict(sorted(kinds.items())),
            "report_level_components": len(report_components),
            "chart_calculated_fields": chart_calcs,
            "datasource_calculated_fields": ds_calcs,
            "blends": len(blend_list),
            "parameters": len(resource.get("parameterResource", [])) + len(resource.get("unifiedParameterResource", [])),
            "filters": len(filters(resource)),
            "datasources": len(datasources),
            "datasources_by_connector": dict(sorted(connectors.items())),
        },
    }
    return out


def markdown(r: dict) -> str:
    rp, c, cov = r["report"], r["counts"], r["coverage"]
    lines = [f"# Looker Studio report: {rp['name']}", "",
             f"- Report ID: `{rp['id']}`",
             f"- Revision extracted: {rp['revision']}" + (" (unpublished changes exist)" if rp["unpublished_changes"] else ""),
             f"- Captured: {rp['captured_at']} (app version {rp['app_version']})",
             f"- Canvas: {rp['canvas']['width']} x {rp['canvas']['height']} px", "",
             "## Counts", "", "| Item | Count |", "|---|---|"]
    for k, v in c.items():
        if isinstance(v, dict):
            v = ", ".join(f"{kk}: {vv}" for kk, vv in v.items()) or "none"
        lines.append(f"| {k.replace('_', ' ')} | {v} |")
    lines += ["", "## Pages", "", "| # | Page | Section | Hidden | Data components |", "|---|---|---|---|---|"]
    for i, p in enumerate(r["pages"], 1):
        n = sum(1 for x in p["components"] if x["kind"] == "data")
        lines.append(f"| {i} | {p['name']} | {p['section'] or ''} | {'yes' if p['hidden'] else 'no'} | {n} |")
    lines += ["", "## Data sources", "", "| Data source | Connector | Access | Fields | Calculated | Components | Blends |",
              "|---|---|---|---|---|---|---|"]
    for d in r["datasources"]:
        conn = (d["connection"] or {}).get("connector", "")
        calc = sum(1 for f in d["fields"] if f.get("calculated"))
        lines.append(f"| {d['name'] or d['alias'] or d['id']} | {conn} | {d['access']} | {len(d['fields'])} "
                     f"| {calc} | {d['used_by_components']} | {d['used_by_blends']} |")
    if r["blends"]:
        lines += ["", "## Blends", ""]
        for b in r["blends"]:
            t = b["tree"] or {}
            jt = t.get("join_type_name") or f"code {t.get('join_type')}"
            lines.append(f"- {b['name']}: {len(leaf_datasources(t))} inputs, join {jt}")
    lines += ["", "## Coverage gaps", ""]
    gaps = [(k.replace("_", " "), v) for k, v in cov.items() if v]
    lines += [f"- {k}: {len(v)} ({', '.join(v[:5])}{'...' if len(v) > 5 else ''})" for k, v in gaps] or ["- none"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", required=True, help="capture folder for one report")
    ap.add_argument("--out", required=True, help="output folder for report.json and report.md")
    a = ap.parse_args(argv)
    cap, out = Path(a.capture), Path(a.out)
    try:
        r = extract(cap)
    except CaptureError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(r, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "report.md").write_text(markdown(r))
    print(f"{r['report']['name']}: {r['counts']['pages']} pages, {r['counts']['components']} components, "
          f"{r['counts']['datasources']} data sources -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Looker Studio to LookML converter (bi_migration, pair looker_studio_to_looker). EXPERIMENTAL.

Reads the report.json files looker_studio_extract.py writes (and, optionally, the ruled metric
catalogue from looker_studio_metrics.py) and writes:

    views/         one view per BigQuery table a data source reads (sql_table_name), and one per
                   custom SQL data source (derived_table); dimensions from the source columns, typed
                   from Looker Studio's data type codes; measures for the aggregations the charts
                   use; calculated fields translated to SQL where the formula is in the supported
                   subset (a ruled metric catalogue entry names the measure)
    models/        the model file: one explore per data source
    dashboards/    one LookML dashboard per report page: charts as elements on the same 24-column
                   grid, text boxes as text tiles, the date range control and dimension filter
                   controls as dashboard filters with listen
    needs_human.json, conversion_summary.json, dependencies.jsonl, parity_map.json

A data source that reads Looker (Looker Studio's Looker connector) needs no view: its charts point
at the existing explore, and each field's formula (t0.<view>.<field>) names the Looker field. A data
source Looker cannot read (Search Console, GA4, Sheets, community connectors such as Funnel.io) is
listed, with its charts. Blends are listed for a person.

parity_map.json links each chart to its element and maps each column of the chart's Route C
recording (looker_studio_parity.py) to the Looker field, so bi_parity.py contracts can be filled.

Deterministic and no AI call. The rules are in wire/bi_pairs/looker_studio_to_looker/.

Usage:
    python3 wire/scripts/ls_to_lookml.py convert --reports <report.json> [...] --out <dir>
        [--catalogue metric_catalogue.json] [--model NAME] [--connection NAME] [--include-root DIR]
    python3 wire/scripts/ls_to_lookml.py lint <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bi_ir  # noqa: E402

VERSION = "0.1.0"
TOOL = "lookerstudio"

# Looker Studio data type codes (confirmed against captured fields and the SQL Looker Studio sent to BigQuery)
DATA_TYPE = {0: "string", 1: "yesno", 2: "number", 3: "number", 8: "date", 9: "timestamp"}
# Aggregation codes: 6 is SUM (confirmed); the others are matched by name when the extractor names them
AGG = {"SUM": ("sum", "total"), "AVG": ("average", "average"), "MIN": ("min", "min"), "MAX": ("max", "max"),
       "COUNT_DISTINCT": ("count_distinct", "count_distinct"), "COUNT": ("count", "count")}
SORT_DESC = {1}                      # direction_code 1 is DESC (confirmed against the SQL)
# dateDuration offset units, confirmed against recorded date ranges: 3 is days (0 = today), 6 is months counted
# from the start of a month. Other units are listed for a person.
DURATION_UNIT = {3: "day", 6: "month"}


def duration_filter(d: dict):
    """A chart's own default date range as a Looker filter expression, or (None, reason)."""
    su, eu = DURATION_UNIT.get(d.get("startOffsetUnit")), DURATION_UNIT.get(d.get("endOffsetUnit"))
    so, eo = d.get("startOffset", 0), d.get("endOffset", 0)
    if su is None or eu is None:
        return None, f"date range units {d.get('startOffsetUnit')}/{d.get('endOffsetUnit')} not known"
    if eu == "day" and eo == 0:
        # From the start of the unit `so` back, to today. Looker has no filter expression that ends at today on
        # BigQuery ("N units ago to now" generates TIMESTAMP('now'), which BigQuery rejects), so the nearest is
        # "N+1 units": the same start, but it runs to the end of the current unit.
        return f"{so + 1} {su}s", (f"chart range: start of the {su} {so} {su}s back to today; Looker '{so + 1} {su}s' "
                                    f"also takes in rows dated after today in the current {su}")
    return None, f"date range {so} {su}s to {eo} {eu}s not mapped"
CHART = {"kpi-metric": "single_value", "scorecard": "single_value", "simple-linechart": "looker_line",
         "timeseries": "looker_line", "simple-barchart": "looker_column", "simple-combochart": "looker_column",
         "simple-piechart": "looker_pie", "simple-table": "looker_grid", "table": "looker_grid",
         "simple-areachart": "looker_area", "simple-scatterchart": "looker_scatter", "simple-donutchart": "looker_pie"}
CHART_ASSISTED = {"simple-combochart", "kpi-metric", "scorecard"}
RECORD_COUNT = re.compile(r"^datastudio_(blend_)?record_count")
# Looker Studio functions with a different name or shape in BigQuery SQL
FUNC = {"COUNT_DISTINCT": None, "NARY_MAX": "GREATEST", "NARY_MIN": "LEAST", "TODAY": "CURRENT_DATE",
        "LENGTH": "LENGTH", "LOWER": "LOWER", "UPPER": "UPPER", "TRIM": "TRIM", "CONCAT": "CONCAT",
        "SUBSTR": "SUBSTR", "REPLACE": "REPLACE", "IFNULL": "IFNULL", "COALESCE": "COALESCE", "IF": "IF",
        "SAFE_DIVIDE": "SAFE_DIVIDE", "ROUND": "ROUND", "ABS": "ABS", "SUM": "SUM", "AVG": "AVG", "MIN": "MIN",
        "MAX": "MAX", "COUNT": "COUNT", "CAST": "CAST", "DATE_TRUNC": "DATE_TRUNC", "DATETIME_TRUNC": "DATETIME_TRUNC",
        "EXTRACT": "EXTRACT", "CONTAINS_TEXT": None, "REGEXP_CONTAINS": "REGEXP_CONTAINS", "CASE": None}
AGG_FUNCS = {"SUM", "AVG", "MIN", "MAX", "COUNT", "COUNT_DISTINCT"}
SQL_WORDS = {"CASE", "WHEN", "THEN", "ELSE", "END", "AND", "OR", "NOT", "IN", "IS", "NULL", "TRUE", "FALSE", "AS",
             "LIKE", "DISTINCT", "INT64", "FLOAT64", "STRING", "DATE", "DATETIME", "TIMESTAMP", "NUMERIC", "BOOL",
             "MONTH", "WEEK", "DAY", "YEAR", "QUARTER"}


class Unsupported(Exception):
    pass


def safe_division(sql: str) -> str:
    """Looker Studio's division returns null on a zero divisor (it sends SAFE_DIVIDE to BigQuery); BigQuery's
    '/' raises an error. Rewrite every division with sqlglot, or a single top-level a / b without it."""
    if "/" not in sql:
        return sql
    try:
        import sqlglot
        from sqlglot import exp
        tree = sqlglot.parse_one(sql, read="bigquery")
        tree = tree.transform(lambda n: exp.SafeDivide(this=n.this, expression=n.expression) if isinstance(n, exp.Div) else n)
        return tree.sql(dialect="bigquery")
    except ImportError:
        m = re.fullmatch(r"\s*(\S+)\s*/\s*(\S+)\s*", sql)
        if m:
            return f"SAFE_DIVIDE({m.group(1)}, {m.group(2)})"
        raise Unsupported("division inside a larger formula needs sqlglot (python3 -m pip install sqlglot)")
    except Exception as e:  # noqa: BLE001  a formula sqlglot cannot parse is not translated
        raise Unsupported(f"formula did not parse ({type(e).__name__})")


def recording_column(cf: dict) -> str:
    """The column name looker_studio_parity.py gives a chart field in its Route C recording."""
    lab = cf.get("label") if cf.get("label") not in (None, "", "-") else (cf.get("source_field") or cf.get("name"))
    return re.sub(r"[^A-Za-z0-9]+", "_", lab).strip("_").lower() or cf.get("name")


def lk_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def quote_col(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"`{name}`"


def esc_filter(v) -> str:
    s = str(v).replace("^", "^^").replace(",", "^,").replace("%", "^%").replace("_", "^_")
    return "^-" + s[1:] if s.startswith("-") else s


TF_ALL = ["raw", "time", "date", "week", "month", "quarter", "year"]


def free_name(v, name):
    taken = set(v["dims"]) | set(v["measures"]) | set(v["groups"])
    for g in v["groups"]:
        taken |= {f"{g}_{tf}" for tf in TF_ALL}
    if name not in taken:
        return name
    n, i = f"{name}_calc", 2
    while n in taken:
        n, i = f"{name}_calc_{i}", i + 1
    return n


class Converter:
    def __init__(self, reports, model, connection, include_root="", catalogue=None, namespace="client"):
        self.reports = reports
        self.namespace = namespace
        self.model, self.connection = model, connection
        self.root = f"{include_root.strip('/')}/" if include_root.strip("/") else ""
        self.catalogue = catalogue or {}
        self.views, self.explores, self.ds_view = {}, {}, {}
        self.needs, self.deps, self.counts, self.parity = [], [], {}, []
        self.reported = set()

    def count(self, construct, cls):
        self.counts.setdefault(construct, {}).setdefault(cls, 0)
        self.counts[construct][cls] += 1

    def need(self, obj, construct, cls, reason, proposal=None):
        key = (obj, construct, reason)
        if key in self.reported:
            return
        self.reported.add(key)
        self.needs.append({"object": obj, "construct": construct, "class": cls, "reason": reason, "proposal": proposal})

    def ident(self, rid, *p):
        """lookerstudio:<namespace>:report:<id>[/<kind>:<id>]..., the identities the audit uses."""
        return bi_ir.identity(TOOL, self.namespace, "report", rid, *p)

    # -- data sources ------------------------------------------------------------------
    def source(self, rid, d):
        """The view (or Looker explore) behind a data source: ('view', name) | ('looker', model, explore) | None."""
        key = d["id"]
        if key in self.ds_view:
            return self.ds_view[key]
        conn = d.get("connection") or {}
        kind = conn.get("connector")
        obj = self.ident(rid, "datasource", d["id"])
        out = None
        if kind == "looker":
            out = ("looker", conn.get("model"), conn.get("explore"))
            self.count("looker_datasource", "mechanical")
            self.deps.append({"from": obj, "to": f"looker:{conn.get('model')}:explore:{conn.get('explore')}", "kind": "reads"})
        elif kind in ("bigquery_table", "bigquery_custom_sql"):
            if kind == "bigquery_table":
                table = ".".join(x for x in (conn.get("project"), conn.get("dataset"), conn.get("table")) if x)
                name = bi_ir.slug(conn.get("table") or d.get("name"))
                src = {"table": f"`{table}`"}
                ident_key = ("table", table)
            else:
                name = bi_ir.slug(d.get("name") or "custom_sql")
                src = {"derived_sql": (conn.get("sql") or "").strip().rstrip(";")}
                ident_key = ("sql", src["derived_sql"])
                if not src["derived_sql"]:
                    self.need(obj, "custom_sql", "redesign", "custom SQL data source with no SQL in the capture", None)
                    self.count("custom_sql_datasource", "redesign")
                    self.ds_view[key] = None
                    return None
                self.need(obj, "custom_sql", "assisted", "custom SQL data source became a view on its SQL: exact, not reusable",
                          "rebuild as a dbt model or as a view on the tables it reads")
            existing = next((n for n, v in self.views.items() if v["key"] == ident_key), None)
            if existing:
                out = ("view", existing)
            else:
                while name in self.views:
                    name = f"{name}_2"
                self.views[name] = {"key": ident_key, "source": src, "dims": {}, "groups": {}, "measures": {},
                                    "label": d.get("name"), "fields": {}}
                self.explores[name] = {"base": name, "label": d.get("name")}
                out = ("view", name)
                self.count(f"{kind}_datasource", "mechanical" if kind == "bigquery_table" else "assisted")
                self.deps.append({"from": obj, "to": f"looker:{self.model}:view:{name}", "kind": "contains"})
            self.add_fields(rid, d, out[1])
        else:
            self.count("unreachable_datasource", "redesign")
            self.need(obj, "unreachable_datasource", "redesign",
                      f"data source {d.get('name')!r} reads a connector Looker cannot query ({kind}): its charts are not converted",
                      "load the data into the warehouse (a pipeline task in the plan), or drop")
        self.ds_view[key] = out
        return out

    def add_fields(self, rid, d, view):
        v = self.views[view]
        plain = [f for f in d.get("fields", []) if not f.get("calculated") and not RECORD_COUNT.match(f["name"])]
        for f in sorted(plain, key=lambda x: x["name"]):
            col = f.get("label") or f["name"].strip("_")
            dname = bi_ir.slug(col)
            lt = DATA_TYPE.get(f.get("data_type_code"))
            if lt is None:
                lt = "string"
                self.need(self.ident(rid, "datasource", d["id"], "field", f["name"]), "unknown_type", "assisted",
                          f"data type code {f.get('data_type_code')} not known: emitted as a string", None)
            if lt in ("date", "timestamp"):
                v["groups"].setdefault(dname, {"label": col, "sql": f"${{TABLE}}.{quote_col(col)}", "datatype": lt})
                v["fields"][f["name"]] = ("group", dname, lt)
            else:
                v["dims"].setdefault(dname, {"type": lt, "label": col, "sql": f"${{TABLE}}.{quote_col(col)}"})
                v["fields"][f["name"]] = ("dim", dname, lt)
        for f in sorted((x for x in d.get("fields", []) if x.get("calculated")), key=lambda x: x["name"]):
            self.calculated(rid, d, view, f)

    # -- calculated fields ------------------------------------------------------------
    def translate(self, formula, view):
        """Looker Studio formula to BigQuery SQL on `view`; (sql, aggregate?) or Unsupported."""
        v = self.views[view]
        out, aggregate, refs = [], False, []
        toks = re.findall(r"t0\.[A-Za-z0-9_.]+|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*|\S", formula)
        i = 0
        while i < len(toks):
            t = toks[i]
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if t.startswith("t0."):
                ref = t[3:]
                hit = v["fields"].get(ref) or next((x for k, x in v["fields"].items() if k.strip("_") == ref.strip("_")), None)
                if hit is None:
                    raise Unsupported(f"reference to {ref}, which is not a column of the data source")
                kind, name, _ = hit
                refs.append(f"({v['calc_sql'][name]})" if kind == "calc" else
                            (f"${{{name}_raw}}" if kind == "group" else f"${{{name}}}"))
                out.append(f"LSREF{len(refs) - 1}X")
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t) and nxt == "(":
                up = t.upper()
                if up not in FUNC:
                    raise Unsupported(f"function {t}")
                if up in AGG_FUNCS:
                    aggregate = True
                if up == "COUNT_DISTINCT":
                    out.append("COUNT(DISTINCT ")
                    i += 2
                    continue
                if up == "CONTAINS_TEXT":
                    raise Unsupported("CONTAINS_TEXT")
                out.append(FUNC[up] or up)
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t):
                if t.upper() not in SQL_WORDS:
                    raise Unsupported(f"bare name {t}")
                out.append(t.upper())
            elif t.startswith('"'):
                out.append("'" + t[1:-1].replace("'", "\\'") + "'")
            else:
                out.append(t)
            i += 1
        sql = " ".join(out)
        sql = re.sub(r"\s+([,)])", r"\1", sql)
        sql = re.sub(r"\(\s+", "(", sql)
        sql = re.sub(r"(\b[A-Z_]+) \(", r"\1(", sql)
        sql = safe_division(sql)
        for i, r in enumerate(refs):
            sql = sql.replace(f"LSREF{i}X", r)
        return sql, aggregate

    def ruled_name(self, f, ds_name):
        """The metric catalogue's target_name for this field, when a ruled group covers it."""
        for g in self.catalogue.get("groups", []):
            if (g.get("ruling") or {}).get("decision") not in ("accept", "accepted", "approved"):
                continue
            for m in g.get("members", []):
                if m.get("field") in (f["name"], f.get("label")) and m.get("datasource") in (ds_name, None):
                    return g.get("target_name") or g.get("name")
        return None

    def calculated(self, rid, d, view, f):
        v = self.views[view]
        obj = self.ident(rid, "datasource", d["id"], "field", f["name"])
        formula = f.get("formula") or ""
        try:
            sql, aggregate = self.translate(formula, view)
        except Unsupported as e:
            self.count("calculated_field", "redesign")
            self.need(obj, "calculated_field", "redesign", f"calculated field {f.get('label')!r} not translated: {e}",
                      f"Looker Studio: {formula}")
            return
        name = bi_ir.slug(self.ruled_name(f, d.get("name")) or f.get("label") or f["name"])
        name = free_name(v, name)
        v.setdefault("calc_sql", {})[name] = sql
        if aggregate:
            v["measures"][name] = {"type": "number", "sql": sql, "label": f.get("label") or name}
            v["fields"][f["name"]] = ("measure", name, "number")
        else:
            lt = DATA_TYPE.get(f.get("data_type_code"), "string")
            v["dims"][name] = {"type": lt if lt in ("string", "number", "yesno") else "string", "label": f.get("label") or name,
                               "sql": sql}
            v["fields"][f["name"]] = ("calc", name, lt)
        self.count("calculated_field", "assisted")
        self.need(obj, "calculated_field", "assisted", f"calculated field {f.get('label')!r} translated to SQL",
                  f"Looker Studio: {formula}")

    # -- chart fields --------------------------------------------------------------------
    def field(self, rid, src, ds, cf, metric, chart_obj, date_range=False):
        """Looker field for a chart field: (looker field, recording column) or Unsupported."""
        name = cf.get("source_field") or ""
        label = next((f.get("label") for f in ds.get("fields", []) if f["name"] == name), None) or name.strip("_")
        if src[0] == "looker":
            f = next((f for f in ds.get("fields", []) if f["name"] == name), None)
            if f is None and RECORD_COUNT.match(name):
                raise Unsupported("Record Count on a Looker data source")
            m = re.fullmatch(r"t0\.([A-Za-z0-9_]+\.[A-Za-z0-9_]+)", (f or {}).get("formula") or "")
            if not m:
                raise Unsupported(f"field {name} has no Looker field reference")
            if metric and cf.get("aggregation_name") not in (None, "AUTO"):
                self.need(chart_obj, "looker_reaggregation", "assisted",
                          f"the chart aggregates Looker field {m.group(1)} again ({cf.get('aggregation_name')})", None)
            return m.group(1), label
        view = src[1]
        v = self.views[view]
        if RECORD_COUNT.match(name):
            v["measures"].setdefault("count", {"type": "count", "label": "Record Count"})
            return f"{view}.count", "Record Count"
        if cf.get("formula"):
            try:
                sql, aggregate = self.translate(cf["formula"], view)
            except Unsupported as e:
                raise Unsupported(f"chart formula {cf.get('label') or cf.get('name')}: {e}")
            n = free_name(v, bi_ir.slug(cf.get("label") or cf["name"]))
            v["measures"][n] = ({"type": "number", "sql": sql, "label": cf.get("label") or n} if aggregate else
                                {"type": AGG.get(cf.get("aggregation_name") or "SUM", ("sum", ""))[0], "sql": sql,
                                 "label": cf.get("label") or n})
            self.need(chart_obj, "chart_formula", "assisted", f"chart-level formula translated: {cf['formula']}", None)
            return f"{view}.{n}", cf.get("label") or cf["name"]
        hit = v["fields"].get(name)
        if hit is None:
            raise Unsupported(f"field {name} is not in the data source")
        kind, dname, lt = hit
        if kind == "measure":
            return f"{view}.{dname}", label
        if metric:
            agg = cf.get("aggregation_name") or ("SUM" if lt == "number" else None)
            if kind == "calc" and agg is None:
                agg = "SUM"
            if agg not in AGG:
                raise Unsupported(f"aggregation {cf.get('aggregation')} ({agg}) not known")
            lt_, prefix = AGG[agg]
            mname = f"{prefix}_{dname}"
            ref = f"${{{dname}_raw}}" if kind == "group" else f"${{{dname}}}"
            spec = {"type": lt_, "sql": ref, "label": f"{label} ({agg.lower().replace('_', ' ')})"}
            if agg == "COUNT":
                spec = {"type": "count", "label": f"{label} (count)", "filters": [(dname, "-NULL")]}
            v["measures"].setdefault(mname, spec)
            return f"{view}.{mname}", label
        if kind == "group":
            return f"{view}.{dname}_date" if date_range else f"{view}.{dname}_{'date' if lt == 'date' else 'time'}", label
        if date_range:
            # Looker Studio casts a text date range field to a date before filtering on it; a Looker date filter
            # needs a date, so the cast becomes a dimension group of its own
            gname = free_name(v, f"{dname}_as_date")
            if f"{dname}_as_date" in v["groups"]:
                gname = f"{dname}_as_date"
            v["groups"].setdefault(gname, {"label": f"{label} (as date)", "datatype": "date",
                                           "sql": f"DATE(SAFE_CAST(${{TABLE}}.{quote_col(label)} AS TIMESTAMP))"})
            self.need(chart_obj, "text_date_range", "assisted",
                      f"date range field {label} is text: filtered through a cast to a date, as Looker Studio does", None)
            return f"{view}.{gname}_date", label
        return f"{view}.{dname}", label

    # -- pages to dashboards ------------------------------------------------------------
    def convert(self):
        files = {}
        for r in self.reports:
            rid = r["report"]["id"]
            dss = {d["id"]: d for d in r.get("datasources", [])}
            blends = {b["id"]: b for b in r.get("blends", [])}
            pages = [p for p in r.get("pages", []) if not p.get("hidden")]
            for p in r.get("pages", []):
                if p.get("hidden"):
                    self.need(self.ident(rid, "page", p["id"]), "hidden_page", "drop", f"hidden page {p.get('name')!r} not migrated", None)
            seen = {}
            for p in pages:
                title = r["report"]["name"] if len(pages) == 1 else f"{r['report']['name']} - {p.get('name')}"
                seen[title] = seen.get(title, 0) + 1
                if seen[title] > 1:                 # pages may share a name ("Untitled Page")
                    title = f"{title} {seen[title]}"
                files.update(self.page(r, rid, p, title, dss, blends))
        files.update(self.render())
        return files

    def page(self, r, rid, p, title, dss, blends):
        elements, filters, date_listen, dim_controls = [], [], {}, []
        pobj = self.ident(rid, "page", p["id"])
        comps = sorted(p.get("components", []) + list(r.get("report_components", [])), key=lambda c: (c["grid"]["y"], c["grid"]["x"], c["id"]))
        for c in comps:
            g = c.get("grid") or {}
            pos = {"row": g.get("y", 0), "col": g.get("x", 0), "width": max(1, g.get("w", 1)), "height": max(1, g.get("h", 1))}
            cobj = self.ident(rid, "page", p["id"], "component", c["id"])
            if c["kind"] == "text":
                elements.append({"name": f"text_{bi_ir.slug(c['id'])}", "type": "text", "body_text": c.get("text") or "", **pos})
                self.count("text", "mechanical")
                continue
            if c["kind"] == "control":
                if c["type"] == "simple-daterangepicker":
                    filters.append(("date", c))
                elif c["type"] == "dimension-filter":
                    dim_controls.append(c)
                else:
                    self.count(f"{c['type']}_control", "drop")
                    self.need(cobj, "control", "drop", f"{c['type']} control not migrated", None)
                continue
            if c["kind"] != "data":
                self.count(f"{c['kind']}_component", "drop")
                self.need(cobj, c["kind"], "drop", f"{c['type']} not migrated", None)
                continue
            ds_ref = c.get("dataset") or {}
            if ds_ref.get("type_code") == 2 or ds_ref.get("id") in blends:
                self.count("blend_chart", "redesign")
                self.need(cobj, "blend", "redesign", f"chart on blend {blends.get(ds_ref.get('id'), {}).get('name')!r}: blends are not converted",
                          "model the join in an explore (the plan rules the keys and grain)")
                continue
            ds = dss.get(ds_ref.get("id"))
            if ds is None:
                self.count("chart", "redesign")
                self.need(cobj, "chart", "redesign", "chart with no data source in the capture", None)
                continue
            src = self.source(rid, ds)
            if src is None:
                self.count("chart", "redesign")
                self.need(cobj, "chart", "redesign", f"chart on data source {ds.get('name')!r}, which is not converted", None)
                continue
            try:
                fields, cols = [], {}
                for cf in c.get("dimensions", []):
                    f, _ = self.field(rid, src, ds, cf, False, cobj)
                    fields.append(f)
                    cols[recording_column(cf)] = f
                for cf in c.get("metrics", []):
                    f, _ = self.field(rid, src, ds, cf, True, cobj)
                    if f not in fields:
                        fields.append(f)
                    col = recording_column(cf)
                    cols[col if col not in cols else f"{col}_2"] = f
                by_name = {cf["name"]: f for cf, f in zip(c.get("dimensions", []) + c.get("metrics", []), fields)}
                sorts = [f"{by_name[s['field']]} {'desc' if s.get('direction_code') in SORT_DESC else 'asc'}"
                         for s in c.get("sort", []) if s.get("field") in by_name]
                date_field = None
                if c.get("date_range_dimension"):
                    cf = next((x for x in c.get("chart_fields", []) if x["name"] == c["date_range_dimension"]), None)
                    if cf:
                        date_field, _ = self.field(rid, src, ds, cf, False, cobj, date_range=True)
            except Unsupported as e:
                self.count("chart", "redesign")
                self.need(cobj, "chart", "redesign", f"chart not converted: {e}", None)
                continue
            model, explore = (src[1], src[2]) if src[0] == "looker" else (self.model, src[1])
            ctype = CHART.get(c["type"])
            cls = "assisted" if c["type"] in CHART_ASSISTED or ctype is None else "mechanical"
            if c["type"] in ("kpi-metric", "scorecard") and len(c.get("metrics", [])) > 1:
                self.need(cobj, "scorecard_comparison", "assisted", "scorecard with a comparison metric: the comparison is hand-finished", None)
            name = f"{bi_ir.slug(c['type'])}_{bi_ir.slug(c['id'])}"
            el = {"name": name, "title": c.get("title") or "", "model": model, "explore": explore,
                  "type": ctype or "looker_grid", "fields": fields}
            if not el["title"]:
                el.pop("title")
            if sorts:
                el["sorts"] = sorts
            dims = fields[:len(c.get("dimensions", []))]
            if len(dims) == 2 and ctype in ("looker_column", "looker_bar", "looker_line", "looker_area"):
                # a breakdown dimension: Looker Studio draws one series per value, as a Looker pivot does
                el["pivots"] = [dims[1]]
                self.need(cobj, "breakdown_series", "assisted",
                          "breakdown dimension became a pivot; Looker Studio draws only its top series (a style "
                          "setting the capture does not hold), Looker draws every series", "set a series limit or a filter")
            el["limit"] = c.get("row_limit") or 500
            el.update(pos)
            elements.append(el)
            if date_field and c.get("date_duration"):
                # the chart's own date range overrides the report's date control in Looker Studio
                expr, why = duration_filter(c["date_duration"])
                if expr:
                    el.setdefault("filters", {})[date_field] = expr
                    self.need(cobj, "chart_date_range", "assisted", why, None)
                    el.pop("listen", None)
                else:
                    self.need(cobj, "chart_date_range", "assisted", why, json.dumps(c["date_duration"]))
            elif date_field:
                date_listen[name] = (date_field, model, explore)
            self.count("chart", cls)
            self.parity.append({"report": rid, "page": p["id"], "component": c["id"], "dashboard": None,
                                "element": name, "model": model, "explore": explore, "fields": cols, "date_field": date_field,
                                "sorts": sorts, "limit": el["limit"]})
            self.deps.append({"from": cobj, "to": f"looker:{model}:explore:{explore}", "kind": "uses_dataset"})
        dash_filters = []
        if filters:
            if date_listen:
                first = next(iter(sorted(date_listen.items())))
                f0 = {"name": "Date range", "title": "Date range", "type": "field_filter", "default_value": "",
                      "allow_multiple_values": True, "required": False, "model": first[1][1], "explore": first[1][2],
                      "field": first[1][0]}
                dash_filters.append(f0)
                for el in elements:
                    if el.get("name") in date_listen:
                        el.setdefault("listen", {})["Date range"] = date_listen[el["name"]][0]
                self.count("date_range_control", "assisted")
                self.need(pobj, "date_range_default", "assisted",
                          "date range control became a dashboard filter; its default range is not in the capture",
                          "set the default (the Route C recordings show the range at capture time)")
            else:
                self.need(pobj, "date_range_control", "drop", "date range control with no chart that has a date range dimension", None)
        for c in dim_controls:
            ds = dss.get((c.get("dataset") or {}).get("id"))
            src = self.source(rid, ds) if ds else None
            cobj = self.ident(rid, "page", p["id"], "component", c["id"])
            if not src or not c.get("dimensions"):
                self.need(cobj, "dimension_control", "assisted", "dimension filter control not resolved", None)
                continue
            try:
                f, _ = self.field(rid, src, ds, c["dimensions"][0], False, cobj)
            except Unsupported as e:
                self.need(cobj, "dimension_control", "assisted", f"dimension filter control not converted: {e}", None)
                continue
            ftitle = f.split(".", 1)[1].replace("_", " ").title()
            model, explore = (src[1], src[2]) if src[0] == "looker" else (self.model, src[1])
            dash_filters.append({"name": ftitle, "title": ftitle, "type": "field_filter", "default_value": "",
                                 "allow_multiple_values": True, "required": False, "model": model, "explore": explore, "field": f})
            # a control filters every chart on the same data source on its page
            for el in elements:
                if el.get("explore") == explore and el.get("model") == model:
                    el.setdefault("listen", {})[ftitle] = f
            self.count("dimension_control", "mechanical")
        doc = [{"dashboard": bi_ir.slug(title), "title": title, "layout": "newspaper", "preferred_viewer": "dashboards-next",
                "description": f"Migrated from Looker Studio report {r['report']['name']} (ls_to_lookml {VERSION}, experimental)",
                **({"filters": dash_filters} if dash_filters else {}), "elements": elements}]
        for pe in self.parity:
            if pe["page"] == p["id"]:
                pe["dashboard"] = bi_ir.slug(title)
        self.count("page", "mechanical")
        models = {e.get("model") for e in elements if e.get("model")}
        folder = f"{self.root}dashboards"
        if models and self.model not in models and len(models) == 1:
            # Every chart reads one existing Looker model (Looker Studio's Looker connector). A LookML dashboard
            # belongs to the model that includes it, so it goes in a folder that model includes, not the new one.
            ext = next(iter(models))
            folder = f"{self.root}dashboards/{ext}"
            self.need(pobj, "external_model_dashboard", "assisted",
                      f"dashboard reads only the existing Looker model {ext}: written to {folder}/",
                      f'add include: "/{folder}/*.dashboard.lookml" to the {ext} model')
        elif len(models) > 1:
            self.need(pobj, "mixed_model_dashboard", "assisted",
                      f"dashboard reads more than one Looker model ({', '.join(sorted(models))}): dashboard filters on "
                      "fields of a model that does not include the dashboard are not reachable", "split the dashboard")
        return {f"{folder}/{bi_ir.slug(title)}.dashboard.lookml": yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)}

    # -- render --------------------------------------------------------------------------
    def render(self):
        files = {}
        for name in sorted(self.views):
            v = self.views[name]
            out = [f"view: {name} {{"]
            if "table" in v["source"]:
                out.append(f"  sql_table_name: {v['source']['table']} ;;")
            else:
                out += ["  derived_table: {", "    sql: " + v["source"]["derived_sql"].replace("\n", "\n      ") + " ;;", "  }"]
            for d in sorted(v["dims"]):
                dm = v["dims"][d]
                out += ["", f"  dimension: {d} {{", f"    type: {dm['type']}", f"    label: {lk_str(dm['label'])}",
                        f"    sql: {dm['sql']} ;;", "  }"]
            for g in sorted(v["groups"]):
                gm = v["groups"][g]
                tfs = ["raw", "date", "week", "month", "quarter", "year"] if gm["datatype"] == "date" else \
                    ["raw", "time", "date", "week", "month", "quarter", "year"]
                out += ["", f"  dimension_group: {g} {{", "    type: time", f"    timeframes: [{', '.join(tfs)}]",
                        f"    datatype: {gm['datatype']}", "    convert_tz: no" if gm["datatype"] == "date" else None,
                        f"    label: {lk_str(gm['label'])}", f"    sql: {gm['sql']} ;;", "  }"]
                out = [o for o in out if o is not None]
            for m in sorted(v["measures"]):
                mm = v["measures"][m]
                out += ["", f"  measure: {m} {{", f"    type: {mm['type']}", f"    label: {lk_str(mm['label'])}"]
                if mm.get("sql"):
                    out.append(f"    sql: {mm['sql']} ;;")
                for f, e in mm.get("filters") or []:
                    out.append(f"    filters: [{f}: {lk_str(e)}]")
                out.append("  }")
            out.append("}")
            files[f"{self.root}views/{name}.view.lkml"] = "\n".join(out) + "\n"
        mo = [f"connection: {lk_str(self.connection)}", "", f'include: "/{self.root}views/*.view.lkml"',
              f'include: "/{self.root}dashboards/*.dashboard.lookml"']
        for x in sorted(self.explores):
            mo += ["", f"explore: {x} {{", f"  label: {lk_str(self.explores[x]['label'])}", "}"]
        files[f"models/{self.model}.model.lkml"] = "\n".join(mo) + "\n"
        return files


def lint(lookml_dir: Path):
    found = sorted(list(Path(lookml_dir).rglob("*.lkml")) + list(Path(lookml_dir).rglob("*.lookml")))
    if not found:
        return [f"{lookml_dir}: no LookML files (nothing was converted, or the wrong folder)"]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mb_to_lookml import duplicate_fields  # one rule for every pair that writes LookML
    rules = [(re.compile(r"\bt0\.[A-Za-z_]"), "Looker Studio field reference t0."),
             (re.compile(r"\bqt_[a-z0-9]{6,}\b"), "Looker Studio chart field id"),
             (re.compile(r"datastudio_[a-z_]*record_count"), "Looker Studio record count field"),
             (re.compile(r"\b(COUNT_DISTINCT|NARY_MAX|NARY_MIN|CONTAINS_TEXT)\s*\("), "Looker Studio function")]
    problems = []
    for p in found:
        text = p.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            for rx, what in rules:
                if rx.search(line):
                    problems.append(f"{p.relative_to(lookml_dir)}:{i}: {what}: {line.strip()[:160]}")
        if p.name.endswith(".view.lkml"):
            problems += [f"{p.relative_to(lookml_dir)}: field {n} is defined twice (Looker: 'Redefinition of field')"
                         for n in duplicate_fields(text)]
    return problems


def write_jsonl(path: Path, rows):
    path.write_text("".join(u + "\n" for u in sorted({json.dumps(r, sort_keys=True) for r in rows})))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("--reports", nargs="+", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--catalogue")
    c.add_argument("--namespace", default="client", help="client slug for identities (lookerstudio:<namespace>:...)")
    c.add_argument("--model", default="looker_studio_migration")
    c.add_argument("--connection", default="warehouse")
    c.add_argument("--include-root", default="")
    lt = sub.add_parser("lint")
    lt.add_argument("lookml_dir")
    a = ap.parse_args(argv)
    if a.cmd == "lint":
        probs = lint(Path(a.lookml_dir))
        for p in probs:
            print("FAIL", p)
        print(f"{'FAIL' if probs else 'PASS'}: {len(probs)} problem(s) in emitted LookML")
        return 1 if probs else 0
    reports = [json.loads(Path(p).read_text()) for p in sorted(a.reports)]
    reports.sort(key=lambda r: r["report"]["id"])
    cat = json.loads(Path(a.catalogue).read_text()) if a.catalogue else None
    cv = Converter(reports, bi_ir.slug(a.model), a.connection, a.include_root, cat, a.namespace)
    files = cv.convert()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    cv.needs.sort(key=lambda n: (n["object"], n["construct"], n["reason"]))
    summary = {"converter": "ls_to_lookml", "version": VERSION, "model": cv.model,
               "counts": {k: dict(sorted(v.items())) for k, v in sorted(cv.counts.items())},
               "views": len(cv.views), "explores": len(cv.explores),
               "dashboards": sum(1 for f in files if f.endswith(".dashboard.lookml")), "needs_human": len(cv.needs)}
    (out / "needs_human.json").write_text(json.dumps(cv.needs, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "conversion_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    (out / "parity_map.json").write_text(json.dumps(sorted(cv.parity, key=lambda x: (x["report"], x["page"], x["component"])),
                                                    indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    write_jsonl(out / "dependencies.jsonl", cv.deps)
    print(f"{summary['views']} views, {summary['explores']} explores, {summary['dashboards']} dashboards, "
          f"{summary['needs_human']} needs_human -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

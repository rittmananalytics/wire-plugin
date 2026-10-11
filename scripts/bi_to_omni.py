#!/usr/bin/env python3
"""
Omni writer for the Tableau to Omni and Metabase to Omni pairs (bi_migration, experimental).

Deterministic: the same snapshot gives byte-identical output. No AI call.

The Tableau reader (twb_to_lookml.py) and the Metabase reader (mb_to_lookml.py) work out the model from
the source tool: which tables become views, which columns, calculations and aggregations become fields,
how the views join, and what each dashboard tile asks for. This script takes that converted model before
it is rendered as LookML and writes an Omni model and Omni dashboard documents from it directly:

    <out>/<prefix><view>.query.view    one per table or SQL source, bound as a query view (default), or
    <out>/<schema>/<prefix><view>.view with --bind schema (schema and table_name)
    <out>/<prefix><topic>.topic        one per explore the reader built (data source group, Metabase table)
    <out>/relationships.yaml           the joins, with relationship and join type
    <out>/documents/<slug>.json        one Omni document body per dashboard (or tab), for
                                       omni documents v2-create <model-id> "<title>" --body "$(cat ...)"
    <out>/needs_human.json             the reader's items plus everything this writer did not emit
    <out>/parity_map.json              per tile: source id, document, query key, topic, Omni fields
    <out>/conversion_summary.json      counts

Omni naming, not LookML naming: a dimension on a table column takes the column's name (Omni auto-maps a
column by name), the source tool's caption becomes its label, and a measure or calculation whose name
would collide with a column is suffixed rather than allowed to shadow it (a measure named after its own
column refers to itself in Omni). Views are query views by default (`SELECT * FROM <table>`), because on a
git-connected Omni model the schema view's file path already belongs to Omni's own generated view.

Omni facts relied on are the ones in wire/bi_pairs/looker_to_omni/translation_guide.md and the document
shapes read back from Omni with `omni documents v2-get` (October 2026).

Usage:
    python3 wire/scripts/bi_to_omni.py convert --source tableau --snapshot <dir> --out <dir>
        [--site S] [--dialect bigquery|snowflake] [--workbooks a,b] [--datasets a,b]
        [--prefix tableau_omni__] [--bind query|schema]
    python3 wire/scripts/bi_to_omni.py convert --source metabase --snapshot <dir> --out <dir>
        [--database N] [--dashboards 1,2] [--cards 3,4] [--prefix ...] [--bind query|schema]
    python3 wire/scripts/bi_to_omni.py lint <out_dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bi_ir  # noqa: E402
import lookml_to_omni as l2o  # noqa: E402

VERSION = "0.1.0"

AGG = {"sum": "sum", "count": "count", "count_distinct": "count_distinct", "average": "average",
       "min": "min", "max": "max", "median": "median", "percentile": "percentile", "list": "list"}
JOIN = {"left_outer": "always_left", "inner": "inner", "full_outer": "full_outer", "cross": "cross"}
REL = {"many_to_one": "many_to_one", "one_to_one": "one_to_one", "one_to_many": "one_to_many",
       "many_to_many": "many_to_many"}
FORMAT = dict(l2o.VALUE_FORMAT_NAME)
TIMEFRAME = {k: v for k, v in l2o.TIMEFRAMES.items()}
TF_TOKENS = sorted(TIMEFRAME, key=len, reverse=True)
OMNI_TIMEFRAMES = {"raw", "date", "week", "month", "quarter", "year", "hour", "minute", "second", "millisecond",
                   "day_of_week_name", "day_of_week_num", "day_of_month", "day_of_quarter", "day_of_year",
                   "hour_of_day", "month_name", "month_num", "quarter_of_year", "fiscal_quarter", "fiscal_year"}
OMNI_AGGREGATES = {"sum", "count", "count_distinct", "average", "min", "max", "median", "list", "percentile",
                   "sum_distinct_on", "average_distinct_on", "median_distinct_on", "percentile_distinct_on"}

# Chart types: the source tile's type, as the readers name it, to Omni's chartType and visType
CHART = {"looker_column": "column", "looker_bar": "bar", "looker_line": "line", "looker_area": "area",
         "looker_pie": "pie", "single_value": "kpi", "looker_grid": "table", "table": "table",
         "looker_scatter": "point"}
ROW_SCALE = 6           # source grid rows to Omni grid units; heights are hand-finished (content_mapping.md)

LIQUID = re.compile(r"\{%|%\}|\{\{|\}\}")
TABLE_COL = re.compile(r"\$\{TABLE\}\.(`[^`]+`|\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_]*)")
FIELD_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?\}")
CONDITION = re.compile(r"\{%\s*condition\s+(\w+)\s*%\}(.*?)\{%\s*endcondition\s*%\}", re.S)
PARAMETER = re.compile(r"\{%\s*parameter\s+(\w+)\s*%\}")
SQL_TABLE = re.compile(r"\$\{(\w+)\.SQL_TABLE_NAME\}")
PLAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class Skip(Exception):
    pass


def key(*parts) -> str:
    """A stable short key (instanceKey, control id) from its parts."""
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# The converted model, normalised from either reader
# ---------------------------------------------------------------------------

def normalise(views: dict, tool: str) -> dict:
    """Both readers keep views as {source, dims, measures, params} plus, for Metabase, groups and filters;
    Tableau marks a date group with dims[n]["group"]. Return {view: {source, label, dims, times, measures,
    params, filters}}."""
    out = {}
    for name, v in views.items():
        dims, times = {}, {}
        for n, d in v.get("dims", {}).items():
            (times if d.get("group") else dims)[n] = d
        for n, g in (v.get("groups") or {}).items():
            times[n] = g
        out[name] = {"source": v["source"], "label": v.get("label"), "dims": dims, "times": times,
                     "measures": v.get("measures", {}), "params": v.get("params", {}),
                     "filters": v.get("filters", {})}
    return out


class Writer:
    def __init__(self, tool: str, views: dict, explores: dict, docs: list, dialect: str, prefix: str = "",
                 bind: str = "query", needs=None, counts=None):
        self.tool, self.dialect, self.prefix, self.bind = tool, dialect, prefix, bind
        self.views = normalise(views, tool)
        self.explores = self.normal_explores(explores)
        self.docs = docs
        self.needs = list(needs or [])
        self.counts = {}
        self.names = {}          # (view, source field name) -> Omni field name
        self.time_names = {}     # (view, source time group) -> Omni field name
        self.measure_names = {}  # (view, source measure) -> Omni measure name
        self.skipped = set()     # (view, source field) not emitted
        self.emitted = {}        # view -> {"dimensions": {...}, "measures": {...}}
        self.extra_columns = {}  # view -> raw columns declared hidden
        self.parity = []

    # -- bookkeeping ---------------------------------------------------------------------------
    def count(self, construct, cls):
        self.counts.setdefault(construct, {}).setdefault(cls, 0)
        self.counts[construct][cls] += 1

    def need(self, obj, construct, cls, reason, proposal=None):
        self.needs.append({"object": obj, "construct": construct, "class": cls, "reason": reason,
                           "proposal": proposal, "writer": "bi_to_omni"})

    def vname(self, v: str) -> str:
        return f"{self.prefix}{v}"

    def ident(self, kind, name):
        return f"omni:{self.prefix.rstrip('_') or self.tool}:{kind}:{name}"

    @staticmethod
    def normal_explores(explores: dict) -> dict:
        """Tableau keeps joins as a list of {view, type, sql_on, relationship}; Metabase as {name: {from?, type,
        sql_on, relationship}}. Return {explore: {base, label, joins: [{name, view, type, sql_on, relationship}]}}."""
        out = {}
        for x, e in explores.items():
            joins = e.get("joins") or []
            if isinstance(joins, dict):
                js = [{"name": n, "view": j.get("from") or n, **{k: j.get(k) for k in ("type", "sql_on", "relationship")}}
                      for n, j in sorted(joins.items())]
            else:
                js = [{"name": j["view"], "view": j["view"], **{k: j.get(k) for k in ("type", "sql_on", "relationship")}}
                      for j in joins]
            out[x] = {"base": e["base"], "label": e.get("label") or x, "joins": js}
        return out

    # -- names -----------------------------------------------------------------------------------
    def plan_names(self):
        """Columns take their column name; everything else keeps its name unless that collides."""
        for vn, v in self.views.items():
            used = set()
            column = {}
            for n, d in list(v["dims"].items()) + list(v["times"].items()):
                m = TABLE_COL.fullmatch((d.get("sql") or "").strip())
                if m and PLAIN.fullmatch(m.group(1).strip('`"')):
                    column[n] = m.group(1).strip('`"')
            for n in sorted(column):
                c = column[n]
                if c in used:          # two captions on one column: keep the second under its own name
                    continue
                used.add(c)
                (self.time_names if n in v["times"] else self.names)[(vn, n)] = c
            # a raw column that a derived field reads but no field shows (TIMESTAMP_SECONDS(${TABLE}.ts)) is
            # declared hidden, so the reference resolves and the derived field cannot take its name
            extra = set()
            for n, d in list(v["dims"].items()) + list(v["times"].items()) + list(v["measures"].items()):
                if n in column:
                    continue
                for m in TABLE_COL.finditer(d.get("sql") or ""):
                    c = m.group(1).strip('`"')
                    if PLAIN.fullmatch(c) and c not in used:
                        extra.add(c)
            used |= extra
            self.extra_columns[vn] = sorted(extra)
            for n in sorted(set(v["dims"]) | set(v["times"])):
                if (vn, n) in self.names or (vn, n) in self.time_names:
                    continue
                name, i = n, 2
                if name in used:
                    name = f"{n}_calc"
                while name in used:
                    name, i = f"{n}_calc_{i}", i + 1
                used.add(name)
                (self.time_names if n in v["times"] else self.names)[(vn, n)] = name
            for n in sorted(v["measures"]):
                name, i = n, 2
                if name in used:
                    name = f"{n}_measure"
                while name in used:
                    name, i = f"{n}_measure_{i}", i + 1
                used.add(name)
                self.measure_names[(vn, n)] = name

    def field(self, view: str, name: str):
        """Omni (view, field[, timeframe]) for a source-model field name on a view, or None."""
        if (view, name) in self.measure_names:
            return self.vname(view), self.measure_names[(view, name)], None
        if (view, name) in self.names:
            return self.vname(view), self.names[(view, name)], None
        if (view, name) in self.time_names:
            return self.vname(view), self.time_names[(view, name)], None
        for tf in TF_TOKENS:
            if name.endswith("_" + tf) and (view, name[: -len(tf) - 1]) in self.time_names:
                return self.vname(view), self.time_names[(view, name[: -len(tf) - 1])], TIMEFRAME[tf] or "raw"
        return None

    def ref(self, view: str, name: str) -> str:
        """`view.field` or `view.field[timeframe]` for a dashboard query; Skip when the field is not emitted."""
        if (view, name) in self.skipped:
            raise Skip(f"{view}.{name} was not emitted")
        f = self.field(view, name)
        if f is None:
            raise Skip(f"{view}.{name} has no Omni field")
        v, n, tf = f
        return f"{v}.{n}" if tf in (None, "raw") else f"{v}.{n}[{tf}]"

    def sql(self, sql: str, view: str, aliases=None) -> str:
        """Source-model SQL to Omni SQL: ${TABLE}.col -> ${col}; ${view.field_tf} -> ${view'.field[tf]};
        ${field} -> ${field'}. Liquid (parameters, templated filters) is not translated: Skip."""
        s = (sql or "").strip()
        if s.endswith(";;"):
            s = s[:-2].strip()
        if LIQUID.search(s):
            raise Skip("uses a parameter or templated filter (Liquid); Omni templated filters are written by hand")

        def col(m):
            c = m.group(1).strip('`"')
            if PLAIN.fullmatch(c):
                return "${" + c + "}"
            return m.group(1)

        aliases = aliases or {}

        def fld(m):
            a, b = m.group(1), m.group(2)
            vw, nm = (a, b) if b else (view, a)
            alias = None
            if vw in aliases:
                alias, vw = vw, aliases[vw]
            if vw not in self.views:
                return m.group(0)
            if (vw, nm) in self.skipped:
                raise Skip(f"refers to {vw}.{nm}, which was not emitted")
            f = self.field(vw, nm)
            if f is None:
                return m.group(0)       # a raw column reference already rewritten above
            v2, n2, tf = f
            if alias:
                v2 = self.vname(alias)
            body = f"{n2}[{tf}]" if tf else n2
            return "${" + (f"{v2}.{body}" if b else body) + "}"

        # source-model field references first, then raw columns (a column name is not a field name)
        return TABLE_COL.sub(col, FIELD_REF.sub(fld, s))

    # -- views -----------------------------------------------------------------------------------
    def source_sql(self, vn: str):
        src = self.views[vn]["source"]
        if "table" in src:
            return f"SELECT * FROM {src['table']}", None
        sql = src["derived_sql"]
        notes = []
        if CONDITION.search(sql):
            sql = CONDITION.sub("TRUE", sql)
            notes.append("templated filter(s) replaced by TRUE")
        if PARAMETER.search(sql):
            params = self.views[vn]["params"]

            def p(m):
                d = (params.get(m.group(1)) or {}).get("default_value")
                if d is None:
                    return "NULL"
                return d if re.fullmatch(r"-?\d+(\.\d+)?", str(d)) else "'" + str(d).replace("'", "''") + "'"
            sql = PARAMETER.sub(p, sql)
            notes.append("parameter(s) replaced by their default value")

        def nested(m):
            other = m.group(1)
            if other in self.views:
                inner, _ = self.source_sql(other)
                return f"({inner})"
            return m.group(0)
        sql = SQL_TABLE.sub(nested, sql)
        return sql, ("; ".join(notes) or None)

    def schema_table(self, table: str):
        parts = [p.strip("`\"") for p in re.split(r"\.(?=(?:[^`]*`[^`]*`)*[^`]*$)", table.strip("`"))]
        parts = [p for x in parts for p in x.split(".")]
        return (parts[-2] if len(parts) > 1 else None), parts[-1]

    def write_views(self, files: dict):
        for vn in sorted(self.views):
            v = self.views[vn]
            body = OrderedDict()
            if v.get("label"):
                body["label"] = v["label"]
            src = v["source"]
            if self.bind == "schema" and "table" in src:
                schema, table = self.schema_table(src["table"])
                body["schema"] = schema
                body["table_name"] = table
                path = f"{schema}/{self.vname(vn)}.view"
            else:
                sql, note = self.source_sql(vn)
                body["sql"] = sql
                path = f"{self.vname(vn)}.query.view"
                if note:
                    self.need(self.ident("view", self.vname(vn)), "query_view_sql", "assisted",
                              f"SQL source bound as a query view; {note}",
                              "recreate as an Omni templated filter, or keep the view without it")
            dims, measures = OrderedDict(), OrderedDict()
            for n in sorted(v["dims"]):
                d = v["dims"][n]
                out = OrderedDict()
                name = self.names[(vn, n)]
                m = TABLE_COL.fullmatch((d.get("sql") or "").strip())
                plain = bool(m and m.group(1).strip('`"') == name)
                try:
                    if not plain:
                        out["sql"] = self.sql(d.get("sql") or "", vn) if not m or PLAIN.fullmatch(
                            m.group(1).strip('`"')) else m.group(1)
                        if m and not PLAIN.fullmatch(m.group(1).strip('`"')):
                            self.need(self.ident("field", f"{self.vname(vn)}.{name}"), "quoted_column", "assisted",
                                      f"column {m.group(1)} is not a plain name: the dimension reads it quoted",
                                      "check the field in Omni, or rename the column in the warehouse")
                except Skip as e:
                    self.skipped.add((vn, n))
                    self.count("dimension", "assisted")
                    self.need(self.ident("field", f"{self.vname(vn)}.{name}"), "dimension", "assisted",
                              f"dimension {d.get('label') or n} not emitted: {e}", d.get("sql"))
                    continue
                if d.get("label") and d["label"] != name:
                    out["label"] = d["label"]
                if d.get("description"):
                    out["description"] = d["description"]
                if d.get("primary_key"):
                    out["primary_key"] = True
                if d.get("hidden"):
                    out["hidden"] = True
                dims[name] = out
                self.count("dimension", "mechanical" if plain else "assisted")
            for c in self.extra_columns.get(vn, []):
                dims[c] = OrderedDict([("hidden", True)])
                self.count("dimension", "mechanical")
            for n in sorted(v["times"]):
                d = v["times"][n]
                out = OrderedDict()
                name = self.time_names[(vn, n)]
                m = TABLE_COL.fullmatch((d.get("sql") or "").strip())
                plain = bool(m and m.group(1).strip('`"') == name)
                try:
                    if not plain:
                        out["sql"] = self.sql(d.get("sql") or "", vn)
                except Skip as e:
                    self.skipped.add((vn, n))
                    self.count("time_dimension", "assisted")
                    self.need(self.ident("field", f"{self.vname(vn)}.{name}"), "time_dimension", "assisted",
                              f"date field {d.get('label') or n} not emitted: {e}", d.get("sql"))
                    continue
                if d.get("label") and d["label"] != name:
                    out["label"] = d["label"]
                if d.get("description"):
                    out["description"] = d["description"]
                dims[name] = out
                self.count("time_dimension", "mechanical" if plain else "assisted")
            for n in sorted(v["measures"]):
                mm = v["measures"][n]
                name = self.measure_names[(vn, n)]
                out = OrderedDict()
                mtype = mm.get("type")
                try:
                    if mtype == "number":
                        out["sql"] = self.sql(mm.get("sql") or "", vn)
                    elif mtype in AGG:
                        if mm.get("sql"):
                            out["sql"] = self.sql(mm["sql"], vn)
                        out["aggregate_type"] = AGG[mtype]
                        if mtype == "percentile" and mm.get("percentile"):
                            out["percentile"] = mm["percentile"]
                    else:
                        raise Skip(f"measure type {mtype} has no Omni aggregate")
                    flt = OrderedDict()
                    for f, e in mm.get("filters") or []:
                        fv, fn = (f.split(".", 1) if "." in f else (vn, f))
                        target = self.field(fv, fn)
                        if target is None or (fv, fn) in self.skipped:
                            raise Skip(f"filter on {f}, which has no Omni field")
                        boolean = (self.views.get(fv, {}).get("dims", {}).get(fn, {}).get("type") == "yesno")
                        op = l2o.translate_filter_value(e, boolean)
                        if op is None:
                            raise Skip(f"filter {f}: {e!r} has no mechanical Omni form")
                        tv, tn, tf = target
                        fkey = (tn if tv == self.vname(vn) else f"{tv}.{tn}") + (f"[{tf}]" if tf and tf != "raw" else "")
                        flt[fkey] = op
                    if flt:
                        out["filters"] = flt
                except Skip as e:
                    self.skipped.add((vn, n))
                    self.count("measure", "assisted")
                    self.need(self.ident("field", f"{self.vname(vn)}.{name}"), "measure", "assisted",
                              f"measure {mm.get('label') or n} not emitted: {e}", mm.get("sql"))
                    continue
                if mm.get("label") and mm["label"] != name:
                    out["label"] = mm["label"]
                if mm.get("description"):
                    out["description"] = mm["description"]
                fmt = self.format(mm.get("format"))
                if fmt:
                    out["format"] = fmt
                measures[name] = out
                self.count("measure", "mechanical" if mtype in ("sum", "count", "count_distinct", "average", "min", "max")
                           else "assisted")
            for pn in sorted(v["params"]):
                self.count("parameter", "assisted")
                self.need(self.ident("field", f"{self.vname(vn)}.{pn}"), "parameter", "assisted",
                          f"parameter {v['params'][pn].get('label') or pn}: not emitted",
                          "an Omni templated filter (Mustache block) or a dashboard control")
            for fn in sorted(v["filters"]):
                self.count("templated_filter", "assisted")
                self.need(self.ident("field", f"{self.vname(vn)}.{fn}"), "templated_filter", "assisted",
                          f"templated filter {v['filters'][fn].get('label') or fn}: not emitted",
                          "an Omni templated filter in the query view's SQL")
            if dims:
                body["dimensions"] = dims
            if measures:
                body["measures"] = measures
            self.emitted[self.vname(vn)] = {"dimensions": dims, "measures": measures}
            files[path] = l2o.dump_yaml(body)
            self.count("view", "mechanical" if "table" in src else "assisted")

    def format(self, fmt):
        if not fmt:
            return None
        if fmt in FORMAT:
            return FORMAT[fmt]
        if self.tool == "tableau":
            import twb_to_lookml
            name = twb_to_lookml.value_format(fmt)
            return FORMAT.get(name) if name else None
        return None

    # -- topics and relationships ----------------------------------------------------------------
    def write_topics(self, files: dict):
        rels, seen = [], set()
        for x in sorted(self.explores):
            e = self.explores[x]
            base = e["base"]
            tree = OrderedDict()
            parent_of = {}
            for j in e["joins"]:
                if not j.get("sql_on"):
                    self.count("join", "assisted")
                    continue          # the reader listed it (sql_on left for a person)
                aliases = {j["name"]: j["view"]} if j["name"] != j["view"] else {}
                try:
                    on = self.sql(j["sql_on"], base, aliases)
                except Skip as e2:
                    self.count("join", "assisted")
                    self.need(self.ident("topic", self.vname(x)), "join", "assisted",
                              f"join {j['name']} not emitted: {e2}", j["sql_on"])
                    continue
                refs = {m.group(1) for m in FIELD_REF.finditer(j["sql_on"]) if m.group(2)}
                parent = next((r for r in sorted(refs) if r not in (j["name"], j["view"])), base)
                parent_of[j["name"]] = parent
                alias = j["name"] if j["name"] != j["view"] else None
                rel = OrderedDict([("join_from_view", self.vname(parent)), ("join_to_view", self.vname(j["view"]))])
                if alias:
                    rel["join_to_view_as"] = self.vname(alias)
                rel["on_sql"] = on
                rel["relationship_type"] = REL.get(j.get("relationship") or "many_to_one", "many_to_one")
                rel["join_type"] = JOIN.get(j.get("type") or "left_outer", "always_left")
                k = json.dumps(rel, sort_keys=True)
                if k not in seen:
                    seen.add(k)
                    rels.append(rel)
                self.count("join", "mechanical")

            def node(name):
                chain = [name]
                while parent_of.get(chain[-1]) and parent_of[chain[-1]] != base:
                    chain.append(parent_of[chain[-1]])
                cur = tree
                for n in reversed(chain):
                    cur = cur.setdefault(self.vname(n), OrderedDict())
            for j in e["joins"]:
                if j["name"] in parent_of:
                    node(j["name"])
            body = OrderedDict([("base_view", self.vname(base)), ("label", e["label"])])
            if tree:
                body["joins"] = tree
            files[f"{self.vname(x)}.topic"] = l2o.dump_yaml(body)
            self.count("topic", "mechanical")
        if rels:
            files["relationships.yaml"] = l2o.dump_yaml(rels)

    # -- dashboards ------------------------------------------------------------------------------
    def kind_of(self, view, name):
        v = self.views.get(view, {})
        if name in v.get("measures", {}):
            return "number"
        if name in v.get("times", {}):
            return "date"
        for tf in TF_TOKENS:
            if name.endswith("_" + tf) and name[: -len(tf) - 1] in v.get("times", {}):
                return "date"
        t = v.get("dims", {}).get(name, {}).get("type")
        return {"yesno": "boolean", "number": "number"}.get(t, "string")

    def omni_filter(self, field: str, expr) -> dict:
        """A source-model filter expression to an Omni filter object; Skip when it has no mapping."""
        vw, nm = field.split(".", 1)
        kind = self.kind_of(vw, nm)
        v = str(expr).strip()
        low = v.lower()
        if low in ("null", "-null"):
            return {"type": "null", "is_negative": low.startswith("-")}
        if low in ("empty", "-empty"):
            return {"kind": "IS_EMPTY", "type": "string", "values": [], "is_negative": low.startswith("-")}
        if kind == "boolean":
            if low in ("yes", "true"):
                return {"type": "boolean", "is_negative": False, "treat_nulls_as_false": False}
            if low in ("no", "false"):
                return {"type": "boolean", "is_negative": True, "treat_nulls_as_false": False}
            raise Skip(f"boolean filter {v!r}")
        if kind == "date":
            m = re.fullmatch(r"(\d+) (day|week|month|quarter|year)s? ago for (\d+) (day|week|month|quarter|year)s?", low)
            if m:
                return {"kind": "TIME_FOR_INTERVAL_DURATION", "type": "date", "ui_type": "PAST",
                        "left_side": f"{m.group(1)} complete {m.group(2)}s ago", "right_side": f"{m.group(3)} {m.group(4)}s"}
            m = re.fullmatch(r"(\d+) (day|week|month|quarter|year)s?", low)
            if m:
                n = int(m.group(1))
                return {"kind": "TIME_FOR_INTERVAL_DURATION", "type": "date", "ui_type": "PAST",
                        "left_side": f"{n - 1} complete {m.group(2)}s ago", "right_side": f"{n} {m.group(2)}s"}
            m = re.fullmatch(r"(this|last) (day|week|month|quarter|year)", low)
            if m or low in ("today", "yesterday"):
                unit = m.group(2) if m else "day"
                back = 0 if (m and m.group(1) == "this") or low == "today" else 1
                return {"kind": "TIME_FOR_INTERVAL_DURATION", "type": "date", "ui_type": "PAST",
                        "left_side": f"{back} complete {unit}s ago", "right_side": f"1 {unit}"}
            m = re.fullmatch(r"(after|before) (\d{4}-\d{2}-\d{2})", low)
            if m:
                return {"kind": "ON_OR_AFTER" if m.group(1) == "after" else "BEFORE", "type": "date", "values": [m.group(2)]}
            m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})", low)
            if m:
                return {"kind": "BETWEEN", "type": "date", "values": [m.group(1), m.group(2)]}
            raise Skip(f"date filter {v!r} has no Omni mapping")
        if kind == "number":
            m = re.fullmatch(r"(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)", v)
            if m:
                # Omni's number kinds are LESS_THAN, GREATER_THAN, EQUALS and BETWEEN; "or equal" is is_inclusive
                k = "GREATER_THAN" if m.group(1).startswith(">") else "LESS_THAN"
                return {"kind": k, "type": "number", "values": [m.group(2)], "is_inclusive": m.group(1).endswith("=")}
            m = re.fullmatch(r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]", v)
            if m:
                return {"kind": "BETWEEN", "type": "number", "values": [m.group(1), m.group(2)], "is_inclusive": True}
            m = re.fullmatch(r"-?(-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?)*)", v)
            if m:
                return {"kind": "EQUALS", "type": "number", "values": m.group(1).split(","),
                        "is_negative": v.startswith("-")}
            raise Skip(f"number filter {v!r} has no Omni mapping")
        neg = v.startswith("-")
        body = v[1:] if neg else v
        if body.count("%") and "," not in body and "^" not in body:
            core = body.strip("%")
            if "%" not in core and "_" not in core and body != core:
                kind = "CONTAINS" if body.startswith("%") and body.endswith("%") else (
                    "STARTS_WITH" if body.endswith("%") else "ENDS_WITH")
                return {"kind": kind, "type": "string", "values": [core], "is_negative": neg}
        if "%" in v or "^" in v:
            raise Skip(f"string filter {v!r} uses a pattern")
        neg = v.startswith("-")
        vals = [x.replace("\\,", ",") for x in re.split(r"(?<!\\),", v[1:] if neg else v)]
        return {"kind": "EQUALS", "type": "string", "values": vals, "is_negative": neg}

    def vis(self, ctype: str, fields: list, dims: list, measures: list) -> dict:
        f = lambda n: {"field": {"name": n}}  # noqa: E731
        if ctype == "kpi":
            return {"config": {"alignment": "center", "dynamicFontSize": True, "verticalAlignment": "center",
                               "markdownConfig": [{"config": {"descriptionBefore": "", "field": {
                                   "field": {"name": measures[0] if measures else fields[0]}, "row": "_first"}},
                                   "id": "headline", "type": "number"}]}, "visType": "omni-kpi"}
        if ctype == "table":
            return {"config": {"hideIndexColumn": True, "tableType": "stretch"}, "visType": "omni-table"}
        if ctype == "pie":
            return {"config": {"configType": "polar", "color": f(dims[0]) if dims else {},
                               "theta": f(measures[0]) if measures else {}, "tooltip": [f(x) for x in fields]},
                    "visType": "basic"}
        horizontal = ctype == "bar"
        mark = {"column": "bar", "bar": "bar", "line": "line", "area": "area", "point": "point"}.get(ctype, "bar")
        cfg = {"_dependentAxis": "x" if horizontal else "y", "behaviors": {"stackMultiMark": False},
               "configType": "cartesian", "mark": {"type": mark}, "tooltip": [f(x) for x in fields],
               "series": [{"field": {"name": m}, ("xAxis" if horizontal else "yAxis"): "x" if horizontal else "y"}
                          for m in measures],
               "color": f(dims[1]) if len(dims) > 1 else {}}
        if dims:
            cfg["y" if horizontal else "x"] = f(dims[0])
        return {"config": cfg, "visType": "basic"}

    def tile(self, el, topic_of, i):
        topic = topic_of(el["explore"])
        base = self.vname(self.explores[el["explore"]]["base"])
        fields, dims, measures = [], [], []
        for fr in el["fields"]:
            vw, nm = fr.split(".", 1)
            r = self.ref(vw, nm)
            fields.append(r)
            (measures if self.kind_of(vw, nm) == "number" and (vw, nm) in self.measure_names else dims).append(r)
        sorts = []
        for s in el.get("sorts") or []:
            fr, _, d = s.rpartition(" ") if s.endswith((" asc", " desc")) else (s, "", "asc")
            vw, nm = fr.split(".", 1)
            sorts.append({"column_name": self.ref(vw, nm), "sort_descending": d == "desc"})
        filters = {}
        for fr, expr in (el.get("filters") or {}).items():
            vw, nm = fr.split(".", 1)
            r = self.ref(vw, nm)
            base_field = r.split("[")[0]
            filters[base_field] = self.omni_filter(fr, expr)
        pivots = [self.ref(*p.split(".", 1)) for p in el.get("pivots") or []]
        ctype = CHART.get(el.get("type"), "table")
        query = OrderedDict([
            ("table", base), ("fields", fields), ("pivots", pivots if ctype == "table" else []),
            ("sorts", sorts), ("filters", filters), ("limit", int(el.get("limit") or 500)),
            ("calculations", []), ("column_totals", {}), ("row_totals", {}), ("fill_fields", []),
            ("join_paths_from_topic_name", topic), ("userEditedSQL", "")])
        qp = OrderedDict([("name", el.get("title") or el.get("name")), ("topicName", topic), ("type", "query"),
                          ("prefersChart", True), ("isSql", False), ("query", query),
                          ("visConfig", {"chartType": ctype, "fields": fields, "version": 0,
                                         "visConfig": self.vis(ctype, fields, dims, measures)})])
        fidelity = None if el.get("type") in CHART else f"table_fallback: {el.get('type')} has no Omni chartType here"
        return qp, fidelity

    def write_documents(self, files: dict):
        topic_of = lambda x: self.vname(x)  # noqa: E731
        for doc in self.docs:
            slug = bi_ir.slug(doc.get("title") or doc.get("dashboard"))
            qps, order, containers, skipped, fidelity = OrderedDict(), [], [], [], []
            tile_key = {}
            for i, el in enumerate(doc.get("elements") or []):
                pos = {"x": el.get("col", 0), "y": el.get("row", 0) * ROW_SCALE,
                       "w": el.get("width", 12), "h": max(1, el.get("height", 6)) * ROW_SCALE}
                if el.get("type") == "text":
                    skipped.append({"element": el["name"], "reason": "text_tile",
                                    "detail": el.get("title_text") or el.get("body_text") or ""})
                    self.count("text_tile", "assisted")
                    continue
                try:
                    qp, fid = self.tile(el, topic_of, i)
                except Skip as e:
                    reason = "unmapped_filter" if "filter" in str(e) else "unmapped_field"
                    skipped.append({"element": el["name"], "reason": reason, "detail": str(e)})
                    self.count("tile", "assisted")
                    continue
                k = str(len(order) + 1)
                qps[k] = qp
                order.append(k)
                tile_key[el["name"]] = k
                if fid:
                    fidelity.append({"element": el["name"], "note": fid})
                containers.append({"containerType": "stack", "style": "tile", "name": qp["name"],
                                   "gridPosition": pos, "metadata": {"attachedQueryKey": k},
                                   "instanceKey": key(slug, "tile", k),
                                   "children": [{"type": "query", "as": "chart", "id": k,
                                                 "instanceKey": key(slug, "query", k)}]})
                self.count("tile", "mechanical")
                self.parity.append({"source": doc.get("source_id"), "source_tile": el["name"],
                                    "source_fields": el["fields"], "document": doc.get("title"),
                                    "document_file": f"documents/{slug}.json", "query_key": k,
                                    "topic": qp["topicName"], "fields": qp["query"]["fields"],
                                    "field_map": {s: o for s, o in zip(el["fields"], qp["query"]["fields"])}})
            controls, corder = OrderedDict(), []
            for flt in doc.get("filters") or []:
                fr = flt.get("field")
                try:
                    vw, nm = fr.split(".", 1)
                    r = self.ref(vw, nm).split("[")[0]
                except (Skip, AttributeError, ValueError) as e:
                    self.need(doc.get("source_id"), "dashboard_filter", "assisted",
                              f"filter {flt.get('title')} not emitted: {e}", None)
                    self.count("dashboard_filter", "assisted")
                    continue
                kind = self.kind_of(vw, nm)
                cfg = OrderedDict([("fieldName", r), ("label", flt.get("title") or flt.get("name")), ("type", kind)])
                default = flt.get("default_value") or ""
                if default:
                    try:
                        cfg.update({k: v for k, v in self.omni_filter(fr, default).items() if k != "type"})
                    except Skip as e:
                        self.need(doc.get("source_id"), "filter_default", "assisted",
                                  f"filter {flt.get('title')} default {default!r} not mapped: {e}", None)
                if "kind" not in cfg and kind != "boolean":
                    cfg["kind"] = "EQUALS" if kind != "date" else "TIME_FOR_INTERVAL_DURATION"
                    if kind == "date":
                        cfg.update({"left_side": "", "right_side": "", "ui_type": "PAST"})
                    else:
                        cfg["values"] = []
                cmap = OrderedDict()
                for el in doc.get("elements") or []:
                    k = tile_key.get(el.get("name"))
                    if k is None:
                        continue
                    lf = (el.get("listen") or {}).get(flt.get("name")) or (el.get("listen") or {}).get(flt.get("title"))
                    if lf:
                        try:
                            cmap[k] = self.ref(*lf.split(".", 1)).split("[")[0]
                        except Skip:
                            cmap[k] = False
                    else:
                        cmap[k] = False
                cid = key(slug, "control", flt.get("name"))
                controls[cid] = {"config": cfg, "map": cmap}
                corder.append(cid)
                self.count("dashboard_filter", "mechanical")
            for s in skipped:
                self.need(doc.get("source_id"), s["reason"], "assisted", f"tile {s['element']} not created: {s['detail']}",
                          "recreate by hand in Omni" if s["reason"] == "text_tile" else None)
            body = OrderedDict([
                ("name", doc.get("title")),
                ("description", (doc.get("description") or "").replace("twb_to_lookml", "twb_to_lookml + bi_to_omni")
                 .replace("mb_to_lookml", "mb_to_lookml + bi_to_omni")),
                ("queryPresentations", {"data": qps, "order": order}),
                ("controls", {"data": controls, "order": corder}),
                ("containers", [{"containerType": "page", "name": doc.get("title"), "instanceKey": key(slug, "page"),
                                 "container": {"containerType": "grid", "name": "Page layout",
                                               "instanceKey": key(slug, "grid"), "children": containers}}]),
                ("settings", {"controlBar": {"collapsible": True, "defaultExpanded": False, "fixed": False},
                              "crossfilterEnabled": False})])
            files[f"documents/{slug}.json"] = json.dumps(body, indent=1, ensure_ascii=False) + "\n"
            self.count("document", "mechanical")
            plan = {"title": doc.get("title"), "source": doc.get("source_id"), "tiles_planned": len(order),
                    "skipped": skipped, "fidelity": fidelity}
            files[f"documents/{slug}.plan.json"] = json.dumps(plan, indent=1, ensure_ascii=False) + "\n"

    def primary_keys(self):
        """Every view on either side of a relationship needs a primary key (lint L6); list the ones without."""
        joined = set()
        for x in self.explores.values():
            if x["joins"]:
                joined.add(x["base"])
                joined |= {j["view"] for j in x["joins"]}
        for vn in sorted(joined):
            if not any(d.get("primary_key") for d in self.views.get(vn, {}).get("dims", {}).values()):
                self.need(self.ident("view", self.vname(vn)), "primary_key", "assisted",
                          "joined view with no primary key: Omni cannot dedupe the join until one is set", None)

    def write(self):
        files = {}
        self.plan_names()
        self.write_views(files)
        self.write_topics(files)
        self.write_documents(files)
        self.primary_keys()
        # the writer checks primary keys against the Omni model itself, so the reader's LookML-worded
        # primary key items are replaced; the same item listed twice (two data sources, one view) is kept once
        seen, needs = set(), []
        for n in self.reword(self.needs):
            if n["writer"] == "reader" and n["construct"] == "primary_key":
                continue
            k = (str(n["object"]), n["construct"], n["reason"])
            if k not in seen:
                seen.add(k)
                needs.append(n)
        needs.sort(key=lambda n: (str(n["object"]), n["construct"], n["reason"]))
        summary = {"writer": "bi_to_omni", "version": VERSION, "source": self.tool, "prefix": self.prefix,
                   "bind": self.bind, "counts": {k: dict(sorted(v.items())) for k, v in sorted(self.counts.items())},
                   "views": len(self.views), "topics": len(self.explores),
                   "documents": sum(1 for f in files if f.endswith(".json") and not f.endswith(".plan.json")),
                   "needs_human": len(needs)}
        return files, needs, summary, self.parity

    @staticmethod
    def reword(needs):
        """The readers word some items for a LookML target; say what they mean for Omni."""
        swaps = [("emitted as a one-tile LookML dashboard", "emitted as a one-tile Omni document"),
                 ("make it a Look through the Looker API (looker_content)", "keep it as a workbook tab in Omni"),
                 ("became 2 LookML dashboards", "became 2 Omni documents"), ("LookML dashboards", "Omni documents"),
                 ("LookML parameter; references use {% parameter %}", "parameter: an Omni templated filter or control"),
                 ("Looker table calculation on the tile, or drop", "Omni table calculation on the tile, or drop"),
                 ("LookML dashboard filters cannot", "Omni controls cannot"), ("Looker filters", "Omni filters"),
                 ("Looker drill fields or links", "Omni drill fields or links"),
                 ("Looker text tiles cannot", "Omni documents carry it only by hand"),
                 ("Looker's dashboard filter replaces the tile's", "check Omni's control against the tile's filter"),
                 ("the Looker filter's default condition must match", "the Omni control's default must match"),
                 ("one LookML model has one connection", "one Omni model has one connection")]
        out = []
        for n in needs:
            n = dict(n)
            for k in ("reason", "proposal"):
                if isinstance(n.get(k), str):
                    for a, b in swaps:
                        n[k] = n[k].replace(a, b)
            n.setdefault("writer", "reader")
            out.append(n)
        return out


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

def lint(out: Path) -> list:
    """Static checks on the emitted Omni files (rules of omni-model-lint that need no Omni call)."""
    probs = []
    views, rel_views = {}, set()
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.suffix in (".view", ".topic", ".yaml"))
    if not files:
        return ["L0: no Omni files in the output folder"]
    for p in files:
        rel = p.relative_to(out).as_posix()
        text = p.read_text()
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as e:
            probs.append(f"L0 {rel}: not parseable YAML ({e})")
            continue
        if "${TABLE}" in text:
            probs.append(f"L1 {rel}: ${{TABLE}} left in")
        if LIQUID.search(text):
            probs.append(f"L2 {rel}: Liquid left in")
        if p.suffix == ".view":
            name = p.name[: -len(".query.view")] if p.name.endswith(".query.view") else p.stem
            dims = (doc or {}).get("dimensions") or {}
            meas = (doc or {}).get("measures") or {}
            views[name] = (dims, meas)
            for n in set(dims) & set(meas):
                probs.append(f"L9 {rel}: {n} is both a dimension and a measure")
            for n, d in dims.items():
                for tf in (d or {}).get("timeframes") or []:
                    if tf not in OMNI_TIMEFRAMES:
                        probs.append(f"L3 {rel}: dimensions.{n} timeframe {tf}")
            for n, m in meas.items():
                m = m or {}
                at = m.get("aggregate_type")
                if at and at not in OMNI_AGGREGATES:
                    probs.append(f"L4 {rel}: measures.{n} aggregate_type {at}")
                if at == "percentile" and "percentile" not in m:
                    probs.append(f"L4 {rel}: measures.{n} percentile has no value")
                for fk, fv in (m.get("filters") or {}).items():
                    if not isinstance(fv, dict):
                        probs.append(f"L5 {rel}: measures.{n}.filters.{fk} is a bare scalar")
                if re.search(r"\$\{" + re.escape(n) + r"\}", m.get("sql") or ""):
                    probs.append(f"L11 {rel}: measures.{n} refers to itself")
            for n, d in dims.items():
                if re.search(r"\$\{" + re.escape(n) + r"\}", (d or {}).get("sql") or ""):
                    probs.append(f"L11 {rel}: dimensions.{n} refers to itself")
        if p.name == "relationships.yaml":
            for r in doc or []:
                rel_views |= {r.get("join_from_view"), r.get("join_to_view")}
                if r.get("relationship_type") not in {"one_to_one", "many_to_one", "one_to_many", "many_to_many",
                                                     "assumed_many_to_one"}:
                    probs.append(f"L8 relationships.yaml: relationship_type {r.get('relationship_type')}")
                if r.get("join_type") not in {"always_left", "inner", "full_outer", "cross", "right_left", "left_right"}:
                    probs.append(f"L8 relationships.yaml: join_type {r.get('join_type')}")
    for p in files:
        if p.suffix == ".topic":
            doc = yaml.safe_load(p.read_text()) or {}

            def walk(t):
                for k, v in (t or {}).items():
                    yield k
                    yield from walk(v)
            for v in [doc.get("base_view")] + list(walk(doc.get("joins"))):
                if v not in views:
                    probs.append(f"L7 {p.relative_to(out).as_posix()}: view {v} is not emitted")
    needs = json.loads((out / "needs_human.json").read_text()) if (out / "needs_human.json").exists() else []
    listed = {n["object"] for n in needs if n.get("construct") == "primary_key"}
    for v in sorted(x for x in rel_views if x):
        dims = views.get(v, ({}, {}))[0]
        if not any((d or {}).get("primary_key") for d in dims.values()) and not any(
                str(o).endswith(f":view:{v}") for o in listed):
            probs.append(f"L6 {v}: joined view has no primary key and no needs_human item")
    return probs


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def from_tableau(a):
    import twb_to_lookml as t
    est = t.Estate(Path(a.snapshot), a.site, a.dialect)
    collect = {}
    only_d = {x for x in (a.datasets or "").split(",") if x}
    only_w = {x for x in (a.workbooks or "").split(",") if x}
    _, needs, _, _ = t.emit_estate(est, "omni", "warehouse", only_d, only_w, collect=collect)
    return Writer("tableau", collect["views"], collect["explores"], collect["dashboards"], a.dialect,
                  a.prefix, a.bind, needs)


def from_metabase(a):
    import mb_to_lookml as m
    est = m.Estate(Path(a.snapshot))
    cv, _, _ = m.run(est, "omni", "warehouse", m.ids(a.dashboards or ""), m.ids(a.cards or ""), a.database)
    dialect = next((est.dialect(c.get("database_id")) for c in est.cards.values()), None) or "bigquery"
    return Writer("metabase", cv.views, cv.explores, cv.dash_docs, dialect, a.prefix, a.bind, cv.needs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("--source", required=True, choices=["tableau", "metabase"])
    c.add_argument("--snapshot", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--prefix", default="", help="prefix for every view and topic name (keeps a test or batch apart)")
    c.add_argument("--bind", default="query", choices=["query", "schema"])
    c.add_argument("--site")
    c.add_argument("--dialect", default="bigquery", choices=["bigquery", "snowflake"])
    c.add_argument("--workbooks", default="")
    c.add_argument("--datasets", default="")
    c.add_argument("--database", type=int)
    c.add_argument("--dashboards", default="")
    c.add_argument("--cards", default="")
    lt = sub.add_parser("lint")
    lt.add_argument("out_dir")
    a = ap.parse_args(argv)
    if a.cmd == "lint":
        probs = lint(Path(a.out_dir))
        for p in probs:
            print("FAIL", p)
        print(f"{'FAIL' if probs else 'PASS'}: {len(probs)} problem(s) in emitted Omni files")
        return 1 if probs else 0
    try:
        w = from_tableau(a) if a.source == "tableau" else from_metabase(a)
        files, needs, summary, parity = w.write()
    except Exception as e:  # the readers raise their own ConvertError types
        if type(e).__name__ in ("ConvertError", "ParseError", "JSONDecodeError"):
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        raise
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / "needs_human.json").write_text(json.dumps(needs, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "parity_map.json").write_text(json.dumps(parity, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "conversion_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(f"{summary['views']} views, {summary['topics']} topics, {summary['documents']} documents, "
          f"{summary['needs_human']} needs_human -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

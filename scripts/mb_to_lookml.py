#!/usr/bin/env python3
"""
Metabase to LookML converter (bi_migration, pair metabase_to_looker). EXPERIMENTAL.

Reads a snapshot written by metabase_export.py and runs one of three commands:

    audit     Catalogs with a translation class per construct (tables, fields, joins,
              custom columns, metrics, models, native questions, questions, dashboards,
              dashboard filters), the tool-neutral IR (wire/scripts/bi_ir.py) and the
              dependency graph.
    convert   LookML: one view per Metabase table (types and primary keys from Metabase's
              metadata), explores with joins (foreign keys and the questions' own joins),
              measures for the aggregations questions use and for saved metrics, views on
              the SQL of saved models and native questions, LookML dashboards (Metabase's
              24-column grid maps one to one; one dashboard per tab), plus needs_human.json.
              Simple single-table native SQL is also lifted into dimensions and measures on
              the table's view, as a proposal (needs sqlglot; skipped with a note without it).
    lint      Fails if Metabase syntax is left in emitted LookML (template tags, optional
              clauses, snippets, card references), if a view defines a field name twice
              (counting the fields a dimension group generates), or the folder has no LookML.

Deterministic and no AI call: the same snapshot gives the same files. The agent decides
each needs_human item, explore design and consolidation; it never hand-writes LookML this
script emits.

Translation rules are in wire/bi_pairs/metabase_to_looker/translation_guide.md.

Usage:
    python3 wire/scripts/mb_to_lookml.py audit --snapshot <dir> --out <dir>
    python3 wire/scripts/mb_to_lookml.py convert --snapshot <dir> --out <dir> [--model NAME]
        [--connection NAME] [--database ID] [--dashboards IDS] [--cards IDS] [--include-root DIR]
    python3 wire/scripts/mb_to_lookml.py lint <lookml dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bi_ir  # noqa: E402

VERSION = "0.1.0"
TOOL = "metabase"

ENGINE_DIALECT = {"bigquery-cloud-sdk": "bigquery", "bigquery": "bigquery", "snowflake": "snowflake",
                  "postgres": "postgres", "redshift": "redshift", "databricks": "databricks", "mysql": "mysql",
                  "sqlserver": "tsql", "athena": "athena", "presto-jdbc": "presto", "starburst": "trino",
                  "clickhouse": "clickhouse", "oracle": "oracle", "vertica": "vertica"}
# Engines Looker has no connection for: content on them converts, but cannot run in Looker
NO_LOOKER = {"sqlite", "h2", "mongo", "druid", "druid-jdbc", "googleanalytics"}

TIMEFRAME = {"minute": "minute", "hour": "hour", "day": "date", "week": "week", "month": "month",
             "quarter": "quarter", "year": "year", "day-of-week": "day_of_week", "day-of-month": "day_of_month",
             "day-of-year": "day_of_year", "week-of-year": "week_of_year", "month-of-year": "month_num",
             "quarter-of-year": "quarter_of_year", "hour-of-day": "hour_of_day"}
TF_DATE = ["raw", "date", "week", "month", "quarter", "year"]
TF_ALL = ["raw", "time", "date", "week", "month", "quarter", "year", "minute", "hour", "day_of_week", "day_of_month",
          "day_of_year", "week_of_year", "month_num", "quarter_of_year", "hour_of_day"]
TF_TIME = ["raw", "time", "date", "week", "month", "quarter", "year"]
TEMPORAL = {"type/Date": "date", "type/DateTime": "timestamp", "type/DateTimeWithTZ": "timestamp",
            "type/DateTimeWithLocalTZ": "timestamp", "type/DateTimeWithZoneOffset": "timestamp",
            "type/DateTimeWithZoneID": "timestamp", "type/Instant": "timestamp"}
AGG = {"sum": ("sum", "total"), "avg": ("average", "average"), "min": ("min", "min"), "max": ("max", "max"),
       "distinct": ("count_distinct", "count_distinct"), "median": ("median", "median")}
VIZ = {"table": "looker_grid", "pivot": "looker_grid", "bar": "looker_column", "row": "looker_bar",
       "line": "looker_line", "area": "looker_area", "combo": "looker_column", "pie": "looker_pie",
       "scalar": "single_value", "smartscalar": "single_value", "gauge": "single_value", "progress": "single_value",
       "funnel": "looker_funnel", "scatter": "looker_scatter", "map": "looker_map", "waterfall": "looker_waterfall",
       "object": "looker_single_record", "boxplot": "looker_boxplot"}
VIZ_ASSISTED = {"pivot", "combo", "smartscalar", "gauge", "progress", "map", "waterfall", "boxplot"}
COERCE = {"Coercion/UNIXSeconds->DateTime": {"bigquery": "TIMESTAMP_SECONDS({c})", "snowflake": "TO_TIMESTAMP({c})"},
          "Coercion/UNIXMilliSeconds->DateTime": {"bigquery": "TIMESTAMP_MILLIS({c})", "snowflake": "TO_TIMESTAMP({c} / 1000)"},
          "Coercion/ISO8601->DateTime": {"bigquery": "CAST({c} AS TIMESTAMP)", "snowflake": "TRY_TO_TIMESTAMP({c})"},
          "Coercion/ISO8601->Date": {"bigquery": "CAST({c} AS DATE)", "snowflake": "TRY_TO_DATE({c})"}}


class ConvertError(Exception):
    pass


class Unsupported(Exception):
    pass


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def parts(x):
    """An MBQL clause as (op, opts, args). MBQL 5: [op, {opts}, *args]. Legacy: [op, *args] and
    ["field", id, opts]."""
    if not isinstance(x, list) or not x or not isinstance(x[0], str):
        return None, {}, []
    op = x[0]
    if len(x) > 1 and isinstance(x[1], dict):
        return op, x[1], x[2:]
    if op in ("field", "expression", "aggregation") and len(x) > 2 and isinstance(x[2], dict):
        return op, x[2], [x[1]]
    return op, {}, x[1:]


def is_clause(x):
    return isinstance(x, list) and x and isinstance(x[0], str) and x[0] in CLAUSES


CLAUSES = {"field", "expression", "aggregation", "value", "+", "-", "*", "/", "case", "if", "coalesce", "concat",
           "lower", "upper", "trim", "ltrim", "rtrim", "length", "abs", "round", "floor", "ceil", "sqrt", "power",
           "log", "exp", "substring", "replace", "contains", "starts-with", "ends-with", "does-not-contain",
           "=", "!=", "<", ">", "<=", ">=", "and", "or", "not", "is-null", "not-null", "is-empty", "not-empty",
           "between", "time-interval", "in", "not-in", "count", "sum", "avg", "min", "max", "distinct", "median", "cum-sum",
           "cum-count", "count-where", "sum-where", "distinct-where", "share", "metric", "stddev", "var",
           "percentile", "offset", "datetime-diff", "now", "segment", "inside", "relative-time-interval"}


def canon(x):
    """x without lib/uuid, for hashing a clause."""
    if isinstance(x, dict):
        return {k: canon(v) for k, v in sorted(x.items()) if k != "lib/uuid"}
    if isinstance(x, list):
        return [canon(v) for v in x]
    return x


def short_hash(x) -> str:
    return hashlib.sha256(json.dumps(canon(x), sort_keys=True).encode()).hexdigest()[:6]


def lk_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def quote_ident(name: str, dialect: str | None) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) and (dialect != "snowflake" or name == name.upper()):
        return name
    if dialect in ("bigquery", "mysql", "databricks", "clickhouse"):
        return f"`{name}`"
    return '"' + name.replace('"', '""') + '"'


def taken_names(v) -> set:
    """Every field name a view defines or will generate: a dimension group named x makes x_date, x_month
    and so on (every timeframe it could gain), so a dimension or measure must not use those names."""
    names = set(v["dims"]) | set(v["measures"]) | set(v["params"]) | set(v["filters"]) | set(v["groups"])
    for g in v["groups"]:
        names |= {f"{g}_{tf}" for tf in TF_ALL}
    return names


def free_name(v, name, suffix="from_sql"):
    taken = taken_names(v)
    if name not in taken:
        return name
    n, i = f"{name}_{suffix}", 2
    while n in taken:
        n, i = f"{name}_{suffix}_{i}", i + 1
    return n


def lk_type(base):
    base = base or ""
    if base in TEMPORAL:
        return "time"
    if base == "type/Boolean":
        return "yesno"
    if any(k in base for k in ("Integer", "Float", "Decimal", "Number", "Currency", "Percentage")):
        return "number"
    return "string"


def stages(q: dict) -> list:
    if "stages" in q:
        return q["stages"]
    if q.get("type") == "native":
        n = q.get("native") or {}
        return [{"lib/type": "mbql.stage/native", "native": n.get("query", ""), "template-tags": n.get("template-tags") or {}}]
    inner, out = q.get("query") or {}, []
    while inner:
        out.insert(0, {k: v for k, v in inner.items() if k != "source-query"})
        inner = inner.get("source-query")
    return out


def fragment(obj, n=2000):
    s = json.dumps(canon(obj), sort_keys=True, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "...(truncated)"


def esc_filter(v) -> str:
    s = str(v)
    s = s.replace("^", "^^").replace(",", "^,").replace("%", "^%").replace("_", "^_")
    return "^-" + s[1:] if s.startswith("-") else s


def tidy_num(v) -> str:
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else repr(f)
    except (TypeError, ValueError):
        return str(v)


def next_day(d: str) -> str:
    import datetime as dt
    try:
        return (dt.date.fromisoformat(d[:10]) + dt.timedelta(days=1)).isoformat()
    except ValueError:
        raise Unsupported(f"date {d!r}")


# ---------------------------------------------------------------------------
# Estate
# ---------------------------------------------------------------------------

class Estate:
    def __init__(self, snap: Path):
        inv_p = snap / "inventory.json"
        if not inv_p.exists():
            raise ConvertError(f"{snap}: no inventory.json (run metabase_export.py first)")
        self.snap = snap
        self.inv = json.loads(inv_p.read_text())
        self.site = self.inv.get("site") or "local"
        self.version = self.inv.get("version")
        self.cards, self.dashboards, self.meta = {}, {}, {}
        for o in self.inv.get("objects", []):
            body = json.loads((snap / o["path"]).read_text())
            (self.cards if o["kind"] == "card" else self.dashboards)[int(o["id"])] = body
            self.meta[(o["kind"], int(o["id"]))] = o
        self.tables, self.fields = {}, {}
        for p in sorted((snap / "tables").glob("*.json")) if (snap / "tables").is_dir() else []:
            t = json.loads(p.read_text())
            self.tables[t["id"]] = t
            for f in t.get("fields", []):
                self.fields[f["id"]] = f
        self.compiled = {int(p.stem): p.read_text() for p in sorted((snap / "compiled").glob("*.sql"))} \
            if (snap / "compiled").is_dir() else {}
        self.dbs = {d["id"]: d for d in self.inv.get("databases", [])}
        self.collections = {c["id"]: c for c in self.inv.get("collections", [])}
        u = snap / "usage.json"
        self.usage = json.loads(u.read_text()) if u.exists() else {}

    def ident(self, *p):
        return bi_ir.identity(TOOL, self.site, *p)

    def engine(self, db_id):
        return (self.dbs.get(db_id) or {}).get("engine")

    def dialect(self, db_id):
        return ENGINE_DIALECT.get(self.engine(db_id))

    def card_kind(self, c):
        return "native" if any("native" in st for st in stages(c.get("dataset_query") or {})) else "mbql"


# ---------------------------------------------------------------------------
# Native SQL: template tags, and lifting simple single-table SQL (sqlglot, optional)
# ---------------------------------------------------------------------------

TAG = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
OPTIONAL = re.compile(r"\[\[(.*?)\]\]", re.S)


def lift_sql(sql: str, dialect: str | None):
    """{'table', 'dims': [(name, sql)], 'measures': [(name, type, sql)], 'where'} or (None, reason)."""
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError:
        return None, "sqlglot is not installed (python3 -m pip install sqlglot): lift skipped"
    if TAG.search(sql) or OPTIONAL.search(sql):
        return None, "template tags: not lifted"
    try:
        tree = sqlglot.parse_one(sql, read=dialect)
    except Exception as e:  # noqa: BLE001  any parse failure means: do not lift
        return None, f"SQL did not parse ({type(e).__name__})"
    if not isinstance(tree, exp.Select) or tree.args.get("joins") or tree.args.get("with") \
            or list(tree.find_all(exp.Subquery)) or list(tree.find_all(exp.Window)):
        return None, "not a single-table select (joins, CTEs, subqueries or window functions)"
    tables = list(tree.find_all(exp.Table))
    if len(tables) != 1:
        return None, "not a single-table select"
    t = tables[0]
    alias = t.alias_or_name
    table = ".".join(p for p in (t.catalog, t.db, t.name) if p)

    def rewrite(node):
        node = node.copy()
        for c in node.find_all(exp.Column):
            if c.table in ("", alias, t.name):
                c.set("table", exp.to_identifier("LOOKERTABLEPLACEHOLDER"))
        return node.sql(dialect=dialect).replace("LOOKERTABLEPLACEHOLDER.", "${TABLE}.")

    prefix = (alias + "_").lower()
    dims, measures = [], []
    for e in tree.expressions:
        name = (e.alias_or_name or "").lower()
        name = name[len(prefix):] if name.startswith(prefix) else name
        inner = e.this if isinstance(e, exp.Alias) else e
        if not name or isinstance(inner, exp.Star):
            return None, "unnamed or star column"
        aggs = list(inner.find_all(exp.AggFunc))
        if not aggs:
            dims.append((bi_ir.slug(name), rewrite(inner)))
            continue
        if isinstance(inner, exp.Count) and isinstance(inner.this, exp.Distinct) and len(inner.this.expressions) == 1:
            measures.append((bi_ir.slug(name), "count_distinct", rewrite(inner.this.expressions[0])))
        elif isinstance(inner, exp.Count) and isinstance(inner.this, exp.Star):
            measures.append((bi_ir.slug(name), "count", None))
        elif isinstance(inner, (exp.Sum, exp.Avg, exp.Min, exp.Max)) and not list(inner.this.find_all(exp.AggFunc)):
            kind = {exp.Sum: "sum", exp.Avg: "average", exp.Min: "min", exp.Max: "max"}[type(inner)]
            measures.append((bi_ir.slug(name), kind, rewrite(inner.this)))
        else:
            measures.append((bi_ir.slug(name), "number", rewrite(inner)))
    where = tree.args.get("where")
    return {"table": table, "dims": dims, "measures": measures,
            "where": where.this.sql(dialect=dialect) if where is not None else None}, None


def sql_order(sql: str, dialect: str | None, columns: list):
    """ORDER BY of a native query as [(column, 'asc'|'desc')], by ordinal or name; [] when unknown."""
    sql = TAG.sub("NULL", OPTIONAL.sub("", sql))      # template tags do not parse; they never hold the sort
    try:
        import sqlglot
        from sqlglot import exp
        tree = sqlglot.parse_one(sql, read=dialect)
    except Exception:  # noqa: BLE001
        return []
    o = tree.args.get("order") if isinstance(tree, exp.Select) else None
    out = []
    for item in (o.expressions if o is not None else []):
        node, desc = item.this, bool(item.args.get("desc"))
        if isinstance(node, exp.Literal) and node.is_int and 0 < int(node.this) <= len(columns):
            out.append((columns[int(node.this) - 1], "desc" if desc else "asc"))
        elif isinstance(node, exp.Column) and node.name in columns:
            out.append((node.name, "desc" if desc else "asc"))
        else:
            return []
    return out


# ---------------------------------------------------------------------------
# The converter
# ---------------------------------------------------------------------------

class Converter:
    def __init__(self, est: Estate, model: str, connection: str, include_root: str = ""):
        self.est, self.model, self.connection = est, model, connection
        self.root = f"{include_root.strip('/')}/" if include_root.strip("/") else ""
        self.views = {}           # name -> {"source", "dims", "groups", "measures", "params", "filters", "label"}
        self.table_view = {}      # table id -> view name
        self.card_view = {}       # card id -> derived view name
        self.explores = {}        # name -> {"base", "label", "joins": {name: {...}}}
        self.base_explore = {}    # ("table", id) | ("card", id) -> explore name
        self.elements = {}        # card id -> element dict (without position) or None
        self.card_class = {}      # card id -> (class, reason)
        self.metric_measure = {}  # metric card id -> "view.measure"
        self.needs, self.deps, self.counts = [], [], {}
        self.names_used = set()
        self.field_names = {}     # Metabase field id -> (view, name, is_group)
        self.reported = set()     # (dashboard, parameter, construct) already listed
        self.dash_docs = []       # dashboard definitions before rendering, for another writer (bi_to_omni.py)

    # -- bookkeeping ----------------------------------------------------------
    def count(self, construct, cls):
        self.counts.setdefault(construct, {}).setdefault(cls, 0)
        self.counts[construct][cls] += 1

    def need(self, obj, construct, cls, reason, proposal=None):
        self.needs.append({"object": obj, "construct": construct, "class": cls, "reason": reason, "proposal": proposal})

    def unique(self, base):
        name, n = base, 2
        while name in self.names_used:
            name, n = f"{base}_{n}", n + 1
        self.names_used.add(name)
        return name

    # -- views from table metadata ------------------------------------------------
    def table_name_sql(self, t):
        d = self.est.dialect(t.get("db_id"))
        det = (self.est.dbs.get(t.get("db_id")) or {}).get("details") or {}
        pieces = [t.get("schema"), t["name"]]
        if d == "bigquery" and det.get("project-id"):
            return "`" + ".".join([det["project-id"]] + [p for p in pieces if p]) + "`"
        return ".".join(quote_ident(p, d) for p in pieces if p)

    def view_for_table(self, tid):
        if tid in self.table_view:
            return self.table_view[tid]
        t = self.est.tables.get(tid)
        if t is None:
            raise Unsupported(f"table {tid} is not in the snapshot")
        name = self.unique(bi_ir.slug(t["name"]))
        self.table_view[tid] = name
        v = {"source": {"table": self.table_name_sql(t)}, "dims": {}, "groups": {}, "measures": {}, "params": {},
             "filters": {}, "label": t.get("display_name") or t["name"]}
        self.views[name] = v
        d = self.est.dialect(t.get("db_id"))
        tid_ident = self.est.ident("table", tid)
        for f in sorted(t.get("fields", []), key=lambda x: (x.get("position", 0), x["id"])):
            vis = f.get("visibility_type")
            if vis == "retired":
                continue
            if vis == "sensitive":
                self.need(bi_ir.field_id(TOOL, self.est.site, t["name"], f["name"]), "sensitive_field", "assisted",
                          "field is marked sensitive in Metabase: not emitted", "emit it hidden, or leave it out")
                continue
            col = f"${{TABLE}}.{quote_ident(f['name'], d)}"
            if f.get("nfc_path"):
                path = f["nfc_path"]
                col = (f"JSON_VALUE(${{TABLE}}.{quote_ident(path[0], d)}, '$.{'.'.join(path[1:])}')" if d == "bigquery"
                       else f"${{TABLE}}.{quote_ident(path[0], d)}:{':'.join(path[1:])}")
                self.need(bi_ir.field_id(TOOL, self.est.site, t["name"], f["name"]), "json_field", "assisted",
                          "field unfolded from JSON by Metabase: check the path expression", col)
            eff = f.get("effective_type") or f.get("base_type")
            cs = f.get("coercion_strategy")
            if cs:
                tmpl = (COERCE.get(cs) or {}).get(d)
                if tmpl:
                    col = tmpl.format(c=col)
                else:
                    eff = f.get("base_type")
                    self.need(bi_ir.field_id(TOOL, self.est.site, t["name"], f["name"]), "coercion", "assisted",
                              f"Metabase casts this field ({cs}); emitted uncast", "add the cast to the dimension SQL")
            dname = bi_ir.slug(f["name"])
            self.field_names[f["id"]] = (name, dname, lk_type(eff) == "time")
            entry = {"label": f.get("display_name") or f["name"], "sql": col, "source_field": f["id"],
                     "hidden": vis == "details-only", "description": f.get("description")}
            lt = lk_type(eff)
            if lt == "time":
                entry.update({"datatype": "date" if TEMPORAL.get(eff) == "date" else "timestamp", "timeframes": set(
                    TF_DATE if TEMPORAL.get(eff) == "date" else TF_TIME)})
                v["groups"][dname] = entry
            else:
                entry["type"] = lt
                if f.get("semantic_type") == "type/PK":
                    entry["primary_key"] = True
                v["dims"][dname] = entry
        clash = sorted(d for d in v["dims"] if d in {f"{g}_{tf}" for g in v["groups"] for tf in TF_ALL})
        for d in clash:
            entry = v["dims"].pop(d)
            new = free_name(v, d, "column")
            v["dims"][new] = entry
            fid = entry.get("source_field")
            if fid in self.field_names:
                self.field_names[fid] = (name, new, False)
            self.need(bi_ir.field_id(TOOL, self.est.site, t["name"], d), "name_clash", "assisted",
                      f"column {d} has the name of a field the date group generates: emitted as {new}", None)
        self.deps.append({"from": tid_ident, "to": f"looker:{self.model}:view:{name}", "kind": "contains"})
        return name

    def field_dim(self, fid):
        """(view, dim name, is_group, field) for a Metabase field id on its own table's view."""
        f = self.est.fields.get(fid)
        if f is None:
            raise Unsupported(f"field {fid} is not in the snapshot")
        self.view_for_table(f["table_id"])
        if fid not in self.field_names:
            raise Unsupported(f"field {f['name']} was not emitted")
        view, name, group = self.field_names[fid]
        return view, name, group, f

    def ensure_count(self, view):
        self.views[view]["measures"].setdefault("count", {"type": "count", "label": "Count"})
        return "count"

    # -- views from SQL (models, native questions) --------------------------------
    def view_for_card(self, cid):
        """A derived-table view on a saved model or native question's SQL (or the SQL Metabase compiles)."""
        if cid in self.card_view:
            return self.card_view[cid]
        c = self.est.cards.get(cid)
        if c is None:
            raise Unsupported(f"card {cid} is not in the snapshot")
        d = self.est.dialect(c.get("database_id"))
        sts = stages(c.get("dataset_query") or {})
        if self.est.card_kind(c) == "native":
            st = sts[0]
            sql, params, filters = self.native_sql(cid, st, d)
        elif cid in self.est.compiled:
            sql, params, filters = self.est.compiled[cid].strip().rstrip(";"), {}, {}
            self.need(self.est.ident("card", cid), "model_sql" if c.get("type") == "model" else "card_as_source",
                      "assisted", "view built on the SQL Metabase compiles for this "
                      + ("model" if c.get("type") == "model" else "question")
                      + ": exact, but not reusable", "rebuild as a dbt model or as an explore on the table views")
        else:
            raise Unsupported(f"no SQL for card {cid} (not compiled in the snapshot)")
        name = self.unique(bi_ir.slug(c.get("name") or f"card_{cid}"))
        self.card_view[cid] = name
        v = {"source": {"derived_sql": sql}, "dims": {}, "groups": {}, "measures": {}, "params": params,
             "filters": filters, "label": c.get("name")}
        self.views[name] = v
        for col in c.get("result_metadata") or []:
            cname = col.get("name")
            if not cname:
                continue
            dname = bi_ir.slug(cname)
            eff = col.get("effective_type") or col.get("base_type")
            entry = {"label": col.get("display_name") or cname, "sql": f"${{TABLE}}.{quote_ident(cname, d)}",
                     "column": cname}
            if lk_type(eff) == "time":
                entry.update({"datatype": "date" if TEMPORAL.get(eff) == "date" else "timestamp",
                              "timeframes": set(TF_DATE if TEMPORAL.get(eff) == "date" else TF_TIME)})
                v["groups"][dname] = entry
            else:
                entry["type"] = lk_type(eff)
                if col.get("semantic_type") == "type/PK":
                    entry["primary_key"] = True
                v["dims"][dname] = entry
        self.deps.append({"from": self.est.ident("card", cid, "dataset", "sql"),
                          "to": f"looker:{self.model}:view:{name}", "kind": "contains"})
        return name

    def native_sql(self, cid, st, dialect):
        sql = (st.get("native") or "").strip().rstrip(";")
        tags = st.get("template-tags") or {}
        params, filters = {}, {}
        cid_ident = self.est.ident("card", cid)
        if "{{snippet:" in sql.replace(" ", "") or any(t.get("type") == "snippet" for t in tags.values()):
            raise Unsupported("native SQL uses a snippet (not in the snapshot)")

        def field_filter(tag):
            dim = tag.get("dimension")
            op, opts, args = parts(dim)
            if op != "field" or not isinstance(args[0], int) or args[0] not in self.est.fields:
                raise Unsupported(f"field filter {tag.get('name')} on an unknown field")
            f = self.est.fields[args[0]]
            t = self.est.tables[f["table_id"]]
            # Metabase writes a field filter's column qualified by its table; the SQL must not alias that table
            tbl = ".".join(x for x in (t.get("schema"), t["name"]) if x)
            col = (f"`{tbl}`.{quote_ident(f['name'], 'bigquery')}" if dialect == "bigquery"
                   else f"{'.'.join(quote_ident(x, dialect) for x in tbl.split('.'))}.{quote_ident(f['name'], dialect)}")
            self.need(cid_ident, "field_filter", "assisted",
                      f"field filter {tag['name']} became a templated filter on {col}, as Metabase writes it",
                      "check the SQL reads that table without an alias")
            ftype = "date" if lk_type(f.get("effective_type") or f.get("base_type")) == "time" else \
                ("number" if lk_type(f.get("base_type")) == "number" else "string")
            filters[bi_ir.slug(tag["name"])] = {"type": ftype, "label": tag.get("display-name") or tag["name"]}
            return f"{{% condition {bi_ir.slug(tag['name'])} %}} {col} {{% endcondition %}}"

        def replace_tags(text, optional):
            def sub(m):
                name = m.group(1).strip()
                if name.startswith("#"):
                    ref = int(re.match(r"#(\d+)", name).group(1))
                    return f"(SELECT * FROM ${{{self.view_for_card(ref)}.SQL_TABLE_NAME}})"
                tag = tags.get(name)
                if tag is None:
                    raise Unsupported(f"template tag {name} is not declared")
                if tag.get("type") == "dimension":
                    return field_filter(tag)
                if optional:
                    raise Unsupported("optional clause on a variable")
                ptype = {"number": "number", "date": "date"}.get(tag.get("type"), "string")
                p = {"type": ptype, "label": tag.get("display-name") or name}
                if tag.get("default") is not None:
                    p["default_value"] = str(tag["default"])
                params[bi_ir.slug(name)] = p
                return f"{{% parameter {bi_ir.slug(name)} %}}"
            return TAG.sub(sub, text)

        removed = []

        def opt(m):
            try:
                return replace_tags(m.group(1), True)
            except Unsupported:
                removed.append(m.group(1).strip())
                return ""
        sql = OPTIONAL.sub(opt, sql)
        sql = replace_tags(sql, False)
        if removed:
            self.need(cid_ident, "optional_clause", "assisted",
                      f"{len(removed)} optional clause(s) on variables removed: the view equals the question with "
                      "those filters empty", "restore each as a templated filter or a parameter: " + " | ".join(removed))
        if params or filters:
            self.need(cid_ident, "template_tags", "assisted",
                      f"template tags became {len(params)} parameter(s) and {len(filters)} templated filter(s)",
                      "check each against the question in Metabase")
        return sql, params, filters

    # -- query context -------------------------------------------------------------
    def base_of(self, st):
        """('table', id) or ('card', id) for a stage."""
        if isinstance(st.get("source-table"), int):
            return ("table", st["source-table"])
        if isinstance(st.get("source-table"), str) and st["source-table"].startswith("card__"):
            return ("card", int(st["source-table"][6:]))
        if st.get("source-card"):
            return ("card", st["source-card"])
        raise Unsupported("stage has no source table or card")

    def explore_for(self, base):
        if base in self.base_explore:
            return self.base_explore[base]
        if base[0] == "table":
            view = self.view_for_table(base[1])
            t = self.est.tables[base[1]]
            label = t.get("display_name") or t["name"]
        else:
            view = self.view_for_card(base[1])
            label = self.est.cards[base[1]].get("name")
        name = self.explore_name(view)
        self.explores[name] = {"base": view, "label": label, "joins": {}, "base_ref": base}
        self.base_explore[base] = name
        return name

    def explore_name(self, view):
        """An explore is named after its base view (explores and views are separate namespaces)."""
        name, n = view, 2
        while name in self.explores:
            name, n = f"{view}_{n}", n + 1
        return name

    def add_join(self, xname, jname, spec, obj):
        joins = self.explores[xname]["joins"]
        if jname in joins:
            if joins[jname]["sql_on"] != spec["sql_on"]:
                self.need(obj, "join_conflict", "assisted",
                          f"join {jname} is defined two ways in explore {xname}; the first is kept",
                          spec["sql_on"])
            return
        joins[jname] = spec
        self.count(spec["construct"], spec["class"])
        if spec["class"] != "mechanical":
            self.need(obj, spec["construct"], spec["class"], spec["reason"], f"relationship: {spec['relationship']}")
        self.deps.append({"from": f"looker:{self.model}:explore:{xname}", "to": f"looker:{self.model}:view:{spec.get('from') or jname}",
                          "kind": "joins"})

    class Q:
        pass

    def context(self, card, st, xname):
        q = Converter.Q()
        q.card, q.st, q.xname = card, st, xname
        q.base = self.explores[xname]["base"]
        q.base_ref = self.explores[xname]["base_ref"]
        q.aliases = {}
        q.expr = {}
        return q

    def fk_join(self, q, fk_id):
        """The implicit join a field with source-field=fk_id needs; returns the join name."""
        fk = self.est.fields.get(fk_id)
        if fk is None or not fk.get("fk_target_field_id"):
            raise Unsupported(f"implicit join through field {fk_id}, which is not a foreign key in the snapshot")
        tgt = self.est.fields.get(fk["fk_target_field_id"])
        if tgt is None:
            raise Unsupported(f"foreign key target {fk['fk_target_field_id']} is not in the snapshot")
        tview = self.view_for_table(tgt["table_id"])
        if q.base_ref[0] == "table":
            lview, ldim, lgrp, _ = self.field_dim(fk_id)
            left = f"${{{q.base}.{ldim}}}"
        else:
            # a model or native question: the foreign key is one of its columns
            col = next((m for m in self.est.cards[q.base_ref[1]].get("result_metadata") or [] if m.get("id") == fk_id), None)
            if col is None:
                raise Unsupported("implicit join through a column the source card does not return")
            left = f"${{{q.base}.{bi_ir.slug(col['name'])}}}"
        _, tdim, _, _ = self.field_dim(tgt["id"])
        joins = self.explores[q.xname]["joins"]
        same = next((n for n, j in sorted(joins.items()) if (j.get("from") or n) == tview
                     and j["sql_on"] == f"{left} = ${{{n}.{tdim}}}"), None)
        if same:
            return same
        jname = tview
        if jname in joins and joins[jname].get("via") != fk_id:
            jname = f"{tview}_via_{bi_ir.slug(fk['name'])}"
        pk = tgt.get("semantic_type") == "type/PK"
        self.add_join(q.xname, jname, {
            "from": tview if jname != tview else None, "type": "left_outer",
            "relationship": "many_to_one" if pk else "many_to_many",
            "sql_on": f"{left} = ${{{jname}.{tdim}}}", "via": fk_id, "construct": "fk_join",
            "class": "mechanical" if pk else "assisted",
            "reason": "foreign key in Metabase's metadata" if pk else "foreign key to a field that is not a primary key"},
            self.est.ident("card", q.card["id"]))
        return jname

    def join_stage(self, q, j):
        alias = j.get("alias")
        jst = (j.get("stages") or [{}])[0] if "stages" in j else j
        src = self.base_of(jst)
        tview = self.view_for_table(src[1]) if src[0] == "table" else self.view_for_card(src[1])
        jname = bi_ir.slug(alias) if alias and bi_ir.slug(alias) != tview else tview
        q.aliases[alias] = (jname, src)
        conds = j.get("conditions") or ([j["condition"]] if j.get("condition") else [])
        ons, rel = [], "many_to_many"
        for c in conds:
            op, _, args = parts(c)
            if op != "=" or len(args) != 2:
                raise Unsupported(f"join condition {op}")
            l, r = self.ref_sql(args[0], q), self.ref_sql(args[1], q)
            ons.append(f"{l} = {r}")
            lf, rf = self.field_of(args[0]), self.field_of(args[1])
            if rf and rf.get("semantic_type") == "type/PK":
                rel = "many_to_one"
            elif lf and lf.get("semantic_type") == "type/PK":
                rel = "one_to_many"
        jt = {"left-join": "left_outer", "inner-join": "inner", "full-join": "full_outer"}.get(j.get("strategy", "left-join"))
        if jt is None:
            raise Unsupported(f"join strategy {j.get('strategy')}")
        mech = rel == "many_to_one"
        self.add_join(q.xname, jname, {"from": tview if jname != tview else None, "type": jt, "relationship": rel,
                                       "sql_on": " AND ".join(ons), "construct": "question_join",
                                       "class": "mechanical" if mech else "assisted",
                                       "reason": "join to a primary key" if mech else
                                       f"{rel}: the join is not to a primary key in Metabase's metadata"},
                      self.est.ident("card", q.card["id"]))

    def field_of(self, ref):
        op, opts, args = parts(ref)
        if op == "field" and isinstance(args[0], int):
            return self.est.fields.get(args[0])
        return None

    def resolve(self, ref, q):
        """A field reference as (view, name, is_group, base_type, temporal_unit)."""
        op, opts, args = parts(ref)
        if op == "expression":
            name = args[0]
            if name not in q.expr:
                raise Unsupported(f"custom column {name} was not emitted")
            return q.expr[name]
        if op != "field":
            raise Unsupported(f"reference {op}")
        fid = args[0]
        unit = opts.get("temporal-unit")
        if isinstance(fid, str):
            if fid in q.expr:
                return q.expr[fid]
            if q.base_ref[0] == "card":
                v = self.views[q.base]
                n = bi_ir.slug(fid)
                if n in v["groups"]:
                    return (q.base, n, True, opts.get("base-type"), unit)
                if n in v["dims"]:
                    return (q.base, n, False, opts.get("base-type"), unit)
            ja = opts.get("join-alias")
            if ja in q.aliases and q.aliases[ja][1][0] == "card":
                jv = self.views[self.card_view[q.aliases[ja][1][1]]]
                n = bi_ir.slug(fid)
                if n in jv["groups"] or n in jv["dims"]:
                    return (q.aliases[ja][0], n, n in jv["groups"], opts.get("base-type"), unit)
            raise Unsupported(f"column {fid!r} not found")
        if opts.get("join-alias"):
            ja = opts["join-alias"]
            if ja not in q.aliases:
                raise Unsupported(f"join alias {ja} not found")
            jname = q.aliases[ja][0]
            _, n, g, f = self.field_dim(fid)
            return (jname, n, g, f.get("effective_type") or f.get("base_type"), unit)
        if opts.get("source-field"):
            jname = self.fk_join(q, opts["source-field"])
            _, n, g, f = self.field_dim(fid)
            return (jname, n, g, f.get("effective_type") or f.get("base_type"), unit)
        if q.base_ref[0] == "card":
            col = next((m for m in self.est.cards[q.base_ref[1]].get("result_metadata") or [] if m.get("id") == fid), None)
            if col is None:
                raise Unsupported(f"field {fid} is not a column of the source card")
            n = bi_ir.slug(col["name"])
            v = self.views[q.base]
            return (q.base, n, n in v["groups"], col.get("effective_type") or col.get("base_type"), unit)
        view, n, g, f = self.field_dim(fid)
        if view != q.base:
            raise Unsupported(f"field {f['name']} is on another table with no join")
        return (view, n, g, f.get("effective_type") or f.get("base_type"), unit)

    def ref_sql(self, ref, q):
        view, n, g, _, _ = self.resolve(ref, q)
        return f"${{{view}.{n}_raw}}" if g else f"${{{view}.{n}}}"

    def field_name(self, res, unit=None, for_filter=False):
        view, n, g, base, u = res
        unit = unit or u
        if not g:
            if unit:
                raise Unsupported(f"date grouping on a non-date field {n}")
            return f"{view}.{n}"
        if unit is None:
            return f"{view}.{n}_date" if for_filter or TEMPORAL.get(base) == "date" else f"{view}.{n}_time"
        tf = TIMEFRAME.get(unit)
        if tf is None:
            raise Unsupported(f"date grouping {unit}")
        self.views[view]["groups"][n]["timeframes"].add(tf)
        return f"{view}.{n}_{tf}"

    # -- expressions (custom columns) -----------------------------------------------
    def expr_sql(self, x, q, home):
        """SQL for an expression on view `home`. Raises Unsupported."""
        if isinstance(x, bool):
            return "TRUE" if x else "FALSE"
        if isinstance(x, (int, float)):
            return tidy_num(x)
        if isinstance(x, str):
            return "'" + x.replace("'", "''") + "'"
        op, opts, args = parts(x)
        e = lambda y: self.expr_sql(y, q, home)  # noqa: E731
        if op == "value":
            return e(args[0])
        if op in ("field", "expression"):
            view, n, g, _, _ = self.resolve(x, q)
            if view != home:
                raise Unsupported("custom column reads fields from more than one table")
            return f"${{{n}_raw}}" if g else f"${{{n}}}"
        if op in ("+", "-", "*") and args:
            return "(" + f" {op} ".join(e(a) for a in args) + ")"
        if op == "/" and len(args) == 2:
            return f"({e(args[0])}) / NULLIF({e(args[1])}, 0)"
        if op in ("=", "!=", "<", ">", "<=", ">=") and len(args) == 2:
            return f"{e(args[0])} {'<>' if op == '!=' else op} {e(args[1])}"
        if op == "=" and len(args) > 2:
            return f"{e(args[0])} IN ({', '.join(e(a) for a in args[1:])})"
        if op in ("and", "or"):
            return "(" + f" {op.upper()} ".join(e(a) for a in args) + ")"
        if op == "not":
            return f"NOT ({e(args[0])})"
        if op in ("is-null", "not-null"):
            return f"{e(args[0])} IS {'NOT ' if op == 'not-null' else ''}NULL"
        if op in ("contains", "starts-with", "ends-with", "does-not-contain"):
            a, b = e(args[0]), e(args[1])
            if not opts.get("case-sensitive", True):
                a, b = f"LOWER({a})", f"LOWER({b})"
            pat = {"contains": f"CONCAT('%', {b}, '%')", "does-not-contain": f"CONCAT('%', {b}, '%')",
                   "starts-with": f"CONCAT({b}, '%')", "ends-with": f"CONCAT('%', {b})"}[op]
            return f"{a} {'NOT ' if op == 'does-not-contain' else ''}LIKE {pat}"
        if op in ("case", "if"):
            pairs = args[0] if args else []
            default = opts.get("default", args[1] if len(args) > 1 else None)
            whens = " ".join(f"WHEN {e(p)} THEN {e(v)}" for p, v in pairs)
            return f"CASE {whens}" + (f" ELSE {e(default)}" if default is not None else "") + " END"
        simple = {"coalesce": "COALESCE", "concat": "CONCAT", "lower": "LOWER", "upper": "UPPER", "trim": "TRIM",
                  "ltrim": "LTRIM", "rtrim": "RTRIM", "length": "LENGTH", "abs": "ABS", "round": "ROUND",
                  "floor": "FLOOR", "ceil": "CEIL", "sqrt": "SQRT", "power": "POWER", "log": "LOG10", "exp": "EXP",
                  "substring": "SUBSTR", "replace": "REPLACE"}
        if op in simple:
            return f"{simple[op]}({', '.join(e(a) for a in args)})"
        raise Unsupported(f"function {op}")

    def home_of(self, x, q, found=None):
        found = set() if found is None else found
        op, opts, args = parts(x)
        if op in ("field", "expression"):
            found.add(self.resolve(x, q)[0])
            return found
        for a in args:
            if isinstance(a, list):
                for y in (a if (a and isinstance(a[0], list)) else [a]):
                    if isinstance(y, list) and y and isinstance(y[0], list):
                        for z in y:
                            self.home_of(z, q, found)
                    else:
                        self.home_of(y, q, found)
        if isinstance(opts.get("default"), list):
            self.home_of(opts["default"], q, found)
        return found

    def emit_expression(self, name, x, q):
        homes = self.home_of(x, q)
        home = sorted(homes)[0] if len(homes) == 1 else q.base
        if len(homes) > 1:
            raise Unsupported("custom column reads fields from more than one table")
        sql = self.expr_sql(x, q, home)
        dname = bi_ir.slug(name)
        v = self.views[home]
        boolean = parts(x)[0] in ("=", "!=", "<", ">", "<=", ">=", "and", "or", "not", "is-null", "not-null",
                                  "contains", "starts-with", "ends-with", "does-not-contain")
        entry = {"label": name, "sql": sql, "type": "yesno" if boolean else
                 ("string" if parts(x)[0] in ("concat", "lower", "upper", "trim", "ltrim", "rtrim", "substring", "replace") else "number")}
        prev = v["dims"].get(dname)
        if prev and prev.get("sql") != sql:
            dname = f"{dname}_{short_hash(x)}"
        v["dims"][dname] = entry
        q.expr[name] = (home, dname, False, None, None)

    # -- filters as Looker filter expressions --------------------------------------
    def filters(self, pred, q):
        """[(looker field, filter expression)] for a filter clause (AND of conditions)."""
        op, opts, args = parts(pred)
        if op == "and":
            return [c for a in args for c in self.filters(a, q)]
        if op == "or":
            subs = [self.filters(a, q) for a in args]
            if all(len(s) == 1 for s in subs) and len({s[0][0] for s in subs}) == 1 \
                    and all(not s[0][1].startswith(("-", ">", "<", "[")) for s in subs):
                return [(subs[0][0][0], ",".join(s[0][1] for s in subs))]
            raise Unsupported("OR across different fields or conditions")
        if op == "segment":
            raise Unsupported("segment")
        res = self.resolve(args[0], q)
        temporal = res[2]
        vals = args[1:]

        def lit(v):
            if isinstance(v, list):
                vop, _, vargs = parts(v)
                if vop == "value":
                    return lit(vargs[0])
                raise Unsupported("filter on an expression value")
            return v

        if op == "time-interval":
            n, unit = vals[0], vals[1] if len(vals) > 1 else "day"
            f = self.field_name(res, for_filter=True)
            if n == "current" or n == 0:
                return [(f, f"this {unit}")]
            k = abs(int(n))
            if int(n) < 0:
                return [(f, f"{k + 1} {unit}s" if opts.get("include-current") else f"{k} {unit}s ago for {k} {unit}s")]
            raise Unsupported("a time interval in the future")
        if op in ("relative-time-interval", "inside", "during"):
            raise Unsupported(op)
        field = self.field_name(res, for_filter=True) if temporal else self.field_name(res)
        if op in ("is-null", "not-null"):
            return [(field, "NULL" if op == "is-null" else "-NULL")]
        if op in ("is-empty", "not-empty"):
            return [(field, "EMPTY" if op == "is-empty" else "-EMPTY")]
        vals = [lit(v) for v in vals]
        def fmt(v):
            if temporal:
                return str(v)[:10]
            if isinstance(v, bool):              # before numbers: True is an int in Python
                return "Yes" if v else "No"
            return tidy_num(v) if isinstance(v, (int, float)) else esc_filter(v)
        if op in ("in", "not-in"):
            op = "=" if op == "in" else "!="
        if op == "=":
            if temporal and res[4] and res[4] not in ("day",):
                raise Unsupported(f"equality on a date grouped by {res[4]}")
            return [(field, ",".join(fmt(v) for v in vals))]
        if op == "!=":
            return [(field, ",".join("-" + fmt(v) for v in vals))]
        if op in ("<", ">", "<=", ">="):
            if temporal:
                d = str(vals[0])[:10]
                return [(field, {"<": f"before {d}", ">=": f"after {d}", ">": f"after {next_day(d)}",
                                 "<=": f"before {next_day(d)}"}[op])]
            return [(field, f"{op}{fmt(vals[0])}")]
        if op == "between":
            if temporal:
                return [(field, f"{str(vals[0])[:10]} to {next_day(str(vals[1]))}")]
            return [(field, f"[{fmt(vals[0])}, {fmt(vals[1])}]")]
        if op in ("contains", "starts-with", "ends-with", "does-not-contain"):
            s = esc_filter(vals[0])
            pat = {"contains": f"%{s}%", "starts-with": f"{s}%", "ends-with": f"%{s}", "does-not-contain": f"-%{s}%"}[op]
            return [(field, pat)]
        raise Unsupported(f"filter {op}")

    # -- aggregations as measures --------------------------------------------------
    def measure(self, agg, q):
        """Looker field (view.measure) for an aggregation clause; emits the measure."""
        op, opts, args = parts(agg)
        label = opts.get("display-name") or opts.get("name")
        if op == "aggregation-options":
            return self.measure(args[0], q)
        if op == "count" and not args:
            return f"{q.base}.{self.ensure_count(q.base)}"
        if op == "metric":
            return self.metric(args[0], q)
        if op in AGG or op == "count":
            view, n, g, _, _ = self.resolve(args[0], q)
            ref = f"${{{n}_raw}}" if g else f"${{{n}}}"
            if op == "count":
                name, spec = f"count_{n}", {"type": "count", "filters": [(f"{view}.{n}" if not g else f"{view}.{n}_raw", "-NULL")]}
            else:
                lt, prefix = AGG[op]
                name, spec = f"{prefix}_{n}", {"type": lt, "sql": ref}
            spec["label"] = label or f"{op.title()} of {self.views[view]['dims'].get(n, self.views[view]['groups'].get(n, {})).get('label', n)}"
            self.views[view]["measures"].setdefault(name, spec)
            return f"{view}.{name}"
        if op in ("count-where", "sum-where", "distinct-where"):
            pred = args[-1]
            conds = self.filters(pred, q)
            if op == "count-where":
                view, name = q.base, f"count_where_{short_hash(pred)}"
                spec = {"type": "count"}
            else:
                view, n, g, _, _ = self.resolve(args[0], q)
                name = f"{'total' if op == 'sum-where' else 'count_distinct'}_{n}_where_{short_hash(pred)}"
                spec = {"type": "sum" if op == "sum-where" else "count_distinct", "sql": f"${{{n}}}"}
            spec["filters"] = conds
            where = " and ".join(f"{f.split('.', 1)[1].replace('_', ' ')} is {e}" for f, e in conds)
            spec["label"] = label or f"{'Count' if op == 'count-where' else name.split('_where_')[0].replace('_', ' ').title()} where {where}"
            self.views[view]["measures"].setdefault(bi_ir.slug(label) if label else name, spec)
            return f"{view}.{bi_ir.slug(label) if label else name}"
        if op in ("percentile",):
            view, n, g, _, _ = self.resolve(args[0], q)
            p = args[1]
            name = f"p{int(float(p) * 100)}_{n}"
            self.views[view]["measures"].setdefault(name, {"type": "percentile", "percentile": int(float(p) * 100),
                                                           "sql": f"${{{n}}}", "label": label or name})
            return f"{view}.{name}"
        if op in ("cum-sum", "cum-count"):
            inner = self.measure(["sum", {}, args[0]] if op == "cum-sum" else ["count", {}], q)
            view, m = inner.split(".")
            name = f"running_{m}"
            self.views[view]["measures"].setdefault(name, {"type": "running_total", "sql": f"${{{m}}}",
                                                           "label": label or f"Running {m.replace('_', ' ')}"})
            self.need(self.est.ident("card", q.card["id"]), "cumulative", "assisted",
                      "cumulative aggregation became a running_total measure: it runs down the result rows, "
                      "so check sorts and pivots", None)
            return f"{view}.{name}"
        if op in ("+", "-", "*", "/"):
            refs, homes = [], set()

            def walk(y):
                if isinstance(y, (int, float)):
                    return tidy_num(y)
                yop, _, yargs = parts(y)
                if yop in ("+", "-", "*"):
                    return "(" + f" {yop} ".join(walk(a) for a in yargs) + ")"
                if yop == "/":
                    return f"({walk(yargs[0])}) / NULLIF({walk(yargs[1])}, 0)"
                f = self.measure(y, q)
                homes.add(f.split(".")[0])
                refs.append(f)
                return f"${{{f}}}"
            sql = walk(agg)
            if len(homes) != 1:
                raise Unsupported("an aggregation expression over measures on more than one table")
            view = homes.pop()
            name = bi_ir.slug(label) if label else f"measure_{short_hash(agg)}"
            sql = sql.replace(f"${{{view}.", "${")
            self.views[view]["measures"].setdefault(name, {"type": "number", "sql": sql, "label": label or name})
            return f"{view}.{name}"
        if op in ("stddev", "var", "share", "offset"):
            raise Unsupported(f"aggregation {op}")
        raise Unsupported(f"aggregation {op}")

    def metric(self, mid, q):
        if mid in self.metric_measure:
            return self.metric_measure[mid]
        m = self.est.cards.get(mid)
        if m is None:
            raise Unsupported(f"metric {mid} is not in the snapshot")
        mst = stages(m["dataset_query"])
        if len(mst) != 1 or not mst[0].get("aggregation"):
            raise Unsupported(f"metric {m.get('name')} is not a single aggregation")
        base = self.base_of(mst[0])
        if base != q.base_ref:
            raise Unsupported(f"metric {m.get('name')} is on another table")
        mq = self.context(m, mst[0], q.xname)
        f = self.measure(mst[0]["aggregation"][0], mq)
        view, inner = f.split(".")
        conds = [c for flt in mst[0].get("filters", []) for c in self.filters(flt, mq)]
        name = bi_ir.slug(m.get("name"))
        spec = dict(self.views[view]["measures"][inner])
        spec["label"] = m.get("name")
        if m.get("description"):
            spec["description"] = m["description"]
        if conds:
            spec["filters"] = list(spec.get("filters", [])) + conds
        if spec.get("type") == "count" and not spec.get("sql"):
            spec.pop("sql", None)
        self.views[view]["measures"][name] = spec
        self.metric_measure[mid] = f"{view}.{name}"
        self.count("metric", "mechanical")
        self.deps.append({"from": self.est.ident("card", mid), "to": f"looker:{self.model}:field:{view}.{name}",
                          "kind": "contains"})
        return self.metric_measure[mid]

    # -- one question to one element -----------------------------------------------
    def convert_card(self, cid):
        if cid in self.elements:
            return self.elements[cid]
        c = self.est.cards[cid]
        obj = self.est.ident("card", cid)
        self.elements[cid] = None
        if c.get("archived"):
            self.card_class[cid] = ("drop", "archived")
            return None
        engine = self.est.engine(c.get("database_id"))
        try:
            el, cls, reasons = self._convert_card(c)
        except Unsupported as e:
            self.card_class[cid] = ("redesign", f"not converted: {e}")
            self.count(f"{self.est.card_kind(c)}_question", "redesign")
            self.need(obj, f"{self.est.card_kind(c)}_question", "redesign", f"question not converted: {e}",
                      f"Metabase: {c.get('name')}")
            return None
        if engine in NO_LOOKER:
            cls, reasons = "redesign", reasons + [f"database engine {engine} has no Looker connection"]
        self.card_class[cid] = (cls, "; ".join(reasons))
        self.count(f"{self.est.card_kind(c)}_question", cls)
        self.elements[cid] = el
        return el

    def _convert_card(self, c):
        cid = c["id"]
        reasons, cls = [], "mechanical"
        sts = stages(c.get("dataset_query") or {})
        display = c.get("display") or "table"
        vs = c.get("visualization_settings") or {}
        if self.est.card_kind(c) == "native":
            view = self.view_for_card(cid)
            xname = self.explore_for(("card", cid))
            v = self.views[view]
            cols = [m.get("name") for m in c.get("result_metadata") or [] if m.get("name")]
            col_field = {}
            for col in cols:
                n = bi_ir.slug(col)
                if n in v["groups"]:
                    col_field[col] = f"{view}.{n}_time" if v["groups"][n]["datatype"] == "timestamp" else f"{view}.{n}_date"
                elif n in v["dims"]:
                    col_field[col] = f"{view}.{n}"
            fields = [col_field[c_] for c_ in cols if c_ in col_field]
            d = self.est.dialect(c.get("database_id"))
            sql = sts[0].get("native") or ""
            sorts = [f"{col_field[col]} {dirn}" for col, dirn in sql_order(sql, d, cols) if col in col_field]
            el = {"explore": xname, "fields": fields, "sorts": sorts or None, "limit": 500}
            cls, reasons = "assisted", ["native SQL: a view on the question's SQL"]
            self.need(self.est.ident("card", cid), "native_sql", "assisted",
                      "native SQL question became a view on its SQL: exact, but not reusable",
                      "remodel onto shared views, or keep")
            self.lift(c, sql, d)
        else:
            if len(sts) > 2 or (len(sts) == 2 and any(k in sts[1] for k in ("aggregation", "breakout", "joins", "expressions"))):
                raise Unsupported("a multi-stage question (aggregates of aggregates)")
            st = sts[0]
            base = self.base_of(st)
            xname = self.explore_for(base)
            q = self.context(c, st, xname)
            for j in st.get("joins", []):
                self.join_stage(q, j)
            exprs = st.get("expressions") or []
            # MBQL 5: a list, each named in its options; legacy MBQL: {name: clause}
            named = [(parts(x)[1].get("lib/expression-name") or parts(x)[1].get("name"), x) for x in exprs] \
                if isinstance(exprs, list) else sorted(exprs.items())
            for name, ex in named:
                try:
                    self.emit_expression(name, ex, q)
                    self.count("custom_column", "assisted")
                except Unsupported as e:
                    self.count("custom_column", "redesign")
                    self.need(self.est.ident("card", cid, "expression", name), "custom_column", "redesign",
                              f"custom column not translated: {e}", json.dumps(canon(ex))[:400])
                    raise Unsupported(f"custom column {name}: {e}")
            if st.get("expressions"):
                cls, reasons = "assisted", reasons + ["custom columns translated to SQL"]
            dims = []
            for b in st.get("breakout", []):
                bop, bopts, _ = parts(b)
                if bopts.get("binning"):
                    bn = bopts["binning"]
                    if bn.get("strategy") == "bin-width" and bn.get("bin-width"):
                        res = self.resolve(b, q)
                        w = tidy_num(bn["bin-width"])
                        bname = f"{res[1]}_bin_{w.replace('.', '_')}"
                        self.views[res[0]]["dims"].setdefault(bname, {"type": "number", "label": f"{res[1]} (bin {w})",
                                                                      "sql": f"FLOOR(${{{res[1]}}} / {w}) * {w}"})
                        dims.append(f"{res[0]}.{bname}")
                        cls, reasons = "assisted", reasons + ["bin by width"]
                        continue
                    raise Unsupported("binning by number of bins: Metabase picks the width from the data range")
                dims.append(self.field_name(self.resolve(b, q)))
            measures = []
            for a in st.get("aggregation", []):
                measures.append(self.measure(a, q))
            fields = dims + [m for m in measures if m not in dims]
            if not st.get("aggregation") and not st.get("breakout"):
                # a raw-row question: its fields (or every field of the base view)
                cols = st.get("fields") or []
                fields = [self.field_name(self.resolve(f, q)) for f in cols] or \
                    [f"{q.base}.{n}" for n in sorted(self.views[q.base]["dims"])][:30]
                cls, reasons = "assisted", reasons + ["raw rows: an element with no measures"]
            filt = {}
            for flt in st.get("filters", []):
                for f, e in self.filters(flt, q):
                    filt[f] = e if f not in filt else f"{filt[f]},{e}"
            agg_names = {}
            for i, a in enumerate(st.get("aggregation", [])):
                aop, aopts, _ = parts(a)
                for k in (aopts.get("lib/uuid"), aopts.get("name"), aopts.get("display-name"), aop):
                    if k:
                        agg_names.setdefault(k, measures[i])
            if len(sts) == 2:
                # A filter on a grouping column in the next stage is a filter on that dimension; a filter on
                # an aggregation is a HAVING filter in Looker too
                breakout_by_name = {}
                for b in st.get("breakout", []):
                    bop, bopts, bargs = parts(b)
                    if isinstance(bargs[0], int) and bargs[0] in self.est.fields:
                        breakout_by_name.setdefault(self.est.fields[bargs[0]]["name"], b)
                    elif isinstance(bargs[0], str):
                        breakout_by_name.setdefault(bargs[0], b)
                for flt in sts[1].get("filters", []):
                    fop, fopts, fargs = parts(flt)
                    target = parts(fargs[0])[2][0] if fargs else None
                    if target in breakout_by_name and target not in agg_names:
                        bop, bopts, bargs = parts(breakout_by_name[target])
                        ref = ["field", {k: v for k, v in bopts.items() if k not in ("temporal-unit", "binning")}, bargs[0]]
                        for f, e in self.filters([fop, fopts, ref, *fargs[1:]], q):
                            filt[f] = e if f not in filt else f"{filt[f]},{e}"
                        continue
                    if target not in agg_names:
                        raise Unsupported("a second-stage filter that is not on an aggregation or a grouping column")
                    vals = [v for v in fargs[1:]]
                    expr = {">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "", "!=": "-"}.get(fop)
                    if expr is None:
                        raise Unsupported(f"second-stage filter {fop}")
                    filt[agg_names[target]] = f"{expr}{tidy_num(vals[0])}"
                cls, reasons = ("assisted" if cls == "mechanical" else cls), reasons + ["filter on an aggregation"]
            sorts = []
            for o in st.get("order-by", []) + (sts[1].get("order-by", []) if len(sts) == 2 else []):
                oop, _, oargs = parts(o)
                target = oargs[0]
                top, topts, targs = parts(target)
                if top == "aggregation":
                    idx = targs[0]
                    f = measures[idx] if isinstance(idx, int) and idx < len(measures) else agg_names.get(idx)
                elif top == "field" and isinstance(targs[0], str) and len(sts) == 2:
                    f = next((measures[i] for i, a in enumerate(st.get("aggregation", []))
                              if targs[0] in (parts(a)[1].get("name"), parts(a)[0])), None)
                else:
                    try:
                        f = self.field_name(self.resolve(target, q))
                    except Unsupported:
                        f = None
                if f is None:
                    raise Unsupported("a sort on a field the question does not return")
                sorts.append(f"{f} {'desc' if oop == 'desc' else 'asc'}")
            if not sorts and dims:
                # Metabase sorts a grouped result by its breakouts, ascending, unless told otherwise
                sorts = [f"{d} asc" for d in dims]
            limit = st.get("limit") or (sts[1].get("limit") if len(sts) == 2 else None) or 500
            el = {"explore": xname, "fields": fields, "filters": filt or None, "sorts": sorts or None, "limit": limit}
            if len(dims) == 2 and display in ("line", "bar", "area", "row", "combo"):
                el["pivots"] = [dims[1]]
        lt = VIZ.get(display)
        if lt is None:
            el["type"] = "looker_grid"
            cls, reasons = ("assisted" if cls == "mechanical" else cls), reasons + [f"{display} chart has no Looker equivalent: shown as a table"]
            self.count("visualisation", "drop")
        else:
            el["type"] = lt
            if display in VIZ_ASSISTED:
                cls, reasons = ("assisted" if cls == "mechanical" else cls), reasons + [f"{display} chart: check the Looker settings"]
        el["title"] = vs.get("card.title") or c.get("name")
        return el, cls, reasons

    def lift(self, c, sql, dialect):
        cid = c["id"]
        res, why = lift_sql(sql, dialect)
        obj = self.est.ident("card", cid)
        if res is None:
            self.need(obj, "sql_lift", "assisted", f"not lifted: {why}", None)
            return
        det = (self.est.dbs.get(c.get("database_id")) or {}).get("details") or {}
        table = res["table"]
        if dialect == "bigquery" and det.get("project-id") and table.count(".") == 1:
            table = f"{det['project-id']}.{table}"
        tname = table.split(".")[-1]
        tid = next((t["id"] for t in self.est.tables.values()
                    if t["name"] == tname and t.get("db_id") == c.get("database_id")), None)
        if tid is not None:
            view = self.view_for_table(tid)
        else:
            view = next((n for n, v in self.views.items() if v.get("lifted_table") == table), None)
            if view is None:
                view = self.unique(bi_ir.slug(tname))
                self.views[view] = {"source": {"table": f"`{table}`" if dialect == "bigquery" else table}, "dims": {},
                                    "groups": {}, "measures": {}, "params": {}, "filters": {}, "label": tname,
                                    "lifted_table": table}
        v = self.views[view]
        added = []
        for name, s in res["dims"]:
            same = v["dims"].get(name, {}).get("sql") == s
            n = name if same else free_name(v, name)
            v["dims"].setdefault(n, {"type": "string", "label": name.replace("_", " ").title(), "sql": s, "lifted": cid})
            added.append(f"dimension {n}")
        for name, kind, s in res["measures"]:
            same = v["measures"].get(name, {}).get("sql") == s and v["measures"].get(name, {}).get("type") == kind
            n = name if same else free_name(v, name)
            spec = {"type": kind, "label": name.replace("_", " ").title(), "lifted": cid}
            if s:
                spec["sql"] = s
            v["measures"].setdefault(n, spec)
            added.append(f"measure {n}")
        if tid is not None:
            self.explore_for(("table", tid))
        elif not any(x["base"] == view for x in self.explores.values()):
            self.explores[self.explore_name(view)] = {"base": view, "label": v["label"], "joins": {},
                                                     "base_ref": ("table", None)}
        self.count("sql_lift", "assisted")
        self.need(obj, "sql_lift", "assisted",
                  f"simple single-table SQL lifted onto view {view}: " + ", ".join(added) +
                  (f"; WHERE clause not lifted: {res['where']}" if res["where"] else ""),
                  "a proposal: keep the fields that belong in the shared model, and filter tiles with Looker filters")

    # -- dashboards -----------------------------------------------------------------
    def convert_dashboard(self, did):
        d = self.est.dashboards[did]
        dobj = self.est.ident("dashboard", did)
        tabs = d.get("tabs") or []
        groups = [(None, d["name"])] if not tabs else [(t["id"], f"{d['name']} - {t['name']}") for t in
                                                         sorted(tabs, key=lambda t: (t.get("position", 0), t["id"]))]
        if tabs:
            self.count("dashboard_tab", "assisted")
            self.need(dobj, "dashboard_tabs", "assisted", f"{len(tabs)} tabs became {len(tabs)} LookML dashboards",
                      "link them, or merge into one dashboard")
        files = {}
        self.param_tiles = {}
        for tab, title in groups:
            dcs = [x for x in d.get("dashcards", []) if tab is None or x.get("dashboard_tab_id") == tab]
            elements, used = [], {}
            for dc in sorted(dcs, key=lambda x: (x["row"], x["col"], x["id"])):
                pos = {"row": dc["row"], "col": dc["col"], "width": dc["size_x"], "height": dc["size_y"]}
                vs = dc.get("visualization_settings") or {}
                virt = (vs.get("virtual_card") or {}).get("display")
                if dc.get("card_id") is None:
                    if virt in ("heading", "text"):
                        raw = vs.get("text") or ""
                        text = TAG.sub(lambda m: f"(the {m.group(1).strip().replace('_', ' ')} filter)", raw)
                        el = {"name": f"text_{dc['id']}", "type": "text"}
                        el["title_text" if virt == "heading" else "body_text"] = text
                        if TAG.search(raw):
                            self.need(self.est.ident("dashboard", did, "dashcard", dc["id"]), "text_variable", "assisted",
                                      "text card showed a filter value; Looker text tiles cannot, so the tag became plain words",
                                      raw[:200])
                        elements.append({**el, **pos})
                        self.count("text_card", "mechanical")
                    else:
                        self.count(f"{virt or 'unknown'}_card", "drop")
                        self.need(self.est.ident("dashboard", did, "dashcard", dc["id"]), f"{virt or 'unknown'}_card",
                                  "drop", f"{virt} card not migrated", None)
                    continue
                el = self.convert_card(dc["card_id"])
                if el is None:
                    self.need(self.est.ident("dashboard", did, "dashcard", dc["id"]), "tile", "assisted",
                              f"tile not emitted: {self.card_class.get(dc['card_id'], ('', ''))[1]}", None)
                    continue
                name = f"{bi_ir.slug(el['title'])}_{dc['id']}"
                e = {"name": name, "title": vs.get("card.title") or el["title"], "model": self.model,
                     "explore": el["explore"], "type": el["type"], "fields": el["fields"]}
                for k in ("pivots", "filters", "sorts", "limit"):
                    if el.get(k):
                        e[k] = el[k]
                e.update(pos)
                elements.append(e)
                used[dc["id"]] = (e, dc)
                self.count("tile", "mechanical")
                self.deps.append({"from": dobj, "to": self.est.ident("card", dc["card_id"]), "kind": "contains"})
                if dc.get("series"):
                    self.need(self.est.ident("dashboard", did, "dashcard", dc["id"]), "combined_series", "assisted",
                              f"{len(dc['series'])} card(s) combined into this chart: only the first is migrated", None)
                if vs.get("click_behavior"):
                    self.need(self.est.ident("dashboard", did, "dashcard", dc["id"]), "click_behavior", "drop",
                              "click behaviour not migrated", "Looker drill fields or links")
            filters = self.dashboard_filters(d, used, did)
            doc = [{"dashboard": bi_ir.slug(title), "title": title, "layout": "newspaper",
                    "preferred_viewer": "dashboards-next",
                    "description": f"Migrated from Metabase dashboard {d['name']} (mb_to_lookml {VERSION}, experimental)",
                    **({"filters": filters} if filters else {}), "elements": elements}]
            self.dash_docs.append({**doc[0], "source_id": dobj if tab is None else self.est.ident("dashboard", did, "tab", tab),
                                   "source_kind": "dashboard"})
            files[f"{self.root}dashboards/{bi_ir.slug(title)}.dashboard.lookml"] = yaml.safe_dump(
                doc, sort_keys=False, allow_unicode=True, width=1000)
            self.count("dashboard", "mechanical")
        return files

    def dashboard_filters(self, d, used, did):
        out = []
        for p in d.get("parameters") or []:
            pobj = self.est.ident("dashboard", did, "parameter", p["id"])
            ptype = p.get("type", "")
            if ptype == "temporal-unit":
                if (did, p["id"], "temporal") not in self.reported:
                    self.reported.add((did, p["id"], "temporal"))
                    self.count("dashboard_filter", "drop")
                    self.need(pobj, "temporal_unit_filter", "drop",
                              "a filter that changes date grouping: LookML dashboard filters cannot",
                              "a parameter with a dynamic dimension in the view")
                continue
            listen, explore, field = {}, None, None
            for dcid, (e, dc) in sorted(used.items()):
                for m in dc.get("parameter_mappings") or []:
                    if m.get("parameter_id") != p["id"]:
                        continue
                    f = self.mapping_field(dc, m)
                    if f is None:
                        self.need(pobj, "filter_mapping", "assisted",
                                  f"filter mapping on tile {e['name']} not resolved", json.dumps(canon(m.get("target")))[:300])
                        continue
                    listen[e["name"]] = f
                    explore, field = explore or e["explore"], field or f
            if not listen:
                # a filter shown on every tab applies only to the tiles mapped to it; list it once, and only when
                # it reaches no migrated tile on any tab
                mapped = {m.get("card_id") for dc in d.get("dashcards", []) for m in dc.get("parameter_mappings") or []
                          if m.get("parameter_id") == p["id"] and dc.get("card_id")}
                reached = any(self.elements.get(c) for c in mapped)
                if not reached and (did, p["id"], "unmapped") not in self.reported:
                    self.reported.add((did, p["id"], "unmapped"))
                    self.count("dashboard_filter", "assisted")
                    self.need(pobj, "dashboard_filter", "assisted", f"filter {p.get('name')} maps to no migrated tile", None)
                continue
            flt = {"name": p.get("name"), "title": p.get("name"), "type": "field_filter",
                   "default_value": self.param_default(p, pobj), "allow_multiple_values": True,
                   "required": bool(p.get("required")), "model": self.model, "explore": explore, "field": field}
            if ptype not in ("string/=", "category", "id", "number/=") and not ptype.startswith("date/"):
                self.need(pobj, "filter_operator", "assisted",
                          f"filter operator {ptype}: the Looker filter's default condition must match", None)
            out.append(flt)
            self.count("dashboard_filter", "mechanical")
            for e, dc in used.values():
                if e["name"] in listen:
                    e.setdefault("listen", {})[p.get("name")] = listen[e["name"]]
                    if listen[e["name"]] in (e.get("filters") or {}):
                        self.need(self.est.ident("dashboard", did, "dashcard", dc["id"]), "filter_override", "assisted",
                                  f"the tile filters {listen[e['name']]} itself and listens to dashboard filter "
                                  f"{p.get('name')} on the same field: Metabase applies both, Looker's dashboard filter "
                                  "replaces the tile's", "move the tile's condition to another field, or accept the difference")
        return out

    def mapping_field(self, dc, m):
        target = m.get("target") or []
        if len(target) < 2:
            return None
        if target[0] in ("variable", "dimension") and isinstance(target[1], list) and target[1][:1] == ["template-tag"]:
            view = self.card_view.get(dc["card_id"])
            name = bi_ir.slug(target[1][1] if not isinstance(target[1][1], dict) else target[1][1].get("id", ""))
            if view and (name in self.views[view]["filters"] or name in self.views[view]["params"]):
                return f"{view}.{name}"
            return None
        if target[0] != "dimension":
            return None
        c = self.est.cards.get(dc["card_id"])
        sts = stages(c.get("dataset_query") or {})
        stage_n = (target[2] or {}).get("stage-number", 0) if len(target) > 2 and isinstance(target[2], dict) else 0
        if self.est.card_kind(c) == "native" or stage_n not in (0, -1) and len(sts) > 1:
            return None
        st = sts[0]
        try:
            q = self.context(c, st, self.base_explore[self.base_of(st)])
            for j in st.get("joins", []):
                alias = j.get("alias")
                jst = (j.get("stages") or [{}])[0] if "stages" in j else j
                src = self.base_of(jst)
                tview = self.view_for_table(src[1]) if src[0] == "table" else self.view_for_card(src[1])
                q.aliases[alias] = (bi_ir.slug(alias) if alias and bi_ir.slug(alias) != tview else tview, src)
            ref = target[1]
            op, opts, args = parts(ref)
            res = self.resolve(ref, q)
            return self.field_name(res, for_filter=True) if res[2] else self.field_name(res)
        except (Unsupported, KeyError):
            return None

    def param_default(self, p, pobj):
        v = p.get("default")
        if v is None:
            return ""
        ptype = p.get("type", "")
        if ptype.startswith("date/"):
            s = v[0] if isinstance(v, list) else v
            m = re.fullmatch(r"(past|next)(\d+)(minute|hour|day|week|month|quarter|year)s(~)?", str(s))
            fixed = {"thisday": "today", "today": "today", "yesterday": "yesterday", "thisweek": "this week",
                     "thismonth": "this month", "thisquarter": "this quarter", "thisyear": "this year",
                     "lastweek": "last week", "lastmonth": "last month", "lastquarter": "last quarter",
                     "lastyear": "last year"}
            if m and m.group(1) == "past":
                k = int(m.group(2))
                return f"{k + 1} {m.group(3)}s" if m.group(4) else f"{k} {m.group(3)}s ago for {k} {m.group(3)}s"
            if str(s) in fixed:
                return fixed[str(s)]
            r = re.fullmatch(r"(\d{4}-\d{2}-\d{2})?~(\d{4}-\d{2}-\d{2})?", str(s))
            if r:
                a, b = r.groups()
                return f"{a} to {next_day(b)}" if a and b else (f"after {a}" if a else f"before {next_day(b)}")
            if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", str(s)):
                return str(s)
            self.need(pobj, "filter_default", "assisted", f"date filter default {s!r} not mapped", None)
            return ""
        vals = v if isinstance(v, list) else [v]
        return ",".join(tidy_num(x) if isinstance(x, (int, float)) else esc_filter(x) for x in vals)

    # -- primary keys on joined views without one ------------------------------------
    def check_keys(self):
        joined = {j.get("from") or n for x in self.explores.values() for n, j in x["joins"].items()} | \
                 {x["base"] for x in self.explores.values() if x["joins"]}
        for vname in sorted(joined):
            v = self.views.get(vname)
            if v and not any(dm.get("primary_key") for dm in v["dims"].values()):
                self.count("primary_key", "assisted")
                self.need(f"looker:{self.model}:view:{vname}", "primary_key", "assisted",
                          "joined view with no primary key in Metabase's metadata: totals across joins are wrong until one is set",
                          None)

    # -- render ---------------------------------------------------------------------------
    def render_view(self, name, v):
        out = [f"view: {name} {{"]
        src = v["source"]
        if "table" in src:
            out.append(f"  sql_table_name: {src['table']} ;;")
        else:
            out += ["  derived_table: {", "    sql: " + src["derived_sql"].replace("\n", "\n      ") + " ;;", "  }"]
        for pname in sorted(v["params"]):
            p = v["params"][pname]
            out += ["", f"  parameter: {pname} {{", f"    type: {p['type'] if p['type'] != 'number' else 'number'}",
                    f"    label: {lk_str(p['label'])}"]
            if p.get("default_value") is not None:
                out.append(f"    default_value: {lk_str(p['default_value'])}")
            out.append("  }")
        for fname in sorted(v["filters"]):
            fl = v["filters"][fname]
            out += ["", f"  filter: {fname} {{", f"    type: {fl['type']}", f"    label: {lk_str(fl['label'])}", "  }"]
        for dname in sorted(v["dims"]):
            dm = v["dims"][dname]
            out += ["", f"  dimension: {dname} {{"]
            if dm.get("primary_key"):
                out.append("    primary_key: yes")
            out += [f"    type: {dm['type']}", f"    label: {lk_str(dm['label'])}"]
            if dm.get("description"):
                out.append(f"    description: {lk_str(dm['description'])}")
            if dm.get("hidden"):
                out.append("    hidden: yes")
            out += [f"    sql: {dm['sql']} ;;", "  }"]
        for gname in sorted(v["groups"]):
            g = v["groups"][gname]
            order = ["raw", "time", "date", "week", "month", "quarter", "year", "minute", "hour", "day_of_week",
                     "day_of_month", "day_of_year", "week_of_year", "month_num", "quarter_of_year", "hour_of_day"]
            tfs = [t for t in order if t in g["timeframes"]]
            out += ["", f"  dimension_group: {gname} {{", "    type: time", f"    timeframes: [{', '.join(tfs)}]",
                    f"    datatype: {g['datatype']}", f"    label: {lk_str(g['label'])}"]
            if g.get("description"):
                out.append(f"    description: {lk_str(g['description'])}")
            out += [f"    sql: {g['sql']} ;;", "  }"]
        for mname in sorted(v["measures"]):
            m = v["measures"][mname]
            out += ["", f"  measure: {mname} {{", f"    type: {m['type']}", f"    label: {lk_str(m['label'])}"]
            if m.get("description"):
                out.append(f"    description: {lk_str(m['description'])}")
            if m.get("percentile"):
                out.append(f"    percentile: {m['percentile']}")
            if m.get("sql"):
                out.append(f"    sql: {m['sql']} ;;")
            for f, e in m.get("filters") or []:
                field = f.split(".", 1)[1] if f.startswith(name + ".") else f
                out.append(f"    filters: [{field}: {lk_str(e)}]")
            out.append("  }")
        out.append("}")
        return "\n".join(out) + "\n"

    def render_model(self):
        out = [f"connection: {lk_str(self.connection)}", "", f'include: "/{self.root}views/*.view.lkml"',
               f'include: "/{self.root}dashboards/*.dashboard.lookml"']
        for x in sorted(self.explores):
            e = self.explores[x]
            out += ["", f"explore: {x} {{", f"  label: {lk_str(e['label'])}"]
            if x != e["base"]:
                out.append(f"  view_name: {e['base']}")
            for jn in sorted(e["joins"]):
                j = e["joins"][jn]
                out += [f"  join: {jn} {{"]
                if j.get("from"):
                    out.append(f"    from: {j['from']}")
                out += [f"    type: {j['type']}", f"    relationship: {j['relationship']}",
                        f"    sql_on: {j['sql_on']} ;;", "  }"]
            out.append("}")
        return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Running a conversion
# ---------------------------------------------------------------------------

def scope(est: Estate, dashboards=None, cards=None, database=None):
    """Cards and dashboards in scope, in id order."""
    ds = sorted(d for d in est.dashboards if not dashboards or d in dashboards)
    if dashboards or cards:
        cs = set(cards or [])
        for d in ds:
            cs |= {dc["card_id"] for dc in est.dashboards[d].get("dashcards", []) if dc.get("card_id")}
    else:
        cs = set(est.cards)
    if database is not None:
        cs = {c for c in cs if est.cards[c].get("database_id") == database}
        ds = [d for d in ds if any(dc.get("card_id") in cs for dc in est.dashboards[d].get("dashcards", []))]
    return sorted(cs), ds


def run(est: Estate, model: str, connection: str, dashboards=None, cards=None, database=None, include_root=""):
    cs, ds = scope(est, dashboards, cards, database)
    dbs = {est.cards[c].get("database_id") for c in cs if not est.cards[c].get("archived")}
    if len(dbs) > 1 and database is None:
        raise ConvertError(f"cards in scope use {len(dbs)} databases {sorted(dbs)}: one LookML model has one "
                           "connection, so convert one database at a time with --database")
    cv = Converter(est, bi_ir.slug(model), connection, include_root)
    # metrics and models first, so questions on them find them
    for cid in sorted(cs, key=lambda c: ({"metric": 0, "model": 1}.get(est.cards[c].get("type"), 2), c)):
        c = est.cards[cid]
        if c.get("type") == "metric" and not c.get("archived"):
            sts = stages(c["dataset_query"])
            try:
                base = cv.base_of(sts[0])
                xname = cv.explore_for(base)
                cv.metric(cid, cv.context(c, sts[0], xname))
                cv.card_class[cid] = ("mechanical", "saved metric: a measure")
            except Unsupported as e:
                cv.card_class[cid] = ("redesign", f"metric not converted: {e}")
                cv.count("metric", "redesign")
                cv.need(est.ident("card", cid), "metric", "redesign", f"metric not converted: {e}", None)
            continue
        if c.get("type") == "model" and not c.get("archived"):
            try:
                cv.view_for_card(cid)
                cv.explore_for(("card", cid))
                cv.card_class[cid] = ("assisted", "saved model: a view on its SQL")
                cv.count("model", "assisted")
            except Unsupported as e:
                cv.card_class[cid] = ("redesign", f"model not converted: {e}")
                cv.count("model", "redesign")
                cv.need(est.ident("card", cid), "model", "redesign", f"model not converted: {e}", None)
            continue
        cv.convert_card(cid)
    files = {}
    for did in ds:
        files.update(cv.convert_dashboard(did))
    on_dash = {dc.get("card_id") for d in ds for dc in est.dashboards[d].get("dashcards", [])}
    for cid in cs:
        el = cv.elements.get(cid)
        if el is None or cid in on_dash:
            continue
        c = est.cards[cid]
        title = c.get("name")
        e = {"name": bi_ir.slug(title), "title": title, "model": cv.model, "explore": el["explore"], "type": el["type"],
             "fields": el["fields"]}
        for k in ("pivots", "filters", "sorts", "limit"):
            if el.get(k):
                e[k] = el[k]
        e.update({"row": 0, "col": 0, "width": 24, "height": 12})
        doc = [{"dashboard": bi_ir.slug(f"{title} question"), "title": title, "layout": "newspaper",
                "preferred_viewer": "dashboards-next",
                "description": f"Migrated from Metabase question {title} (mb_to_lookml {VERSION}, experimental)",
                "elements": [e]}]
        cv.dash_docs.append({**doc[0], "source_id": est.ident("card", cid), "source_kind": "question"})
        files[f"{cv.root}dashboards/{bi_ir.slug(title + ' question')}.dashboard.lookml"] = yaml.safe_dump(
            doc, sort_keys=False, allow_unicode=True, width=1000)
        cv.need(est.ident("card", cid), "standalone_question", "assisted",
                "question on no dashboard: emitted as a one-tile LookML dashboard",
                "keep it, make it a Look through the Looker API (looker_content), or drop")
    cv.check_keys()
    for vname in sorted(cv.views):
        files[f"{cv.root}views/{vname}.view.lkml"] = cv.render_view(vname, cv.views[vname])
    files[f"models/{cv.model}.model.lkml"] = cv.render_model()
    cv.needs.sort(key=lambda n: (n["object"], n["construct"], n["reason"]))
    summary = {"converter": "mb_to_lookml", "version": VERSION, "model": cv.model, "metabase_version": est.version,
               "counts": {k: dict(sorted(v.items())) for k, v in sorted(cv.counts.items())},
               "views": len(cv.views), "explores": len(cv.explores),
               "dashboards": sum(1 for f in files if f.endswith(".dashboard.lookml")), "needs_human": len(cv.needs)}
    return cv, files, summary


# ---------------------------------------------------------------------------
# Audit outputs and IR
# ---------------------------------------------------------------------------
MODEL_COLUMNS = ["object_type", "object_uri", "dataset", "model", "field_name", "label", "construct",
                 "translation_class", "complexity", "reason", "source_file", "database", "engine"]
CONTENT_COLUMNS = ["object_type", "object_uri", "id", "title", "collection", "card_type", "display", "query_kind",
                   "database", "views", "last_used", "updated_at", "dashboard_ids", "tile_count", "translation_class",
                   "reason"]
COMPLEXITY = {"mechanical": "Low", "assisted": "Medium", "redesign": "High", "drop": "Low"}


def audit(est: Estate):
    """Convert each database separately (one model per connection), then catalog."""
    dbs = sorted({c.get("database_id") for c in est.cards.values() if not c.get("archived")} - {None})
    cvs = []
    for db in dbs:
        cv, _, _ = run(est, f"db_{db}", "warehouse", database=db)
        cvs.append((db, cv))
    card_class = {}
    for _, cv in cvs:
        card_class.update(cv.card_class)
    model_rows, content_rows, ir, deps, needs = [], [], [], [], []
    for db, cv in cvs:
        deps += cv.deps
        needs += cv.needs
        engine = est.engine(db)
        for tid, view in sorted(cv.table_view.items()):
            t = est.tables[tid]
            ident = est.ident("table", tid)
            cls = "redesign" if engine in NO_LOOKER else "mechanical"
            model_rows.append({"object_type": "table", "object_uri": ident, "dataset": f"{t.get('schema') or ''}.{t['name']}".strip("."),
                               "model": view, "construct": "table", "translation_class": cls, "complexity": COMPLEXITY[cls],
                               "reason": f"engine {engine} has no Looker connection" if cls == "redesign" else "",
                               "source_file": f"tables/{tid}.json", "database": (est.dbs.get(db) or {}).get("name"), "engine": engine})
            fields = []
            for f in sorted(t.get("fields", []), key=lambda x: x["id"]):
                construct = "primary_key" if f.get("semantic_type") == "type/PK" else \
                    ("foreign_key" if f.get("fk_target_field_id") else "column")
                fcls = "assisted" if (f.get("coercion_strategy") or f.get("nfc_path") or f.get("visibility_type") == "sensitive") else "mechanical"
                model_rows.append({"object_type": "field", "object_uri": bi_ir.field_id(TOOL, est.site, f"table_{tid}", f["name"]),
                                   "dataset": t["name"], "model": view, "field_name": f["name"],
                                   "label": f.get("display_name"), "construct": construct, "translation_class": fcls,
                                   "complexity": COMPLEXITY[fcls], "reason": "", "source_file": f"tables/{tid}.json",
                                   "database": (est.dbs.get(db) or {}).get("name"), "engine": engine})
                fields.append({"id": bi_ir.field_id(TOOL, est.site, f"table_{tid}", f["name"]), "name": f["name"],
                               "label": f.get("display_name"), "field_kind": "dimension", "source_type": f.get("base_type"),
                               "data_type": f.get("effective_type") or f.get("base_type"),
                               "key": {"type/PK": "primary", "type/FK": "foreign"}.get(f.get("semantic_type")),
                               "hidden": f.get("visibility_type") in ("details-only", "sensitive"), "class": fcls,
                               "target": f"looker:{cv.model}:view:{view}"})
            joins = [{"left": f["name"], "right": str(f["fk_target_field_id"]), "type": "left", "on": None,
                      "cardinality": "many_to_one", "kind": "relationship", "class": "mechanical",
                      "reason": "foreign key in Metabase's metadata"}
                     for f in sorted(t.get("fields", []), key=lambda x: x["id"]) if f.get("fk_target_field_id")]
            det = (est.dbs.get(db) or {}).get("details") or {}
            ir.append(bi_ir.obj("dataset", ident, t["name"], {"file": f"tables/{tid}.json", "fragment": fragment(
                {k: t.get(k) for k in ("id", "schema", "name", "db_id", "entity_type")})}, label=t.get("display_name"),
                connection={"class": engine, "project": det.get("project-id"), "database": (est.dbs.get(db) or {}).get("name"),
                            "schema": t.get("schema")},
                relations=[{"name": t["name"], "table": f"{t.get('schema') or ''}.{t['name']}".strip(".")}],
                fields=fields, joins=joins, materialisation="live", **{"class": "redesign" if engine in NO_LOOKER else "mechanical"}))
        for x, e in sorted(cv.explores.items()):
            ref = e["base_ref"]
            base_id = est.ident("table", ref[1]) if ref[0] == "table" and ref[1] is not None else \
                (est.ident("card", ref[1], "dataset", "sql") if ref[0] == "card" else None)
            ir.append(bi_ir.obj("model", est.ident("database", db, "model", x), x, {"fragment": x}, label=e["label"],
                                base_dataset=base_id, joins=[{"left": e["base"], "right": jn, "type": j["type"].split("_")[0],
                                                              "on": j["sql_on"], "cardinality": j["relationship"],
                                                              "kind": "relationship", "class": j["class"],
                                                              "reason": j["reason"]} for jn, j in sorted(e["joins"].items())]))
    on_dashboards = {}
    for did, d in est.dashboards.items():
        for dc in d.get("dashcards", []):
            if dc.get("card_id"):
                on_dashboards.setdefault(dc["card_id"], set()).add(did)
    for cid, c in sorted(est.cards.items()):
        m = est.meta[("card", cid)]
        cls, reason = card_class.get(cid, ("drop", "archived") if c.get("archived") else ("assisted", "not converted"))
        u = (est.usage.get("cards") or {}).get(str(cid), {})
        content_rows.append({"object_type": c.get("type") or "question", "object_uri": est.ident("card", cid), "id": cid,
                             "title": c.get("name"), "collection": m.get("collection") or "", "card_type": c.get("type"),
                             "display": c.get("display"), "query_kind": m.get("query_kind"),
                             "database": (est.dbs.get(c.get("database_id")) or {}).get("name"),
                             "views": u.get("view_count", ""), "last_used": u.get("last_used_at") or "",
                             "updated_at": c.get("updated_at") or "",
                             "dashboard_ids": ";".join(str(x) for x in sorted(on_dashboards.get(cid, []))),
                             "translation_class": cls, "reason": reason})
        q = c.get("dataset_query") or {}
        ir.append(bi_ir.obj("report", est.ident("card", cid), c.get("name") or str(cid),
                            {"file": m["path"], "fragment": fragment(q), "sha256": m.get("sha256"), "updated_at": c.get("updated_at")},
                            query={"kind": m.get("query_kind"), "stages": len(stages(q))},
                            visualisation={"display": c.get("display")},
                            datasets=sorted({est.ident("table", t) for t in _tables_of(q)}), **{"class": cls, "reason": reason}))
        if c.get("type") in ("model",) or m.get("query_kind") == "native":
            ir.append(bi_ir.obj("dataset", est.ident("card", cid, "dataset", "sql"), c.get("name") or str(cid),
                                {"file": m["path"], "fragment": fragment(q)}, materialisation="live",
                                fields=[{"id": bi_ir.field_id(TOOL, est.site, f"card_{cid}", col.get("name")),
                                         "name": col.get("name"), "label": col.get("display_name"), "field_kind": "dimension",
                                         "source_type": col.get("base_type"), "data_type": col.get("effective_type") or col.get("base_type")}
                                        for col in c.get("result_metadata") or [] if col.get("name")],
                                **{"class": "assisted", "reason": "a view on the card's SQL"}))
    for did, d in sorted(est.dashboards.items()):
        m = est.meta[("dashboard", did)]
        u = (est.usage.get("dashboards") or {}).get(str(did), {})
        tiles = [dc for dc in d.get("dashcards", []) if dc.get("card_id")]
        content_rows.append({"object_type": "dashboard", "object_uri": est.ident("dashboard", did), "id": did,
                             "title": d.get("name"), "collection": m.get("collection") or "", "views": u.get("view_count", ""),
                             "last_used": u.get("last_viewed_at") or "", "updated_at": d.get("updated_at") or "",
                             "tile_count": len(tiles), "translation_class": "assisted" if d.get("tabs") else "mechanical",
                             "reason": f"{len(d['tabs'])} tabs" if d.get("tabs") else ""})
        ir.append(bi_ir.obj("dashboard", est.ident("dashboard", did), d.get("name"),
                            {"file": m["path"], "fragment": fragment({k: d.get(k) for k in ("name", "tabs", "parameters", "width")})},
                            size={"width": 24, "tabs": len(d.get("tabs") or [])},
                            tiles=[{"id": est.ident("dashboard", did, "dashcard", dc["id"]), "report": est.ident("card", dc["card_id"]),
                                    "position": {"row": dc["row"], "col": dc["col"], "width": dc["size_x"], "height": dc["size_y"]},
                                    "class": card_class.get(dc["card_id"], ("assisted", ""))[0]} for dc in sorted(tiles, key=lambda x: x["id"])],
                            controls=[{"id": p["id"], "name": p.get("name"), "type": p.get("type")} for p in d.get("parameters") or []]))
    for cid_, c in sorted(est.collections.items()):
        loc = [x for x in (c.get("location") or "/").split("/") if x]
        ir.append(bi_ir.obj("folder", est.ident("collection", cid_), c.get("name") or str(cid_), {"fragment": c.get("name") or ""},
                            parent=est.ident("collection", loc[-1]) if loc else None))
    return model_rows, content_rows, ir, deps, needs


def _tables_of(q):
    out = set()
    for st in stages(q):
        for s in [st] + [js for j in st.get("joins", []) for js in j.get("stages", [])]:
            if isinstance(s.get("source-table"), int):
                out.add(s["source-table"])
    return out


def write_csv(path: Path, rows, columns):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})
    path.write_text(buf.getvalue())


def write_jsonl(path: Path, rows):
    uniq = sorted({json.dumps(r, sort_keys=True) for r in rows})
    path.write_text("".join(u + "\n" for u in uniq))


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------
METABASE_ISMS = [
    (re.compile(r"\{\{\s*[^}%]+\}\}"), "Metabase template tag {{...}}"),
    (re.compile(r"\[\["), "Metabase optional clause [[...]]"),
    (re.compile(r"snippet:", re.I), "Metabase snippet"),
    (re.compile(r"card__\d+"), "Metabase card reference"),
    (re.compile(r'"lib/uuid"|\["field",'), "MBQL fragment"),
]


def lint(lookml_dir: Path):
    found = sorted(list(Path(lookml_dir).rglob("*.lkml")) + list(Path(lookml_dir).rglob("*.lookml")))
    if not found:
        return [f"{lookml_dir}: no LookML files (nothing was converted, or the wrong folder)"]
    problems = []
    for p in found:
        text = p.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            for rx, what in METABASE_ISMS:
                if rx.search(line):
                    problems.append(f"{p.relative_to(lookml_dir)}:{i}: {what}: {line.strip()[:160]}")
        if p.name.endswith(".view.lkml"):
            problems += [f"{p.relative_to(lookml_dir)}: field {n} is defined twice (Looker: 'Redefinition of field')"
                         for n in duplicate_fields(text)]
    return problems


def duplicate_fields(view_text: str) -> list:
    """Field names a view defines more than once, counting the fields each dimension_group generates."""
    names = []
    for kind, n in re.findall(r"^  (dimension|measure|parameter|filter|dimension_group): (\w+)", view_text, re.M):
        if kind == "dimension_group":
            m = re.search(r"dimension_group: " + n + r" \{[^}]*?timeframes: \[([^\]]*)\]", view_text)
            names += [f"{n}_{t.strip()}" for t in (m.group(1).split(",") if m else [])]
        else:
            names.append(n)
    return sorted({x for x in names if names.count(x) > 1})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def ids(s):
    return {int(x) for x in (s or "").split(",") if x.strip()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "convert"):
        s = sub.add_parser(name)
        s.add_argument("--snapshot", required=True)
        s.add_argument("--out", required=True)
        if name == "convert":
            s.add_argument("--model", default="metabase_migration")
            s.add_argument("--connection", default="warehouse")
            s.add_argument("--database", type=int)
            s.add_argument("--dashboards", default="")
            s.add_argument("--cards", default="")
            s.add_argument("--include-root", default="",
                           help="folder in the target LookML repo for the views and dashboards (default: repo root)")
    lt = sub.add_parser("lint")
    lt.add_argument("lookml_dir")
    a = ap.parse_args(argv)

    if a.cmd == "lint":
        probs = lint(Path(a.lookml_dir))
        for p in probs:
            print("FAIL", p)
        print(f"{'FAIL' if probs else 'PASS'}: {len(probs)} problem(s) in emitted LookML")
        return 1 if probs else 0
    try:
        est = Estate(Path(a.snapshot))
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        if a.cmd == "audit":
            model_rows, content_rows, ir, deps, needs = audit(est)
            write_csv(out / "bi_model_catalog.csv", model_rows, MODEL_COLUMNS)
            write_csv(out / "bi_content_catalog.csv", content_rows, CONTENT_COLUMNS)
            write_jsonl(out / "dependencies.jsonl", deps)
            bi_ir.write(out / "ir", ir)
            (out / "needs_human.json").write_text(json.dumps(sorted(needs, key=lambda n: (n["object"], n["construct"], n["reason"])),
                                                             indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            by = {}
            for r in model_rows + content_rows:
                if r.get("translation_class"):
                    by[r["translation_class"]] = by.get(r["translation_class"], 0) + 1
            print(f"{len(est.cards)} cards, {len(est.dashboards)} dashboards, {len(est.tables)} tables; "
                  f"classes {dict(sorted(by.items()))} -> {out}")
            return 0
        cv, files, summary = run(est, a.model, a.connection, ids(a.dashboards), ids(a.cards), a.database, a.include_root)
    except (ConvertError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / "needs_human.json").write_text(json.dumps(cv.needs, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "conversion_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    write_jsonl(out / "dependencies.jsonl", cv.deps)
    print(f"{summary['views']} views, {summary['explores']} explores, {summary['dashboards']} dashboards, "
          f"{summary['needs_human']} needs_human -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

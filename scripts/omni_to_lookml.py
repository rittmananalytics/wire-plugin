#!/usr/bin/env python3
"""
Omni to LookML converter (bi_migration, pair omni_to_looker). EXPERIMENTAL.

Reads a snapshot written by omni_export.py (the Omni model's YAML files, the field list Omni reports
for each view, and the dashboard documents) and runs one of three commands:

    audit     Catalogs with a translation class per construct (views, fields, topics, relationships,
              documents, tiles, controls), the tool-neutral IR (wire/scripts/bi_ir.py) and the
              dependency graph.
    convert   LookML: one view per Omni view (schema views keep their table, query views become
              derived tables), dimension groups for time fields, measures, explores from topics with
              joins from the relationships, and one LookML dashboard per Omni dashboard document
              (Omni's 24-column grid maps one to one; controls become dashboard filters with listen).
              Writes needs_human.json and parity_map.json alongside.
    lint      Fails if Omni syntax is left in emitted LookML (timeframe brackets, Mustache, Omni
              keys), if a view defines a field name twice (counting the fields a dimension group
              generates), if a dimension references a measure, or the folder has no LookML.

Deterministic and no AI call: the same snapshot gives the same files. The agent decides each
needs_human item, explore design and consolidation; it never hand-writes LookML this script emits.

Omni facts relied on: a bare identifier in a field's sql is a column of the view's table; ${field}
and ${view.field} are field references; ${field[month]} selects a timeframe. Translation rules are in
wire/bi_pairs/omni_to_looker/translation_guide.md.

Usage:
    python3 wire/scripts/omni_to_lookml.py audit --snapshot <dir> --out <dir>
    python3 wire/scripts/omni_to_lookml.py convert --snapshot <dir> --out <dir> [--model NAME]
        [--connection NAME] [--topics a,b] [--documents id,id] [--include-root DIR]
    python3 wire/scripts/omni_to_lookml.py lint <lookml dir>
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
import bi_ir  # noqa: E402

VERSION = "0.1.0"
TOOL = "omni"

# Omni timeframe -> LookML timeframe (None: no LookML equivalent)
TIMEFRAME = {"raw": "raw", "time": "time", "date": "date", "week": "week", "month": "month", "quarter": "quarter",
             "year": "year", "hour": "hour", "minute": "minute", "second": "second", "millisecond": "millisecond",
             "day_of_week_name": "day_of_week", "day_of_week_num": "day_of_week_index", "day_of_month": "day_of_month",
             "day_of_year": "day_of_year", "hour_of_day": "hour_of_day", "month_name": "month_name",
             "month_num": "month_num", "quarter_of_year": "quarter_of_year", "week_of_year": "week_of_year",
             "fiscal_quarter": "fiscal_quarter", "fiscal_year": "fiscal_year", "fiscal_month_num": "fiscal_month_num",
             "fiscal_quarter_of_year": "fiscal_quarter_of_year", "day_of_quarter": None}
TF_ORDER = ["raw", "time", "date", "week", "month", "quarter", "year", "hour", "minute", "second", "millisecond",
            "day_of_week", "day_of_week_index", "day_of_month", "day_of_year", "hour_of_day", "month_name", "month_num",
            "quarter_of_year", "week_of_year", "fiscal_month_num", "fiscal_quarter", "fiscal_quarter_of_year",
            "fiscal_year"]
TF_DEFAULT = ["raw", "time", "date", "week", "month", "quarter", "year"]

AGG = {"sum": "sum", "count": "count", "count_distinct": "count_distinct", "average": "average", "min": "min",
       "max": "max", "median": "median", "list": "list", "percentile": "percentile",
       "sum_distinct_on": "sum_distinct", "average_distinct_on": "average_distinct",
       "median_distinct_on": "median_distinct", "percentile_distinct_on": "percentile_distinct"}
JOIN_TYPE = {"always_left": "left_outer", "inner": "inner", "full_outer": "full_outer", "cross": "cross"}
REL = {"many_to_one": "many_to_one", "one_to_one": "one_to_one", "one_to_many": "one_to_many",
       "many_to_many": "many_to_many"}
REVERSE_REL = {"many_to_one": "one_to_many", "one_to_many": "many_to_one", "one_to_one": "one_to_one",
               "many_to_many": "many_to_many"}

# Omni format -> LookML value_format_name, or ("value_format", string)
FORMAT_NAME = {"currency": "usd", "currency_0": "usd_0", "currency_2": "usd", "usdcurrency": "usd",
               "usdcurrency_0": "usd_0", "usdcurrency_2": "usd", "gbpcurrency": "gbp", "gbpcurrency_0": "gbp_0",
               "gbpcurrency_2": "gbp", "eurcurrency": "eur", "eurcurrency_0": "eur_0", "eurcurrency_2": "eur",
               "id": "id", "percent": "percent_0"}
for _n in range(5):
    FORMAT_NAME[f"number_{_n}"] = f"decimal_{_n}"
    FORMAT_NAME[f"percent_{_n}"] = f"percent_{_n}"
FORMAT_STRING = {"number": "#,##0.##", "thousands_0": '#,##0,"K"', "thousands_1": '#,##0.0,"K"',
                 "thousands_2": '#,##0.00,"K"', "millions_0": '#,##0,,"M"', "millions_1": '#,##0.0,,"M"',
                 "millions_2": '#,##0.00,,"M"', "billions_0": '#,##0,,,"B"', "billions_1": '#,##0.0,,,"B"',
                 "billions_2": '#,##0.00,,,"B"'}
NUMERIC_FORMATS = set(FORMAT_NAME) | set(FORMAT_STRING) | {"big", "bigcurrency", "accounting"}

# Omni chartType -> LookML element type, extra settings
CHART = {"kpi": ("single_value", {}), "table": ("looker_grid", {}), "pie": ("looker_pie", {}),
         "area": ("looker_area", {}), "areaStacked": ("looker_area", {"stacking": "normal"}),
         "line": ("looker_line", {}), "lineColor": ("looker_line", {}), "column": ("looker_column", {}),
         "columnGrouped": ("looker_column", {}), "columnStacked": ("looker_column", {"stacking": "normal"}),
         "bar": ("looker_bar", {}), "barGrouped": ("looker_bar", {}), "barStacked": ("looker_bar", {"stacking": "normal"}),
         "point": ("looker_scatter", {}), "scatter": ("looker_scatter", {})}
CHART_ASSISTED = {"barLine": "looker_column", "columnLine": "looker_column", "map": "looker_map",
                  "heatmap": "looker_grid", "funnel": "looker_funnel", "sankey": "looker_grid",
                  "boxplot": "looker_boxplot", "waterfall": "looker_waterfall"}
ROW_SCALE = 6           # Omni grid height units to Looker newspaper rows

# SQL words that are never column names in a field expression
KEYWORDS = {w.upper() for w in """
and or not null is in like ilike between case when then else end as true false distinct interval cast safe_cast
over partition by order asc desc rows range unbounded preceding following current row from with escape ignore
respect nulls limit offset ordinal struct array unnest exists any all some except replace at zone collate
day week month quarter year hour minute second millisecond microsecond dayofweek dayofyear isoweek isoyear
date datetime timestamp time int64 float64 numeric bignumeric string bool boolean bytes integer int float double
varchar char decimal number text varint bigint smallint tinyint real json geography variant object
monday tuesday wednesday thursday friday saturday sunday local utc
""".split()}
REF = re.compile(r"\$\{\s*([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?(?:\[([a-z_0-9]+)\])?\s*\}")
MUSTACHE = re.compile(r"\{\{.*?\}\}", re.S)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PLAIN_COLUMN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SELECT_STAR = re.compile(r"\s*select\s+\*\s+from\s+(`[^`]+`|[A-Za-z0-9_.\-\"]+)\s*;?\s*", re.I)

# Keys handled; anything else on these objects is listed, never silently dropped
VIEW_KEYS = {"schema", "table_name", "catalog", "sql", "query", "label", "description", "dimensions", "measures",
             "filters", "extends", "template", "schema_label", "dbt", "primary_key", "hidden", "tags",
             "custom_compound_primary_key_sql", "ignored", "aliases", "display_order", "default_drill_fields"}
DIM_KEYS = {"sql", "label", "description", "group_label", "hidden", "primary_key", "format", "timeframes",
            "convert_tz", "bin_boundaries", "groups", "else", "all_values", "suggestion_list",
            "suggest_from_field", "order_by_field", "drill_fields", "links", "markdown", "parent_field",
            "nested_on_field", "duration", "view_label", "type", "aliases", "display_order", "synonyms",
            "ai_context", "sample_values", "tags", "required_access_grants", "dimension_group", "colors"}
MEASURE_KEYS = {"sql", "label", "description", "group_label", "hidden", "format", "aggregate_type", "filters",
                "custom_primary_key_sql", "percentile", "drill_fields", "links", "markdown", "view_label",
                "aliases", "display_order", "synonyms", "ai_context", "tags", "required_access_grants", "colors"}
TOPIC_KEYS = {"base_view", "label", "description", "group_label", "hidden", "joins", "relationships", "fields",
              "always_where_sql", "always_where_filters", "default_filters", "access_filters",
              "required_access_grants", "ai_context", "ai_fields", "sample_queries", "cache_policy", "views",
              "display_order", "warehouse_override", "ai_chat_topics", "extends", "tags", "aliases"}
AI_KEYS = {"ai_context", "ai_fields", "sample_queries", "ai_chat_topics", "synonyms", "sample_values"}
MODEL_KEYS = {"week_start_day", "fiscal_month_offset", "access_grants", "ignored_schemas", "included_schemas",
              "dynamic_schemas", "query_timezone", "cache_policies", "default_cache_policy", "ai_context",
              "topics", "views", "extends", "warehouse_override", "default_topic_access_filters"}


class ConvertError(Exception):
    pass


class Unsupported(Exception):
    pass


def lk_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def lk_name(name: str) -> str:
    n = re.sub(r"[^a-z0-9_]+", "_", str(name).lower()).strip("_")
    return n if n and not n[0].isdigit() else f"f_{n}"


def view_name_of(path: str) -> str | None:
    """Omni names a view by its file path: analytics/orders.view is analytics__orders."""
    for suffix in (".query.view", ".view"):
        if path.endswith(suffix):
            return path[: -len(suffix)].replace("/", "__")
    return None


def topic_name_of(path: str) -> str:
    return path[: -len(".topic")].rsplit("/", 1)[-1]


def fragment(obj, n=2000):
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str) if not isinstance(obj, str) else obj
    return s[:n]


def esc_filter(v) -> str:
    """A value inside a Looker filter expression: commas and carets are escaped with a caret."""
    s = str(v)
    return s.replace("^", "^^").replace(",", "^,").replace('"', '^"')


def tidy_num(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f == int(f) else repr(f)


# ---------------------------------------------------------------------------
# The snapshot
# ---------------------------------------------------------------------------

class Estate:
    def __init__(self, snap: Path):
        self.snap = snap
        inv_p = snap / "inventory.json"
        if not inv_p.exists():
            raise ConvertError(f"{snap}: no inventory.json (not an omni_export.py snapshot)")
        self.inv = json.loads(inv_p.read_text())
        self.instance = self.inv.get("instance") or "omni"
        self.model_meta = self.inv.get("model") or {}
        self.dialect = (self.model_meta.get("dialect") or "bigquery").lower()
        self.model_file, self.relationships = {}, []
        self.views, self.view_path, self.topics, self.topic_path = {}, {}, {}, {}
        for rel in sorted(self.inv.get("model_files", {})):
            p = snap / "model" / rel
            if not p.exists():
                raise ConvertError(f"{p}: listed in inventory.json but missing")
            data = yaml.safe_load(p.read_text()) or {}
            if rel == "model":
                self.model_file = data
            elif rel == "relationships":
                self.relationships = list(data or [])
            elif rel.endswith(".topic"):
                name = topic_name_of(rel)
                self.topics[name], self.topic_path[name] = data, rel
            elif view_name_of(rel):
                name = view_name_of(rel)
                self.views[name], self.view_path[name] = data, rel
        reported = json.loads((snap / "views.json").read_text()) if (snap / "views.json").exists() else {"views": []}
        # Omni's own field list: a field reported with [timeframe] variants is a time field
        self.reported_tf = {}
        for v in reported.get("views", []):
            for f in v.get("fields", []):
                m = re.fullmatch(r"(\w+)\[(\w+)\]", f.get("name", ""))
                if m:
                    self.reported_tf.setdefault((v["name"], m.group(1)), []).append(m.group(2))
        cols = json.loads((snap / "columns.json").read_text()) if (snap / "columns.json").exists() else {}
        self.columns = {k.lower(): {c.lower(): t for c, t in v.items()} for k, v in cols.items()}
        self.documents = {}
        for ident, meta in sorted((self.inv.get("documents") or {}).items()):
            p = snap / meta.get("file", f"documents/{ident}.json")
            if p.exists():
                self.documents[ident] = json.loads(p.read_text())

    def ident(self, *p):
        return bi_ir.identity(TOOL, self.instance, *p)

    def column_type(self, view: dict, col: str) -> str | None:
        """The column's warehouse type from columns.json, for a schema view or a SELECT * query view."""
        key = None
        if view.get("table_name"):
            key = f"{view.get('schema') or ''}.{view['table_name']}".lower()
        elif isinstance(view.get("sql"), str) and SELECT_STAR.fullmatch(view["sql"]):
            parts = SELECT_STAR.fullmatch(view["sql"]).group(1).strip("`\"").split(".")
            key = ".".join(parts[-2:]).lower() if len(parts) >= 2 else None
        return (self.columns.get(key) or {}).get(col.lower()) if key else None


# ---------------------------------------------------------------------------
# SQL translation
# ---------------------------------------------------------------------------

def scan(sql: str, dialect: str):
    """Yield (kind, text) tokens: str, qident, ref, word, other. Strings and comments are kept whole."""
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "$" and sql.startswith("${", i):
            j = sql.find("}", i)
            j = n - 1 if j < 0 else j
            yield "ref", sql[i:j + 1]
            i = j + 1
        elif c == "'" or (c == '"' and dialect == "bigquery"):
            j = i + 1
            while j < n and sql[j] != c:
                j += 2 if sql[j] == "\\" else 1
            yield "str", sql[i:j + 1]
            i = j + 1
        elif c == "`" or (c == '"' and dialect != "bigquery"):
            j = sql.find(c, i + 1)
            j = n - 1 if j < 0 else j
            yield "qident", sql[i:j + 1]
            i = j + 1
        elif c == "-" and sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            yield "other", sql[i:j]
            i = j
        elif c.isalpha() or c == "_":
            m = IDENT.match(sql, i)
            yield "word", m.group(0)
            i = m.end()
        elif c.isdigit():
            m = re.compile(r"[0-9.]+(?:[eE][-+]?[0-9]+)?").match(sql, i)
            yield "other", m.group(0)
            i = m.end()
        else:
            yield "other", c
            i += 1


class Sql:
    """Translates one Omni sql expression to LookML for a field on `view`."""

    def __init__(self, conv, view: str, kind: str = "measure"):
        self.conv, self.view, self.kind = conv, view, kind
        self.cross_views = set()
        self.complex_columns = False
        self.measure_columns = set()   # measure names a dimension read as columns

    def ref(self, m) -> str:
        a, b, tf = m.group(1), m.group(2), m.group(3)
        view, field = (a, b) if b else (self.view, a)
        if self.kind == "dimension" and not tf:
            real = self.conv.real(view)
            dims = self.conv.resolved(real, "dimensions")
            if field not in dims and field in self.conv.resolved(real, "measures"):
                # Omni reads ${x} in a dimension as the column x when x is only a measure; LookML reads the measure
                if real != self.conv.real(self.view):
                    raise Unsupported(f"a dimension reading {view}.{field}, a measure of another view")
                self.measure_columns.add(field)
                return "${TABLE}." + field
        if view != self.view:
            self.cross_views.add(view)
        lv = self.conv.lk_view(view)
        lf = self.conv.field_ref(view, field, tf, context="sql")
        return "${" + (f"{lv}." if b else "") + lf + "}"

    def translate(self, sql) -> str:
        sql = str(sql)
        if MUSTACHE.search(sql):
            raise Unsupported("Mustache templating ({{ }}) in sql: a Liquid parameter or templated filter by hand")
        tokens = list(scan(sql, self.conv.est.dialect))
        words = [t for k, t in tokens if k == "word"]
        if any(w.upper() == "SELECT" for w in words):
            # a subquery: bare names may belong to the inner query, so nothing is qualified
            self.complex_columns = True
            return REF.sub(self.ref, sql)
        out, prev_sig = [], ""
        for idx, (kind, text) in enumerate(tokens):
            if kind == "ref":
                out.append(REF.sub(self.ref, text))
            elif kind == "word":
                nxt = next((t for k, t in tokens[idx + 1:] if k != "other" or t.strip()), "")
                is_fn = nxt.startswith("(")
                if prev_sig == "." or is_fn or text.upper() in KEYWORDS or prev_sig.upper() == "AS":
                    out.append(text)
                else:
                    out.append("${TABLE}." + text)
            elif kind == "qident" and prev_sig != "." and "." not in text[1:-1] and \
                    not next((t for k, t in tokens[idx + 1:] if k != "other" or t.strip()), "").startswith("."):
                out.append("${TABLE}." + text)
            else:
                out.append(text)
            if kind != "other" or text.strip():
                prev_sig = text
        return "".join(out)


# ---------------------------------------------------------------------------
# Filter expressions
# ---------------------------------------------------------------------------

def date_expr(left: str | None, right: str | None):
    """Omni 'N complete units ago' + 'M units' -> Looker. None when not mechanical."""
    lm = re.fullmatch(r"\s*(\d+)\s+(complete\s+)?(day|week|month|quarter|year)s?\s+ago\s*", left or "")
    rm = re.fullmatch(r"\s*(\d+)\s+(day|week|month|quarter|year)s?\s*", right or "")
    if not lm or not rm:
        return None, False
    n, m, unit = int(lm.group(1)), int(rm.group(1)), rm.group(2)
    if lm.group(3) != unit:
        u1 = lm.group(3)
        return f"{n} {u1}{'s' if n != 1 else ''} ago for {m} {unit}{'s' if m != 1 else ''}", False
    exact = bool(lm.group(2)) or unit == "day"
    if m == n + 1:
        return f"{m} {unit}{'s' if m != 1 else ''}", exact
    return f"{n} {unit}{'s' if n != 1 else ''} ago for {m} {unit}{'s' if m != 1 else ''}", exact


def query_filter(f: dict):
    """An Omni document filter object -> (Looker expression, class). class None: not translatable."""
    t, kind, vals = f.get("type"), f.get("kind"), f.get("values") or []
    neg = bool(f.get("is_negative"))
    if t == "composite":
        parts = [query_filter(x) for x in f.get("filters") or []]
        if f.get("conjunction") == "AND" and parts and all(p[0] and p[0].startswith("-") for p in parts):
            return ",".join(p[0] for p in parts), "mechanical"
        return None, None
    if t == "null":
        return ("-NULL" if neg else "NULL"), "mechanical"
    if t == "boolean":
        return ("No" if neg else "Yes"), "mechanical"
    if t == "string":
        if kind == "EQUALS":
            if not vals:
                return "", "mechanical"
            return ",".join(("-" if neg else "") + esc_filter(v) for v in vals), "mechanical"
        if kind == "IS_EMPTY":
            return ("-EMPTY" if neg else "EMPTY"), "mechanical"
        if kind in ("CONTAINS", "STARTS_WITH", "ENDS_WITH") and vals:
            pat = {"CONTAINS": "%{}%", "STARTS_WITH": "{}%", "ENDS_WITH": "%{}"}[kind]
            return ",".join(("-" if neg else "") + pat.format(esc_filter(v)) for v in vals), "mechanical"
        return None, None
    if t == "number":
        if neg:
            return None, None
        inc = "=" if f.get("is_inclusive") else ""
        if kind == "EQUALS" and vals:
            return ",".join(tidy_num(v) for v in vals), "mechanical"
        if kind == "GREATER_THAN" and len(vals) == 1:
            return f">{inc}{tidy_num(vals[0])}", "mechanical"
        if kind == "LESS_THAN" and len(vals) == 1:
            return f"<{inc}{tidy_num(vals[0])}", "mechanical"
        if kind == "BETWEEN" and len(vals) == 2:
            lo, hi = tidy_num(vals[0]), tidy_num(vals[1])
            return (f"[{lo},{hi}]" if f.get("is_inclusive", True) else f"({lo},{hi})"), "mechanical"
        return None, None
    if t in ("date", "timestamp"):
        if neg:
            return None, None
        if kind == "TIME_FOR_INTERVAL_DURATION":
            e, exact = date_expr(f.get("left_side"), f.get("right_side"))
            return (e, "mechanical" if exact else "assisted") if e else (None, None)
        if kind == "BETWEEN" and len(vals) == 2 and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(x)) for x in vals):
            return f"{vals[0]} to {vals[1]}", "assisted"
        if kind in ("BEFORE", "ON_OR_AFTER") and len(vals) == 1:
            v = str(vals[0])
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?|today|yesterday|tomorrow", v):
                return ("before " if kind == "BEFORE" else "after ") + v, "mechanical"
        return None, None
    return None, None


def yaml_filter(cond):
    """An Omni YAML filter condition ({is: x}, {greater_than: 5}, ...) -> Looker expression or None."""
    if not isinstance(cond, dict) or len(cond) != 1:
        return None
    (op, v), = cond.items()
    vals = v if isinstance(v, list) else [v]
    if op in ("is", "is_not"):
        neg = "-" if op == "is_not" else ""
        if v is None:
            return "-NULL" if neg else "NULL"
        if isinstance(v, bool):
            return ("No" if v else "Yes") if neg else ("Yes" if v else "No")
        return ",".join(neg + (tidy_num(x) if isinstance(x, (int, float)) else esc_filter(x)) for x in vals)
    if op == "not" and v is None:
        return "-NULL"
    ops = {"greater_than": ">", "greater_than_or_equal_to": ">=", "less_than": "<", "less_than_or_equal_to": "<="}
    if op in ops and not isinstance(v, (list, dict)):
        return f"{ops[op]}{tidy_num(v)}"
    if op == "between" and isinstance(v, list) and len(v) == 2:
        return f"[{tidy_num(v[0])},{tidy_num(v[1])}]"
    pats = {"contains": "%{}%", "starts_with": "{}%", "ends_with": "%{}", "does_not_contain": "-%{}%",
            "does_not_start_with": "-{}%", "does_not_end_with": "-%{}"}
    if op in pats and not isinstance(v, dict):
        return ",".join(pats[op].format(esc_filter(x)) for x in vals)
    if op == "time_for_duration" and isinstance(v, list) and len(v) == 2:
        e, _ = date_expr(v[0], v[1])
        return e
    return None


# ---------------------------------------------------------------------------
# The converter
# ---------------------------------------------------------------------------

class Converter:
    def __init__(self, est: Estate, model: str, connection: str, include_root: str = ""):
        self.est, self.model, self.connection = est, model, connection
        self.root = f"{include_root.strip('/')}/" if include_root.strip("/") else ""
        self.needs, self.deps, self.counts = [], [], {}
        self.obj_class = {}          # identity -> (class, reason): the worst class recorded against it
        self.views = {}              # LookML view name -> rendered parts
        self.explores = {}           # explore name -> dict
        self.groups = {}             # (omni view, omni field) -> {"timeframes": [...], "datatype": ...}
        self.field_names = {}        # (omni view, omni field) -> LookML field name
        self.view_names = {}         # omni view -> LookML view name
        self.view_fields = {}        # omni view -> set of omni field names emitted
        self.dash_docs, self.parity = [], []
        self.custom_aggregates = []  # (view, field identity): measures aggregating columns in their own SQL
        self.reported = set()
        self._prepare()

    # -- bookkeeping ----------------------------------------------------------
    def count(self, construct, cls):
        self.counts.setdefault(construct, {}).setdefault(cls, 0)
        self.counts[construct][cls] += 1

    def need(self, obj, construct, cls, reason, proposal=None):
        key = (obj, construct, reason)
        if key in self.reported:
            return
        self.reported.add(key)
        self.needs.append({"object": obj, "construct": construct, "class": cls, "reason": reason, "proposal": proposal})
        self.mark(obj, cls, reason)

    def mark(self, obj, cls, reason):
        rank = {"mechanical": 0, "drop": 1, "assisted": 2, "redesign": 3}
        old = self.obj_class.get(obj)
        if old is None or rank[cls] > rank[old[0]]:
            self.obj_class[obj] = (cls, reason)

    def vid(self, view):
        return self.est.ident("view", view)

    def fid(self, view, field):
        return bi_ir.field_id(TOOL, self.est.instance, view, field)

    # -- names ----------------------------------------------------------------
    def _prepare(self):
        """Names and time fields for every view, before any SQL is translated."""
        self.aliases = {}            # join_to_view_as alias -> the view behind it
        for r in list(self.est.relationships) + [r for t in self.est.topics.values() for r in t.get("relationships") or []]:
            if isinstance(r, dict) and r.get("join_to_view_as") and r.get("join_to_view") in self.est.views:
                self.aliases.setdefault(r["join_to_view_as"], r["join_to_view"])
        taken_views = set()
        for v in sorted(self.est.views):
            n = lk_name(v)
            while n in taken_views:
                n += "_view"
            taken_views.add(n)
            self.view_names[v] = n
        for v, body in sorted(self.est.views.items()):
            dims = self.resolved(v, "dimensions")
            for f, d in dims.items():
                d = d or {}
                tfs = d.get("timeframes")
                reported = self.est.reported_tf.get((v, f))
                ctype = (self.est.column_type(self.resolved_view(v), d.get("sql") if isinstance(d.get("sql"), str)
                                              and PLAIN_COLUMN.fullmatch(d.get("sql") or "") else f) or "").upper()
                is_time = bool(tfs) or bool(reported) or ctype in ("DATE", "DATETIME", "TIMESTAMP", "TIMESTAMP_NTZ",
                                                                     "TIMESTAMP_TZ", "TIMESTAMP_LTZ")
                if not is_time or d.get("duration"):
                    continue
                omni_tfs = list(tfs) if tfs else (sorted(set(reported or [])) or ["raw", "date", "week", "month",
                                                                                  "quarter", "year"])
                self.groups[(v, f)] = {"omni": omni_tfs, "datatype": "date" if ctype == "DATE" else
                                       ("datetime" if ctype == "DATETIME" else None)}
            taken = set()
            for f in sorted(dims):
                n = lk_name(f)
                while n in taken:
                    n += "_dim"
                taken.add(n)
                self.field_names[(v, f)] = n
            gen = set()
            for (gv, gf), g in self.groups.items():
                if gv == v:
                    gen |= {f"{self.field_names[(v, gf)]}_{t}" for t in TF_ORDER}
            for f in sorted(self.resolved(v, "measures")) + sorted((body.get("filters") or {})):
                n = lk_name(f)
                while n in taken or n in gen:
                    n += "_measure"
                taken.add(n)
                self.field_names[(v, f)] = n

    def resolved_view(self, v, seen=None):
        """A view with its extends chain merged in (fields of the extending view win)."""
        seen = seen or set()
        body = dict(self.est.views.get(v) or {})
        for parent in body.get("extends") or []:
            if parent in seen or parent not in self.est.views:
                continue
            pb = self.resolved_view(parent, seen | {v})
            for k, val in pb.items():
                if k in ("dimensions", "measures", "filters"):
                    merged = dict(val or {})
                    merged.update(body.get(k) or {})
                    body[k] = merged
                elif k not in body and k not in ("template", "extends"):
                    body[k] = val
        return body

    def resolved(self, v, key):
        return dict(self.resolved_view(v).get(key) or {})

    def lk_view(self, v):
        if v not in self.view_names:
            self.view_names[v] = lk_name(v)
        return self.view_names[v]

    def real(self, v):
        return v if v in self.est.views else self.aliases.get(v, v)

    def field_ref(self, view, field, tf=None, context="query"):
        """An Omni field (with optional [timeframe]) -> LookML field name in its view (or alias)."""
        view = self.real(view)
        g = self.groups.get((view, field))
        base = self.field_names.get((view, field), lk_name(field))
        if g is None:
            if tf:
                raise Unsupported(f"timeframe [{tf}] on {view}.{field}, which is not a time field")
            return base
        if tf is None:
            if context == "sql":
                return f"{base}_raw"
            tf_l = "date" if g.get("datatype") == "date" else "time"
        else:
            tf_l = TIMEFRAME.get(tf, "?")
            if tf_l in (None, "?"):
                raise Unsupported(f"timeframe [{tf}] has no LookML equivalent")
        g.setdefault("need", set()).add(tf_l)
        return f"{base}_{tf_l}"

    def query_field(self, ref: str):
        """'view.field[tf]' from a document query -> 'lkview.lkfield'."""
        m = re.fullmatch(r"(\w+)\.(\w+)(?:\[(\w+)\])?", ref)
        if not m:
            raise Unsupported(f"field reference {ref!r} not understood")
        v, f, tf = m.groups()
        if self.real(v) not in self.est.views:
            raise Unsupported(f"view {v} is not in the shared model (a workbook-only field or view)")
        known = set(self.resolved(self.real(v), "dimensions")) | set(self.resolved(self.real(v), "measures"))
        if f not in known:
            raise Unsupported(f"field {v}.{f} is not in the shared model (defined in the workbook)")
        return f"{self.lk_view(v)}.{self.field_ref(v, f, tf)}"

    # -- views ----------------------------------------------------------------
    def table_sql(self, body):
        cat, sch, tab = body.get("catalog"), body.get("schema"), body.get("table_name")
        parts = [p for p in (cat, sch, tab) if p]
        if self.est.dialect == "bigquery":
            if not cat and self.est.model_meta.get("database"):
                parts = [self.est.model_meta["database"]] + parts
            return "`" + ".".join(parts) + "`"
        return ".".join(parts)

    def convert_view(self, v):
        if self.lk_view(v) in self.views:
            return
        lv = self.lk_view(v)
        raw = self.est.views[v]
        body = self.resolved_view(v)
        obj = self.vid(v)
        out = {"name": v, "label": body.get("label"), "description": body.get("description"), "dims": {},
               "groups": {}, "measures": {}, "filters": {}, "source": None, "extension": None}
        self.views[lv] = out
        for k in sorted(set(raw) - VIEW_KEYS):
            self.need(obj, f"view_key_{k}", "assisted", f"view key {k!r} not converted", fragment(raw[k], 300))
        if raw.get("template"):
            out["extension"] = "required"
        if body.get("query"):
            self.count("query_view_from_topic", "redesign")
            self.need(obj, "query_view_from_topic", "redesign",
                      "a query view built from a topic query (Omni query:) has no SQL in the model",
                      "a native derived table (explore_source) or a view on the generated SQL")
            out["source"] = {"error": True}
        elif body.get("sql") and SELECT_STAR.fullmatch(str(body["sql"])):
            out["source"] = {"table": SELECT_STAR.fullmatch(str(body["sql"])).group(1)}
            self.count("table_view", "mechanical")
        elif body.get("sql"):
            out["source"] = {"derived_sql": str(body["sql"]).strip()}
            if MUSTACHE.search(str(body["sql"])):
                self.need(obj, "templated_sql_view", "redesign",
                          "Mustache templating in the view's SQL", "Liquid {% condition %} or a parameter")
                out["source"] = {"error": True}
            self.count("sql_view", "mechanical")
        elif body.get("table_name"):
            out["source"] = {"table": self.table_sql(body)}
            self.count("table_view", "mechanical")
        else:
            out["source"] = {"error": True}
            self.need(obj, "view_without_source", "redesign", "view has no table_name, sql or query", None)
        if raw.get("extends"):
            self.count("extends", "mechanical")
            for p in raw["extends"]:
                self.deps.append({"from": obj, "to": self.vid(p), "kind": "extends"})
        if body.get("custom_compound_primary_key_sql"):
            self.need(obj, "compound_primary_key", "assisted", "compound primary key",
                      "a hidden dimension concatenating the key columns, with primary_key: yes")
        for f, d in sorted(self.resolved(v, "dimensions").items()):
            self.convert_dimension(v, f, d or {}, out)
        for f, m in sorted(self.resolved(v, "measures").items()):
            self.convert_measure(v, f, m or {}, out)
        for f, fl in sorted((body.get("filters") or {}).items()):
            fl = fl or {}
            ftype = {"timestamp": "date_time", "date": "date", "string": "string", "number": "number",
                     "boolean": "yesno"}.get(fl.get("type"), "string")
            out["filters"][self.field_names[(v, f)]] = {"type": ftype, "label": fl.get("label"),
                                                        "description": fl.get("description")}
            self.count("filter_only_field", "mechanical")
            self.need(self.fid(v, f), "filter_only_field", "assisted",
                      "filter-only field: Omni applies it through Mustache in SQL",
                      "Liquid {% condition " + self.field_names[(v, f)] + " %} in the view's SQL")
        self.view_fields[v] = set(self.resolved(v, "dimensions")) | set(self.resolved(v, "measures"))

    def common(self, obj, d, keys):
        o = {}
        for k in ("label", "description", "group_label", "view_label"):
            if d.get(k) is not None:
                o[k] = d[k]
        if d.get("hidden"):
            o["hidden"] = True
        fmt = d.get("format")
        if fmt is not None:
            f = str(fmt).lower()
            if f in FORMAT_NAME:
                o["value_format_name"] = FORMAT_NAME[f]
            elif f in FORMAT_STRING:
                o["value_format"] = FORMAT_STRING[f]
            else:
                self.need(obj, "format", "assisted", f"format {fmt!r} has no LookML equivalent: emitted without it",
                          "value_format with an Excel-style format string")
        for k in sorted(set(d) - keys):
            self.need(obj, f"field_key_{k}", "assisted", f"field key {k!r} not converted", fragment(d[k], 300))
        if set(d) & AI_KEYS:
            self.need(obj, "ai_context", "drop", "Omni AI context not migrated (no LookML equivalent)", None)
        if d.get("drill_fields"):
            try:
                o["drill_fields"] = [self.query_field(x) if "." in x else x for x in d["drill_fields"]]
            except Unsupported as e:
                self.need(obj, "drill_fields", "assisted", f"drill fields not converted: {e}", None)
        if d.get("links"):
            self.need(obj, "links", "assisted", "links: Omni Mustache tokens are not Liquid",
                      "LookML link: with Liquid {{ value }} tokens")
        if d.get("markdown"):
            self.need(obj, "markdown", "redesign", "markdown display (Mustache) not converted", "LookML html: with Liquid")
        if d.get("required_access_grants"):
            o["required_access_grants"] = list(d["required_access_grants"])
            self.need(obj, "required_access_grants", "assisted", "access grants must exist in the LookML model", None)
        return o

    def convert_dimension(self, v, f, d, out):
        obj = self.fid(v, f)
        name = self.field_names[(v, f)]
        body = self.resolved_view(v)
        if d.get("parent_field") or d.get("nested_on_field"):
            self.count("nested_field", "redesign")
            self.need(obj, "nested_field", "redesign",
                      "a field inside a record or repeated column (parent_field / nested_on_field)",
                      "${TABLE}.parent.child for a record; a join on UNNEST for a repeated column")
            return
        sqlx = Sql(self, v, "dimension")
        try:
            if d.get("sql") is None:
                col = f
                sql = "${TABLE}." + (col if PLAIN_COLUMN.fullmatch(col) else
                                     ("`" + col + "`" if self.est.dialect == "bigquery" else '"' + col + '"'))
            else:
                sql = sqlx.translate(d["sql"])
        except Unsupported as e:
            self.count("dimension", "redesign")
            self.need(obj, "dimension", "redesign", str(e), None)
            return
        if sqlx.cross_views:
            self.need(obj, "cross_view_reference", "assisted",
                      f"references {', '.join(sorted(sqlx.cross_views))}: every explore exposing it must join them", None)
        if sqlx.complex_columns:
            self.need(obj, "column_qualification", "assisted",
                      "the expression holds a subquery: its column names were left as written",
                      "qualify the outer query's columns with ${TABLE}")
        if sqlx.measure_columns:
            self.need(obj, "measure_reference_in_dimension", "assisted",
                      f"references {', '.join(sorted(sqlx.measure_columns))}, a measure, which Omni reads here as the column: "
                      "written as ${TABLE}.<column>", "confirm the column is meant")
        o = self.common(obj, d, DIM_KEYS)
        o["sql"] = sql
        if d.get("primary_key"):
            o["primary_key"] = True
        if d.get("duration"):
            self.count("duration", "assisted")
            self.need(obj, "duration", "assisted", "duration dimension", "dimension_group type: duration (sql_start, sql_end)")
            return
        g = self.groups.get((v, f))
        if g is not None:
            tfs = []
            for t in g["omni"]:
                lt = TIMEFRAME.get(t)
                if lt is None:
                    self.need(obj, "timeframe", "assisted", f"timeframe {t} has no LookML equivalent: dropped", None)
                    continue
                tfs.append(lt)
            o["timeframes"] = tfs
            o["datatype"] = g.get("datatype")
            if d.get("convert_tz") is False:
                o["convert_tz"] = False
            o["_group"] = g
            out["groups"][name] = o
            self.count("time_dimension", "mechanical")
            return
        if d.get("bin_boundaries"):
            o["tiers"] = list(d["bin_boundaries"])
            o["type"] = "tier"
            self.count("tier", "assisted")
            self.need(obj, "bin_boundaries", "assisted", "bins became a tier: Looker labels tiers differently",
                      "confirm the tier style and labels")
        elif d.get("groups"):
            case = self.groups_to_case(d, sql)
            if case is None:
                self.count("grouped_dimension", "assisted")
                self.need(obj, "groups", "assisted", "groups other than equality on one field: not converted",
                          "a CASE expression by hand")
                return
            o["case"] = case
            self.count("grouped_dimension", "mechanical")
        else:
            self.count("dimension", "mechanical")
        col = d.get("sql") if isinstance(d.get("sql"), str) and PLAIN_COLUMN.fullmatch(d.get("sql") or "") else f
        ctype = (self.est.column_type(body, col) or "").upper()
        if "tiers" not in o:
            if ctype in ("BOOL", "BOOLEAN"):
                o["type"] = "yesno"
            elif ctype in ("INT64", "INTEGER", "INT", "NUMERIC", "BIGNUMERIC", "FLOAT64", "FLOAT", "NUMBER",
                           "DECIMAL", "DOUBLE", "BIGINT"):
                o["type"] = "number"
            elif ctype in ("STRING", "VARCHAR", "TEXT"):
                o["type"] = "string"
            elif d.get("format") and str(d["format"]).lower() in NUMERIC_FORMATS and str(d["format"]).lower() != "id":
                o["type"] = "number"
            elif (v, f) in self.boolean_fields:
                o["type"] = "yesno"
            elif (v, f) in self.numeric_fields:
                o["type"] = "number"
        if d.get("all_values") or d.get("suggestion_list"):
            o["suggestions"] = list(d.get("all_values") or d.get("suggestion_list"))
        if d.get("suggest_from_field"):
            o["suggest_dimension"] = d["suggest_from_field"]
        if d.get("order_by_field"):
            o["order_by_field"] = self.field_names.get((v, d["order_by_field"]), lk_name(d["order_by_field"]))
        out["dims"][name] = o

    def groups_to_case(self, d, sql):
        whens = []
        for g in d.get("groups") or []:
            flt = (g or {}).get("filter") or {}
            if set(flt) != {"is"}:
                return None
            vals = flt["is"] if isinstance(flt["is"], list) else [flt["is"]]
            lits = ", ".join("'" + str(x).replace("'", "\\'") + "'" if isinstance(x, str) else tidy_num(x) for x in vals)
            cond = f"{sql} = {lits}" if len(vals) == 1 else f"{sql} IN ({lits})"
            whens.append({"sql": cond, "label": g.get("name")})
        return {"whens": whens, "else": d.get("else")}

    def convert_measure(self, v, f, m, out):
        obj = self.fid(v, f)
        name = self.field_names[(v, f)]
        agg = m.get("aggregate_type")
        o = self.common(obj, m, MEASURE_KEYS)
        sqlx = Sql(self, v)
        try:
            sql = sqlx.translate(m["sql"]) if m.get("sql") is not None else None
        except Unsupported as e:
            self.count("measure", "redesign")
            self.need(obj, "measure", "redesign", str(e), None)
            return
        if sqlx.cross_views:
            self.need(obj, "cross_view_reference", "assisted",
                      f"references {', '.join(sorted(sqlx.cross_views))}: every explore exposing it must join them", None)
        if agg is None:
            if sql is None:
                self.count("measure", "redesign")
                self.need(obj, "measure", "redesign", "measure with neither aggregate_type nor sql", None)
                return
            o.update({"type": "number", "sql": sql})
            if re.search(r"\$\{TABLE\}", sql):
                self.custom_aggregates.append((v, obj))
            self.count("derived_measure", "mechanical")
        elif agg == "count" and sql is None:
            o["type"] = "count"
            self.count("measure", "mechanical")
        elif agg == "count":
            o.update({"type": "number", "sql": f"COUNT({sql})"})
            self.count("measure", "assisted")
            self.need(obj, "count_of_expression", "assisted", "count of an expression: COUNT(...) as a number measure",
                      "type: count_distinct if the values are keys")
        elif agg in AGG:
            o["type"] = AGG[agg]
            o["sql"] = sql if sql is not None else f"${{TABLE}}.{f}"
            if agg.endswith("_distinct_on"):
                key = m.get("custom_primary_key_sql")
                if not key:
                    self.need(obj, "distinct_key", "assisted", f"{agg} without custom_primary_key_sql",
                              "sql_distinct_key on the view's primary key")
                else:
                    try:
                        o["sql_distinct_key"] = Sql(self, v).translate(key)
                    except Unsupported as e:
                        self.need(obj, "distinct_key", "redesign", str(e), None)
                        return
            if agg.startswith("percentile"):
                o["percentile"] = m.get("percentile", 50)
            self.count("measure", "mechanical")
        else:
            self.count("measure", "redesign")
            self.need(obj, "aggregate_type", "redesign", f"aggregate_type {agg} has no LookML measure type", None)
            return
        if m.get("filters"):
            fl = []
            for key, cond in sorted(m["filters"].items()):
                mm = re.fullmatch(r"(?:(\w+)\.)?(\w+)(?:\[(\w+)\])?", key)
                expr = yaml_filter(cond)
                if not mm or expr is None:
                    self.count("measure_filter", "assisted")
                    self.need(obj, "measure_filter", "assisted",
                              f"filter {key}: {fragment(cond, 120)} not translated: measure withheld (an unfiltered measure would change the number)",
                              "a filters: expression by hand")
                    return
                fv, ff, ftf = mm.group(1) or v, mm.group(2), mm.group(3)
                try:
                    lf = self.field_ref(fv, ff, ftf or ("date" if (fv, ff) in self.groups and isinstance(cond, dict)
                                                         and "time_for_duration" in cond else None))
                except Unsupported as e:
                    self.need(obj, "measure_filter", "assisted", f"{e}: measure withheld", None)
                    return
                fl.append(((f"{self.lk_view(fv)}." if fv != v else "") + lf, expr))
            o["filters"] = fl
        out["measures"][name] = o

    # -- type hints from content ------------------------------------------------
    def type_hints(self):
        self.boolean_fields, self.numeric_fields = set(), set()

        def note(field, flt):
            m = re.fullmatch(r"(\w+)\.(\w+)", field)
            if not m or not isinstance(flt, dict):
                return
            if flt.get("type") == "boolean":
                self.boolean_fields.add(m.groups())
            elif flt.get("type") == "number":
                self.numeric_fields.add(m.groups())
        for doc in self.est.documents.values():
            for t in ((doc.get("queryPresentations") or {}).get("data") or {}).values():
                for field, flt in ((t.get("query") or {}).get("filters") or {}).items():
                    note(field, flt)
        for v, body in self.est.views.items():
            for m in (body.get("measures") or {}).values():
                for key, cond in ((m or {}).get("filters") or {}).items():
                    if isinstance(cond, dict) and any(isinstance(x, bool) for x in cond.values()):
                        self.boolean_fields.add((v, key))

    # -- explores ---------------------------------------------------------------
    def relationship(self, topic: dict, a: str, b: str, a_real: str | None = None):
        """The relationship joining b to a (a already in the explore, a_real the view behind an alias).
        Returns (rel, alias_of, reversed)."""
        froms = {a, a_real or a}
        for scope in (topic.get("relationships") or [], self.est.relationships):
            for r in scope:
                to = r.get("join_to_view_as") or r.get("join_to_view")
                if r.get("join_from_view") in froms and to == b:
                    return r, (r.get("join_to_view") if r.get("join_to_view_as") else None), False
            for r in scope:
                if r.get("join_from_view") == b and r.get("join_to_view") in froms and not r.get("join_to_view_as"):
                    return r, None, True
        return None, None, False

    def convert_topic(self, name):
        if name in self.explores:
            return self.explores[name]
        t = self.est.topics[name]
        obj = self.est.ident("topic", name)
        base = t.get("base_view")
        if base not in self.est.views:
            self.need(obj, "topic", "redesign", f"base view {base!r} is not in the model", None)
            self.count("topic", "redesign")
            self.explores[name] = None
            return None
        for k in sorted(set(t) - TOPIC_KEYS):
            self.need(obj, f"topic_key_{k}", "assisted", f"topic key {k!r} not converted", fragment(t[k], 300))
        if set(t) & AI_KEYS:
            self.need(obj, "ai_context", "drop", "Omni AI context and sample queries not migrated (no LookML equivalent)", None)
        x = {"name": lk_name(name), "base": base, "label": t.get("label"), "description": t.get("description"),
             "group_label": t.get("group_label"), "hidden": bool(t.get("hidden")), "joins": [], "views": [base],
             "names": [base]}
        self.convert_view(base)
        self.deps.append({"from": obj, "to": self.vid(base), "kind": "base_view"})

        def walk(parent, tree, parent_real=None):
            for child in sorted(tree or {}):
                r, alias_of, rev = self.relationship(t, parent, child, parent_real)
                real = alias_of or child
                if r is None or real not in self.est.views:
                    self.count("join", "redesign")
                    self.need(obj, "join", "redesign", f"no relationship joins {child} to {parent}",
                              "add the relationship, or drop the join")
                    continue
                try:
                    on = Sql(self, parent_real or parent).translate(r.get("on_sql") or "")
                except Unsupported as e:
                    self.need(obj, "join", "redesign", f"join {child}: {e}", None)
                    continue
                if not r.get("on_sql"):
                    self.need(obj, "join", "redesign", f"join {child} has no on_sql", None)
                    continue
                rel = r.get("relationship_type") or "many_to_one"
                rel = REVERSE_REL.get(rel, rel) if rev else rel
                jt = r.get("join_type") or "always_left"
                j = {"name": lk_name(child), "from": self.lk_view(real) if alias_of else None,
                     "type": JOIN_TYPE.get(jt, "left_outer"), "relationship": REL.get(rel, "many_to_one"), "sql_on": on}
                if jt not in JOIN_TYPE:
                    self.need(obj, "join_type", "assisted", f"join {child}: join_type {jt} has no LookML form: left_outer",
                              "confirm the join direction")
                if rev and jt != "inner":
                    self.need(obj, "join_direction", "assisted",
                              f"join {child}: the relationship is declared from {child} to {parent}",
                              "confirm the join type from this explore's side")
                if rel == "many_to_many":
                    self.need(obj, "many_to_many", "assisted", f"join {child} is many_to_many",
                              "confirm both views have a primary key (symmetric aggregates)")
                if alias_of:
                    self.count("join_alias", "mechanical")
                x["joins"].append(j)
                x["views"].append(real)
                x["names"].append(child)
                self.convert_view(real)
                self.count("join", "mechanical")
                self.deps.append({"from": obj, "to": self.vid(real), "kind": "joins"})
                walk(child, tree[child], real)
        walk(base, t.get("joins"))
        if t.get("always_where_sql"):
            try:
                x["sql_always_where"] = Sql(self, base).translate(t["always_where_sql"])
                self.count("always_where_sql", "mechanical")
            except Unsupported as e:
                self.need(obj, "always_where_sql", "redesign", str(e), None)
        for key, kind in (("default_filters", "always_filter"), ("always_where_filters", "sql_always_where")):
            if t.get(key):
                exprs = []
                for fk, cond in sorted(t[key].items()):
                    mm = re.fullmatch(r"(\w+)\.(\w+)(?:\[(\w+)\])?", fk)
                    e = yaml_filter(cond)
                    try:
                        lf = f"{self.lk_view(mm.group(1))}.{self.field_ref(mm.group(1), mm.group(2), mm.group(3) or ('date' if (mm.group(1), mm.group(2)) in self.groups else None))}" if mm else None
                    except Unsupported:
                        lf = None
                    exprs.append(f"{lf}: {lk_str(e)}" if lf and e is not None else f"{fk}: {fragment(cond, 80)}")
                self.need(obj, key, "assisted",
                          f"{key} not emitted: Omni applies it to new queries, while Looker's {kind} would also change saved tiles",
                          f"{kind}: [{', '.join(exprs)}]")
        if t.get("access_filters"):
            x["access_filters"] = []
            for af in t["access_filters"]:
                mm = re.fullmatch(r"(\w+)\.(\w+)", af.get("field") or "")
                if mm:
                    x["access_filters"].append({"field": f"{self.lk_view(mm.group(1))}.{self.field_ref(*mm.groups())}",
                                                "user_attribute": af.get("user_attribute")})
            self.need(obj, "access_filters", "assisted", "access filters need the user attributes in Looker", None)
        if t.get("required_access_grants"):
            x["required_access_grants"] = list(t["required_access_grants"])
            self.need(obj, "required_access_grants", "assisted", "access grants must exist in the LookML model", None)
        if t.get("fields"):
            flds = list(t["fields"])
            if all(isinstance(e, str) and (e == "all_views.*" or re.fullmatch(r"-\w+\.\w+", e)) for e in flds):
                x["fields"] = ["ALL_FIELDS*"] + [f"-{self.lk_view(e[1:].split('.')[0])}.{lk_name(e.split('.')[1])}"
                                                 for e in flds if e.startswith("-")]
            else:
                self.need(obj, "fields", "assisted", "topic fields list not converted", f"fields: {flds}")
        if t.get("cache_policy"):
            self.need(obj, "cache_policy", "assisted", "cache policy", "a datagroup and persist_with")
        self.count("topic", "mechanical")
        self.explores[name] = x
        return x

    def explore_for_view(self, view, extra_views):
        """A topicless tile queries a view directly: an explore on it, joining what the tile needs."""
        name = f"{lk_name(view)}_tiles"
        if name not in self.explores:
            self.convert_view(view)
            self.explores[name] = {"name": name, "base": view, "label": None, "description": None, "group_label": None,
                                   "hidden": True, "joins": [], "views": [view]}
        x = self.explores[name]
        for ev in sorted(extra_views - set(x["views"])):
            r, alias_of, rev = self.relationship({}, view, ev)
            if r is None:
                raise Unsupported(f"no relationship from {view} to {ev}")
            rel = r.get("relationship_type") or "many_to_one"
            x["joins"].append({"name": lk_name(ev), "from": None,
                               "type": JOIN_TYPE.get(r.get("join_type") or "always_left", "left_outer"),
                               "relationship": REVERSE_REL.get(rel, rel) if rev else rel,
                               "sql_on": Sql(self, view).translate(r["on_sql"])})
            x["views"].append(ev)
            self.convert_view(ev)
        return x

    # -- documents --------------------------------------------------------------
    def positions(self, doc):
        """attachedQueryKey -> gridPosition, and the text containers with theirs."""
        tiles, texts = {}, []

        def walk(n, pos):
            if isinstance(n, dict):
                pos = n.get("gridPosition") or pos
                key = (n.get("metadata") or {}).get("attachedQueryKey")
                if key is not None and n.get("gridPosition"):
                    tiles[str(key)] = (n["gridPosition"], n.get("name"))
                if n.get("type") in ("inline-text", "markdown", "text"):
                    texts.append((n, pos))
                for k, val in n.items():
                    if k != "gridPosition":
                        walk(val, pos)
            elif isinstance(n, list):
                for val in n:
                    walk(val, pos)
        walk(doc.get("containers") or [], None)
        return tiles, texts

    def convert_document(self, ident):
        doc = self.est.documents[ident]
        meta = (self.est.inv.get("documents") or {}).get(ident) or {}
        dobj = self.est.ident("document", ident)
        title = doc.get("name") or meta.get("name") or ident
        data = (doc.get("queryPresentations") or {}).get("data") or {}
        tiles, texts = self.positions(doc)
        elements, el_by_key, files = [], {}, {}
        for key in sorted(data, key=lambda k: (tiles.get(k, ({"y": 10 ** 6, "x": 0}, None))[0].get("y", 0),
                                                tiles.get(k, ({"x": 0}, None))[0].get("x", 0), k)):
            t = data[key]
            tobj = f"{dobj}/query:{key}"
            if key not in tiles:
                self.count("tile_not_on_dashboard", "drop")
                self.need(tobj, "tile_not_on_dashboard", "drop", f"workbook tab {t.get('name')!r} is not on the dashboard", None)
                continue
            pos, cname = tiles[key]
            try:
                e, pm = self.convert_tile(ident, key, t, tobj)
            except Unsupported as ex:
                self.count("tile", "assisted" if "workbook" in str(ex) else "redesign")
                self.need(tobj, "tile", "assisted" if "workbook" in str(ex) else "redesign",
                          f"tile {t.get('name')!r} not emitted: {ex}", None)
                continue
            e["title"] = cname or t.get("name") or e["title"]
            e.update(self.layout(pos))
            elements.append(e)
            el_by_key[key] = e
            pm.update({"document": title, "dashboard_file": None, "element": e["name"]})
            self.parity.append(pm)
            self.deps.append({"from": dobj, "to": tobj, "kind": "contains"})
        for n, pos in texts:
            content = n.get("content") or n.get("markdown") or n.get("text") or ""
            if MUSTACHE.search(content):
                self.need(f"{dobj}/text:{n.get('instanceKey')}", "text_variable", "assisted",
                          "text tile with Mustache tokens: kept as written", content[:200])
            el = {"name": f"text_{lk_name(n.get('instanceKey') or str(len(elements)))}", "type": "text",
                  "body_text": content}
            if pos:
                el.update(self.layout(pos))
            else:
                el.update({"row": 0, "col": 0, "width": 24, "height": 2})
                self.need(f"{dobj}/text:{n.get('instanceKey')}", "text_position", "assisted",
                          "text tile has no grid position of its own: placed at the top", None)
            elements.append(el)
            self.count("text_tile", "mechanical")
        filters = self.controls(ident, doc, el_by_key, dobj)
        if any(n.get("type") == "inline-page-switcher" for n in self.walk_nodes(doc.get("containers") or [])):
            self.need(dobj, "page_switcher", "assisted", "the document has pages: they became one dashboard",
                      "split into one LookML dashboard per page, linked")
        slug = bi_ir.slug(title)
        dash = {"dashboard": slug, "title": title, "layout": "newspaper", "preferred_viewer": "dashboards-next",
                "description": f"Migrated from Omni document {title} (omni_to_lookml {VERSION}, experimental)"}
        if filters:
            dash["filters"] = filters
        dash["elements"] = sorted(elements, key=lambda e: (e["row"], e["col"], e["name"]))
        rel = f"{self.root}dashboards/{slug}.dashboard.lookml"
        for pm in self.parity:
            if pm["source"].startswith(dobj + "/") and pm["dashboard_file"] is None:
                pm["dashboard_file"] = rel
        files[rel] = yaml.safe_dump([dash], sort_keys=False, allow_unicode=True, width=1000)
        self.dash_docs.append({**dash, "source_id": dobj})
        self.count("dashboard", "mechanical")
        return files

    @staticmethod
    def walk_nodes(n):
        if isinstance(n, dict):
            yield n
            for v in n.values():
                yield from Converter.walk_nodes(v)
        elif isinstance(n, list):
            for v in n:
                yield from Converter.walk_nodes(v)

    @staticmethod
    def layout(pos):
        return {"row": int(round(pos.get("y", 0) / ROW_SCALE)), "col": int(pos.get("x", 0)),
                "width": int(pos.get("w", 12)), "height": max(1, int(round(pos.get("h", 36) / ROW_SCALE)))}

    def convert_tile(self, ident, key, t, tobj):
        q = t.get("query") or {}
        if t.get("isSql") or (q.get("userEditedSQL") or "").strip():
            raise Unsupported("a SQL tile: a view on its SQL, or rebuild on an explore")
        vis = t.get("visConfig") or {}
        chart = vis.get("chartType")
        if chart == "omni-ai-summary-markdown" or t.get("type") not in (None, "query"):
            raise Unsupported(f"{chart or t.get('type')} tile has no Looker equivalent")
        fields_raw = [f for f in q.get("fields") or [] if f != "omni_period_pivot"]
        pivots_raw = [p for p in q.get("pivots") or [] if p != "omni_period_pivot"]
        if len(fields_raw) != len(q.get("fields") or []) or q.get("period_over_period_computations"):
            self.need(tobj, "period_over_period", "assisted", "period-over-period comparison not migrated",
                      "a period_over_period measure or an offset table calculation")
        field_map = {f: self.query_field(f) for f in fields_raw + pivots_raw}
        topic = t.get("topicName") or q.get("join_paths_from_topic_name")
        views_used = {f.split(".")[0] for f in field_map}
        if topic and topic in self.est.topics:
            x = self.convert_topic(topic)
            if x is None:
                raise Unsupported(f"topic {topic} was not converted")
            missing = views_used - set(x["views"]) - set(x.get("names", []))
            if missing:
                raise Unsupported(f"fields from {', '.join(sorted(missing))}, which topic {topic} does not join")
        else:
            base = q.get("table")
            if base not in self.est.views:
                raise Unsupported(f"no topic and base view {base!r} not in the model")
            x = self.explore_for_view(base, views_used - {base})
            self.need(tobj, "topicless_tile", "assisted", f"tile queries view {base} with no topic: explore {x['name']} made for it",
                      "move it onto a converted topic's explore")
        self.deps.append({"from": tobj, "to": self.est.ident("topic", topic) if topic in self.est.topics else self.vid(q.get("table")),
                          "kind": "queries"})
        if chart in CHART:
            etype, extra = CHART[chart]
        elif chart in CHART_ASSISTED:
            etype, extra = CHART_ASSISTED[chart], {}
            self.need(tobj, "chart_type", "assisted", f"chart {chart}: emitted as {etype}", "finish the visualisation")
        else:
            etype, extra = "looker_grid", {}
            if chart is not None:
                self.need(tobj, "chart_type", "assisted", f"chart {chart}: emitted as a table", "pick a Looker chart")
            elif fields_raw:
                etype = "single_value" if len(fields_raw) == 1 else "looker_grid"
                self.need(tobj, "chart_type", "assisted", "tile with no chart type (markdown or automatic)",
                          "pick a Looker chart")
        filters = {}
        for fk, flt in sorted((q.get("filters") or {}).items()):
            expr, cls = query_filter(flt)
            m = re.fullmatch(r"(\w+)\.(\w+)(?:\[(\w+)\])?", fk)
            if expr is None or not m:
                raise Unsupported(f"filter on {fk} not translated ({fragment(flt, 160)})")
            v, f, tf = m.groups()
            if (self.real(v), f) in self.groups and tf is None:
                tf = "date"
            try:
                lf = f"{self.lk_view(v)}.{self.field_ref(v, f, tf)}"
            except Unsupported as e:
                raise Unsupported(f"filter on {fk}: {e}")
            if self.real(v) not in self.est.views:
                raise Unsupported(f"filter on {fk}: view not in the model")
            if cls == "assisted":
                self.need(tobj, "date_filter", "assisted",
                          f"date filter {flt.get('kind')} {flt.get('left_side') or flt.get('values')} {flt.get('right_side') or ''} became {expr!r}: confirm the window",
                          "check where the window starts and whether its end is included; run both sides on the same day")
            filters[lf] = expr
        calcs, dyn = [], []
        for c in q.get("calculations") or []:
            if str(c.get("calc_name", "")).startswith("_omni"):
                continue
            try:
                expr = self.calc_expr(c.get("sql_expression") or {})
            except Unsupported as e:
                self.need(tobj, "table_calculation", "assisted", f"calculation {c.get('label') or c.get('calc_name')}: {e}",
                          "a Looker table calculation by hand")
                continue
            name = lk_name(c.get("calc_name"))
            d = {"category": "table_calculation", "expression": expr, "label": c.get("label") or c.get("calc_name"),
                 "table_calculation": name, "_kind_hint": "measure", "_type_hint": "number"}
            fmt = str(c.get("format") or "").lower()
            if fmt in FORMAT_NAME:
                d["value_format_name"] = FORMAT_NAME[fmt]
            dyn.append(d)
            calcs.append(name)
            self.count("table_calculation", "mechanical")
        if q.get("column_totals") or q.get("row_totals"):
            self.need(tobj, "totals", "assisted", "column or row totals", "show_totals / show_row_totals on the element")
        e = {"name": f"{bi_ir.slug(t.get('name') or 'tile')}_{key}", "title": t.get("name"), "model": self.model,
             "explore": x["name"], "type": etype, "fields": [field_map[f] for f in fields_raw] + calcs}
        if pivots_raw:
            e["pivots"] = [field_map[p] for p in pivots_raw]
        if filters:
            e["filters"] = filters
        sorts = []
        for s in q.get("sorts") or []:
            col = s.get("column_name")
            if col in field_map:
                sorts.append(field_map[col] + (" desc" if s.get("sort_descending") else ""))
            elif col and col != "omni_period_pivot":
                try:
                    sorts.append(self.query_field(col) + (" desc" if s.get("sort_descending") else ""))
                except Unsupported:
                    self.need(tobj, "sort", "assisted", f"sort on {col} not converted", None)
        if sorts:
            e["sorts"] = sorts
        if q.get("limit"):
            e["limit"] = int(q["limit"])
        if dyn:
            e["dynamic_fields"] = dyn
        e.update(extra)
        self.count("tile", "mechanical")
        pm = {"source": tobj, "source_query_key": key, "document_identifier": ident, "explore": x["name"],
              "fields": e["fields"], "source_fields": fields_raw, "field_map": {k: field_map[k] for k in fields_raw}}
        return e, pm

    def calc_expr(self, node) -> str:
        t = node.get("type")
        if t == "field":
            return "${" + self.query_field(node["field_name"]) + "}"
        if t == "literal":
            v = node.get("value", node.get("string_value"))
            return tidy_num(v) if isinstance(v, (int, float)) else '"' + str(v).replace('"', '\\"') + '"'
        if t == "call":
            ops = [self.calc_expr(o) for o in node.get("operands") or []]
            op = node.get("operator")
            infix = {"SqlStdOperatorTable.PLUS": "+", "SqlStdOperatorTable.MINUS": "-",
                     "SqlStdOperatorTable.MULTIPLY": "*", "SqlStdOperatorTable.DIVIDE": "/"}
            if op in infix and len(ops) == 2:
                return f"({ops[0]} {infix[op]} {ops[1]})"
            if op == "Omni.OMNI_FX_SAFE_DIVIDE" and len(ops) == 2:
                return f"if({ops[1]} = 0, null, {ops[0]} / {ops[1]})"
            raise Unsupported(f"operator {op} not translated")
        raise Unsupported(f"expression node {t} not translated")

    def controls(self, ident, doc, el_by_key, dobj):
        out = []
        cdata = (doc.get("controls") or {}).get("data") or {}
        order = (doc.get("controls") or {}).get("order") or sorted(cdata)
        for cid in [c for c in order if c in cdata] + sorted(set(cdata) - set(order)):
            c = cdata[cid]
            cfg = c.get("config") or {}
            cobj = f"{dobj}/control:{cid}"
            if cfg.get("type") == "FIELD_SELECTION" or cfg.get("kind") == "FIELD":
                self.count("field_selection_control", "redesign")
                self.need(cobj, "field_selection_control", "redesign", f"control {cfg.get('label')!r} switches fields",
                          "a LookML parameter with Liquid in a dimension")
                continue
            fname = cfg.get("fieldName")
            m = re.fullmatch(r"(\w+)\.(\w+)", fname or "")
            expr, cls = query_filter({k: v for k, v in cfg.items() if k in ("type", "kind", "values", "is_negative",
                                                                             "left_side", "right_side", "is_inclusive",
                                                                             "filters", "conjunction")})
            if not m or expr is None or self.real(m.group(1)) not in self.est.views:
                self.count("control", "assisted")
                self.need(cobj, "control", "assisted", f"control {cfg.get('label')!r} not converted", fragment(cfg, 300))
                continue
            name = lk_name(cid)
            for key, target in sorted((c.get("map") or {}).items()):
                if target and key in el_by_key and re.fullmatch(r"(\w+)\.(\w+)", target):
                    tv, tf = target.split(".")
                    if self.real(tv) not in self.est.views:
                        continue
                    tff = "date" if (self.real(tv), tf) in self.groups else None
                    el_by_key[key].setdefault("listen", {})[name] = f"{self.lk_view(tv)}.{self.field_ref(tv, tf, tff)}"
            v, f = m.groups()
            tff = "date" if (self.real(v), f) in self.groups else None
            field = f"{self.lk_view(v)}.{self.field_ref(v, f, tff)}"
            explore = next((e["explore"] for k, e in sorted(el_by_key.items()) if name in (e.get("listen") or {})), None)
            if explore is None:
                topic = cfg.get("topic")
                explore = lk_name(topic) if topic in self.est.topics else None
                if topic in self.est.topics:
                    self.convert_topic(topic)
            if explore is None:
                self.need(cobj, "control", "assisted", f"control {cfg.get('label')!r} has no tile listening and no topic",
                          "attach it to an explore by hand")
                continue
            flt = {"name": name, "title": cfg.get("label") or name, "type": "field_filter", "default_value": expr,
                   "allow_multiple_values": True, "required": bool(cfg.get("required")),
                   "ui_config": {"type": "advanced" if cfg.get("type") in ("date", "timestamp") else "tag_list",
                                 "display": "popover"},
                   "model": self.model, "explore": explore, "field": field}
            if cls == "assisted":
                self.need(cobj, "date_filter", "assisted",
                          f"control default {cfg.get('kind')} {cfg.get('left_side') or cfg.get('values')} {cfg.get('right_side') or ''} became {expr!r}: confirm the window",
                          "check where the window starts and whether its end is included")
            out.append(flt)
            self.count("control", "mechanical")
        return out

    # -- rendering --------------------------------------------------------------
    def render_field_common(self, o, ind="    "):
        out = []
        for k in ("label", "group_label", "view_label", "description"):
            if o.get(k) is not None:
                out.append(f"{ind}{k}: {lk_str(o[k])}")
        if o.get("hidden"):
            out.append(f"{ind}hidden: yes")
        if o.get("value_format_name"):
            out.append(f"{ind}value_format_name: {o['value_format_name']}")
        if o.get("value_format"):
            out.append(f"{ind}value_format: {lk_str(o['value_format'])}")
        if o.get("drill_fields"):
            out.append(f"{ind}drill_fields: [{', '.join(o['drill_fields'])}]")
        if o.get("required_access_grants"):
            out.append(f"{ind}required_access_grants: [{', '.join(o['required_access_grants'])}]")
        return out

    def render_view(self, name, v):
        out = [f"view: {name} {{"]
        if v.get("extension"):
            out.append("  extension: required")
        src = v["source"] or {}
        if src.get("table"):
            out.append(f"  sql_table_name: {src['table']} ;;")
        elif src.get("derived_sql"):
            out += ["  derived_table: {", "    sql: " + src["derived_sql"].replace("\n", "\n      ") + " ;;", "  }"]
        if v.get("label"):
            out.append(f"  label: {lk_str(v['label'])}")
        for fname in sorted(v["filters"]):
            fl = v["filters"][fname]
            out += ["", f"  filter: {fname} {{", f"    type: {fl['type']}"]
            if fl.get("label"):
                out.append(f"    label: {lk_str(fl['label'])}")
            out.append("  }")
        for dname in sorted(v["dims"]):
            d = v["dims"][dname]
            out += ["", f"  dimension: {dname} {{"]
            if d.get("primary_key"):
                out.append("    primary_key: yes")
            if d.get("type"):
                out.append(f"    type: {d['type']}")
            if d.get("tiers"):
                out += [f"    tiers: [{', '.join(tidy_num(x) for x in d['tiers'])}]", "    style: integer"]
            out += self.render_field_common(d)
            out.append(f"    sql: {d['sql']} ;;")
            if d.get("case"):
                out.append("    case: {")
                for w in d["case"]["whens"]:
                    out += ["      when: {", f"        sql: {w['sql']} ;;", f"        label: {lk_str(w['label'])}", "      }"]
                if d["case"].get("else") is not None:
                    out.append(f"      else: {lk_str(d['case']['else'])}")
                out.append("    }")
            if d.get("suggestions"):
                out.append(f"    suggestions: [{', '.join(lk_str(s) for s in d['suggestions'])}]")
            if d.get("suggest_dimension"):
                out.append(f"    suggest_dimension: {d['suggest_dimension']}")
            if d.get("order_by_field"):
                out.append(f"    order_by_field: {d['order_by_field']}")
            out.append("  }")
        for gname in sorted(v["groups"]):
            g = v["groups"][gname]
            tfs = set(g["timeframes"]) | g["_group"].get("need", set()) | {"raw"}
            if "time" not in tfs and "date" not in tfs:
                tfs.add("date")
            out += ["", f"  dimension_group: {gname} {{", "    type: time",
                    f"    timeframes: [{', '.join(t for t in TF_ORDER if t in tfs)}]"]
            if g.get("datatype"):
                out.append(f"    datatype: {g['datatype']}")
            if g.get("convert_tz") is False:
                out.append("    convert_tz: no")
            out += self.render_field_common(g)
            out += [f"    sql: {g['sql']} ;;", "  }"]
        for mname in sorted(v["measures"]):
            m = v["measures"][mname]
            out += ["", f"  measure: {mname} {{", f"    type: {m['type']}"]
            if m.get("percentile") is not None:
                out.append(f"    percentile: {m['percentile']}")
            out += self.render_field_common(m)
            if m.get("sql"):
                out.append(f"    sql: {m['sql']} ;;")
            if m.get("sql_distinct_key"):
                out.append(f"    sql_distinct_key: {m['sql_distinct_key']} ;;")
            if m.get("filters"):
                out.append("    filters: [" + ", ".join(f"{f}: {lk_str(e)}" for f, e in m["filters"]) + "]")
            out.append("  }")
        out.append("}")
        return "\n".join(out) + "\n"

    def render_model(self):
        out = [f"connection: {lk_str(self.connection)}", "", f'include: "/{self.root}views/*.view.lkml"',
               f'include: "/{self.root}dashboards/*.dashboard.lookml"']
        mf = self.est.model_file or {}
        if mf.get("week_start_day"):
            out.append(f"week_start_day: {str(mf['week_start_day']).lower()}")
        if mf.get("fiscal_month_offset") is not None:
            out.append(f"fiscal_month_offset: {int(mf['fiscal_month_offset'])}")
        for x in sorted((e for e in self.explores.values() if e), key=lambda e: e["name"]):
            out += ["", f"explore: {x['name']} {{"]
            if x["name"] != self.lk_view(x["base"]):
                out.append(f"  view_name: {self.lk_view(x['base'])}")
            for k in ("label", "group_label", "description"):
                if x.get(k):
                    out.append(f"  {k}: {lk_str(x[k])}")
            if x.get("hidden"):
                out.append("  hidden: yes")
            if x.get("fields"):
                out.append(f"  fields: [{', '.join(x['fields'])}]")
            if x.get("required_access_grants"):
                out.append(f"  required_access_grants: [{', '.join(x['required_access_grants'])}]")
            if x.get("sql_always_where"):
                out.append(f"  sql_always_where: {x['sql_always_where']} ;;")
            for af in x.get("access_filters") or []:
                out += ["  access_filter: {", f"    field: {af['field']}", f"    user_attribute: {af['user_attribute']}", "  }"]
            for j in x["joins"]:
                out.append(f"  join: {j['name']} {{")
                if j.get("from"):
                    out.append(f"    from: {j['from']}")
                out += [f"    type: {j['type']}", f"    relationship: {j['relationship']}",
                        f"    sql_on: {j['sql_on']} ;;", "  }"]
            out.append("}")
        return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Running a conversion
# ---------------------------------------------------------------------------

def run(est: Estate, model: str, connection: str, topics=None, documents=None, include_root="", all_views=False):
    cv = Converter(est, lk_name(model), connection, include_root)
    cv.type_hints()
    mf = est.model_file or {}
    for k in sorted(set(mf) - MODEL_KEYS):
        cv.need(est.ident("model", est.model_meta.get("name") or "model"), f"model_key_{k}", "assisted",
                f"model key {k!r} not converted", fragment(mf[k], 300))
    if mf.get("ai_context"):
        cv.need(est.ident("model", est.model_meta.get("name") or "model"), "ai_context", "drop",
                "Omni AI context not migrated (no LookML equivalent)", None)
    for k in ("access_grants", "dynamic_schemas", "query_timezone", "cache_policies", "default_cache_policy"):
        if mf.get(k):
            cv.need(est.ident("model", est.model_meta.get("name") or "model"), k,
                    "redesign" if k == "dynamic_schemas" else "assisted", f"model setting {k} not converted",
                    {"access_grants": "access_grant: blocks in the model file", "dynamic_schemas": "Liquid in sql_table_name",
                     "query_timezone": "the Looker connection's query time zone",
                     "cache_policies": "datagroups", "default_cache_policy": "a datagroup and persist_with"}[k])
    docs = sorted(d for d in est.documents if not documents or d in documents)
    tps = sorted(t for t in est.topics if not topics or t in topics)
    if topics or documents:
        for d in docs:
            for t in ((est.documents[d].get("queryPresentations") or {}).get("data") or {}).values():
                tn = t.get("topicName") or (t.get("query") or {}).get("join_paths_from_topic_name")
                if tn in est.topics and tn not in tps:
                    tps.append(tn)
    for t in sorted(tps):
        cv.convert_topic(t)
    if all_views:
        for v in sorted(est.views):
            cv.convert_view(v)
    files = {}
    for d in docs:
        files.update(cv.convert_document(d))
    # the needed timeframes are known only after the documents; render last
    for lv in sorted(cv.views):
        v = cv.views[lv]
        if (v["source"] or {}).get("error"):
            continue
        files[f"{cv.root}views/{lv}.view.lkml"] = cv.render_view(lv, v)
    # explores that reach a view not emitted are withheld
    for name, x in list(cv.explores.items()):
        if x and any((cv.views.get(cv.lk_view(v), {}).get("source") or {}).get("error") for v in x["views"]):
            cv.need(est.ident("topic", name), "topic", "redesign", "topic reaches a view that was not converted",
                    "convert the view by hand, or drop the join")
            cv.explores[name] = None
    files[f"models/{cv.model}.model.lkml"] = cv.render_model()
    joined = {v for x in cv.explores.values() if x and x["joins"] for v in x["views"]}
    for v, obj in cv.custom_aggregates:
        if v in joined:
            cv.need(obj, "custom_aggregate", "assisted",
                    "measure SQL aggregates columns directly and its view is in an explore with joins: no protection from fan-out",
                    "an aggregate_type measure, or keep the view joined many_to_one only")
    cv.needs.sort(key=lambda n: (n["object"], n["construct"], n["reason"]))
    cv.parity.sort(key=lambda p: (p["dashboard_file"] or "", p["source"]))
    summary = {"converter": "omni_to_lookml", "version": VERSION, "model": cv.model,
               "omni_model": est.model_meta.get("name"), "dialect": est.dialect,
               "counts": {k: dict(sorted(v.items())) for k, v in sorted(cv.counts.items())},
               "views": sum(1 for f in files if f.endswith(".view.lkml")),
               "explores": sum(1 for x in cv.explores.values() if x),
               "dashboards": sum(1 for f in files if f.endswith(".dashboard.lookml")), "needs_human": len(cv.needs)}
    return cv, files, summary


# ---------------------------------------------------------------------------
# Audit outputs and IR
# ---------------------------------------------------------------------------
MODEL_COLUMNS = ["object_type", "object_uri", "dataset", "model", "field_name", "label", "construct",
                 "translation_class", "complexity", "reason", "source_file"]
CONTENT_COLUMNS = ["object_type", "object_uri", "id", "title", "folder", "topic", "chart_type", "visits",
                   "last_viewed", "updated_at", "tile_count", "translation_class", "reason"]
COMPLEXITY = {"mechanical": "Low", "assisted": "Medium", "redesign": "High", "drop": "Low"}


def audit(est: Estate):
    cv, _, _ = run(est, "omni_audit", "warehouse", all_views=True)
    cls_of = cv.obj_class
    model_rows, content_rows, ir = [], [], []
    for v in sorted(est.views):
        if cv.lk_view(v) not in cv.views:
            continue
        body = cv.resolved_view(v)
        vobj = cv.vid(v)
        vc, vr = cls_of.get(vobj, ("mechanical", ""))
        construct = "query_view" if body.get("query") else ("sql_view" if body.get("sql") else "table_view")
        model_rows.append({"object_type": "view", "object_uri": vobj, "dataset": v, "model": cv.lk_view(v),
                           "label": body.get("label"), "construct": construct, "translation_class": vc,
                           "complexity": COMPLEXITY[vc], "reason": vr, "source_file": f"model/{est.view_path[v]}"})
        fields = []
        for kind, items in (("dimension", cv.resolved(v, "dimensions")), ("measure", cv.resolved(v, "measures"))):
            for f, d in sorted(items.items()):
                d = d or {}
                fo = cv.fid(v, f)
                fc, fr = cls_of.get(fo, ("mechanical", ""))
                cons = "time_dimension" if (v, f) in cv.groups else (
                    "derived_measure" if kind == "measure" and not d.get("aggregate_type") else kind)
                model_rows.append({"object_type": "field", "object_uri": fo, "dataset": v, "model": cv.lk_view(v),
                                   "field_name": f, "label": d.get("label"), "construct": cons, "translation_class": fc,
                                   "complexity": COMPLEXITY[fc], "reason": fr, "source_file": f"model/{est.view_path[v]}"})
                fields.append({"id": fo, "name": f, "label": d.get("label"), "field_kind": kind,
                               "expression": str(d["sql"]) if d.get("sql") is not None else None,
                               "aggregation": d.get("aggregate_type"), "format": d.get("format"),
                               "hidden": bool(d.get("hidden")), "key": "primary" if d.get("primary_key") else None,
                               "class": fc, "reason": fr or None,
                               "target": f"looker:{cv.model}:view:{cv.lk_view(v)}"})
        ir.append(bi_ir.obj("dataset", vobj, v, {"file": f"model/{est.view_path[v]}",
                                                 "fragment": fragment({k: body.get(k) for k in ("schema", "table_name", "sql", "query", "extends")})},
                            label=body.get("label"), description=body.get("description"),
                            connection={"class": est.dialect, "project": body.get("catalog") or est.model_meta.get("database"),
                                        "schema": body.get("schema")},
                            relations=[{"name": v, "table": f"{body.get('schema') or ''}.{body['table_name']}".strip(".")}]
                            if body.get("table_name") else None,
                            fields=fields, materialisation="live", **{"class": vc, "reason": vr or None}))
    for t in sorted(est.topics):
        tobj = est.ident("topic", t)
        x = cv.explores.get(t)
        tc, tr = cls_of.get(tobj, ("mechanical", "") if x else ("redesign", "not converted"))
        tb = est.topics[t]
        model_rows.append({"object_type": "topic", "object_uri": tobj, "dataset": tb.get("base_view"), "model": lk_name(t),
                           "label": tb.get("label"), "construct": "topic", "translation_class": tc,
                           "complexity": COMPLEXITY[tc], "reason": tr, "source_file": f"model/{est.topic_path[t]}"})
        ir.append(bi_ir.obj("model", tobj, t, {"file": f"model/{est.topic_path[t]}", "fragment": fragment(tb)},
                            label=tb.get("label"), description=tb.get("description"),
                            base_dataset=cv.vid(tb.get("base_view")) if tb.get("base_view") else None,
                            datasets=sorted(cv.vid(v) for v in (x or {}).get("views", [])) or None,
                            joins=[{"left": tb.get("base_view"), "right": j["name"], "type": j["type"].split("_")[0],
                                    "on": j["sql_on"], "cardinality": j["relationship"], "kind": "relationship",
                                    "class": "mechanical"} for j in (x or {}).get("joins", [])] or None,
                            **{"class": tc, "reason": tr or None}))
    for i, r in enumerate(est.relationships):
        model_rows.append({"object_type": "relationship", "object_uri": est.ident("relationship", i + 1),
                           "dataset": f"{r.get('join_from_view')} -> {r.get('join_to_view_as') or r.get('join_to_view')}",
                           "construct": "relationship", "translation_class": "mechanical", "complexity": "Low",
                           "reason": f"{r.get('relationship_type')} {r.get('join_type') or 'always_left'}",
                           "source_file": "model/relationships"})
    for ident in sorted(est.documents):
        doc = est.documents[ident]
        meta = (est.inv.get("documents") or {}).get(ident) or {}
        dobj = est.ident("document", ident)
        tiles, _ = cv.positions(doc)
        data = (doc.get("queryPresentations") or {}).get("data") or {}
        on = [k for k in data if k in tiles]
        dc = "mechanical"
        for k in on:
            c = cls_of.get(f"{dobj}/query:{k}", ("mechanical", ""))[0]
            if c in ("assisted", "redesign"):
                dc = "assisted"
        dcls = cls_of.get(dobj, (dc, ""))
        content_rows.append({"object_type": "document", "object_uri": dobj, "id": ident, "title": doc.get("name"),
                             "folder": meta.get("folder") or "", "visits": meta.get("visits", ""),
                             "last_viewed": meta.get("last_viewed_at") or "", "updated_at": meta.get("updated_at") or "",
                             "tile_count": len(on), "translation_class": dcls[0] if dcls[0] != "mechanical" else dc,
                             "reason": dcls[1]})
        tile_ir = []
        for k in sorted(data, key=lambda s: (len(s), s)):
            t = data[k]
            tobj = f"{dobj}/query:{k}"
            tc, tr = cls_of.get(tobj, ("mechanical", "") if k in on else ("drop", "not on the dashboard"))
            q = t.get("query") or {}
            topic = t.get("topicName") or q.get("join_paths_from_topic_name")
            content_rows.append({"object_type": "tile", "object_uri": tobj, "id": k, "title": t.get("name"),
                                 "folder": meta.get("folder") or "", "topic": topic or "",
                                 "chart_type": (t.get("visConfig") or {}).get("chartType") or "",
                                 "translation_class": tc, "reason": tr})
            ir.append(bi_ir.obj("report", tobj, t.get("name") or k, {"file": meta.get("file", f"documents/{ident}.json"),
                                                                       "fragment": fragment(q)},
                                datasets=sorted({cv.vid(f.split(".")[0]) for f in q.get("fields") or [] if "." in f}) or None,
                                query={"fields": q.get("fields"), "pivots": q.get("pivots") or None,
                                       "filters": sorted((q.get("filters") or {}).keys()) or None,
                                       "sql": bool(t.get("isSql"))},
                                visualisation={"chart_type": (t.get("visConfig") or {}).get("chartType")},
                                **{"class": tc, "reason": tr or None}))
            if k in on:
                gp = tiles[k][0]
                tile_ir.append({"id": tobj, "report": tobj, "position": {"row": gp.get("y"), "col": gp.get("x"),
                                                                         "width": gp.get("w"), "height": gp.get("h")},
                                "class": tc})
        ir.append(bi_ir.obj("dashboard", dobj, doc.get("name") or ident,
                            {"file": meta.get("file", f"documents/{ident}.json"), "sha256": meta.get("sha256"),
                             "updated_at": meta.get("updated_at"),
                             "fragment": fragment({k: doc.get(k) for k in ("name", "settings")})},
                            size={"width": 24}, tiles=tile_ir,
                            controls=[{"id": cid, "name": (c.get("config") or {}).get("label"),
                                       "type": (c.get("config") or {}).get("type")}
                                      for cid, c in sorted(((doc.get("controls") or {}).get("data") or {}).items())] or None,
                            **{"class": dcls[0] if dcls[0] != "mechanical" else dc}))
    for ident, meta in sorted((est.inv.get("skipped_documents") or {}).items()):
        content_rows.append({"object_type": "workbook", "object_uri": est.ident("document", ident), "id": ident,
                             "title": meta.get("name"), "folder": meta.get("folder") or "", "visits": meta.get("visits", ""),
                             "updated_at": meta.get("updated_at") or "", "translation_class": "drop",
                             "reason": meta.get("reason") or "no dashboard"})
    folders = sorted({(m.get("folder") or "") for m in (est.inv.get("documents") or {}).values()} - {""})
    for f in folders:
        ir.append(bi_ir.obj("folder", est.ident("folder", f), f, {"fragment": f}))
    return model_rows, content_rows, ir, cv.deps, cv.needs


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
OMNI_ISMS = [
    (re.compile(r"\$\{[^}]*\[[a-z_0-9]+\]\s*\}"), "Omni timeframe reference ${field[timeframe]}"),
    (re.compile(r"\{\{[#^/]?\s*(filters|[\w]+\.[\w]+)"), "Omni Mustache template"),
    (re.compile(r"^\s*(aggregate_type|base_view|join_from_view|join_to_view|relationship_type|on_sql|"
                r"bin_boundaries|all_values|parent_field|nested_on_field)\s*:"), "Omni model key"),
    (re.compile(r"\b\w+\.\w+\[(raw|date|week|month|quarter|year|day_of_week_name|month_name)\]"),
     "Omni timeframe field name"),
]


def lint(lookml_dir: Path):
    found = sorted(list(Path(lookml_dir).rglob("*.lkml")) + list(Path(lookml_dir).rglob("*.lookml")))
    if not found:
        return [f"{lookml_dir}: no LookML files (nothing was converted, or the wrong folder)"]
    problems = []
    for p in found:
        text = p.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            for rx, what in OMNI_ISMS:
                if rx.search(line):
                    problems.append(f"{p.relative_to(lookml_dir)}:{i}: {what}: {line.strip()[:160]}")
        if p.name.endswith(".view.lkml"):
            problems += [f"{p.relative_to(lookml_dir)}: field {n} is defined twice (Looker: 'Redefinition of field')"
                         for n in duplicate_fields(text)]
            problems += [f"{p.relative_to(lookml_dir)}: dimension {d} references measure {m} (Looker: 'Field references an aggregate')"
                         for d, m in dimension_on_measure(text)]
    return problems


def dimension_on_measure(view_text: str) -> list:
    """(dimension, measure) pairs where a dimension's SQL references a measure of the same view."""
    blocks = re.findall(r"^  (dimension|dimension_group|measure): (\w+) \{\n(.*?)^  \}", view_text, re.M | re.S)
    measures = {n for k, n, _ in blocks if k == "measure"}
    out = []
    for kind, name, body in blocks:
        if kind == "measure":
            continue
        for ref in re.findall(r"\$\{(\w+)\}", body):
            if ref in measures:
                out.append((name, ref))
    return sorted(set(out))


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

def names(s):
    return {x.strip() for x in (s or "").split(",") if x.strip()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "convert"):
        s = sub.add_parser(name)
        s.add_argument("--snapshot", required=True)
        s.add_argument("--out", required=True)
        if name == "convert":
            s.add_argument("--model", default="omni_migration")
            s.add_argument("--connection", default="warehouse")
            s.add_argument("--topics", default="", help="topics to convert (default: all, plus those the documents use)")
            s.add_argument("--documents", default="", help="document identifiers to convert (default: all)")
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
            (out / "needs_human.json").write_text(json.dumps(needs, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            by = {}
            for r in model_rows + content_rows:
                if r.get("translation_class"):
                    by[r["translation_class"]] = by.get(r["translation_class"], 0) + 1
            print(f"{len(est.views)} views, {len(est.topics)} topics, {len(est.documents)} documents; "
                  f"classes {dict(sorted(by.items()))} -> {out}")
            return 0
        cv, files, summary = run(est, a.model, a.connection, names(a.topics), names(a.documents), a.include_root)
    except (ConvertError, json.JSONDecodeError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / "needs_human.json").write_text(json.dumps(cv.needs, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "conversion_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    (out / "parity_map.json").write_text(json.dumps(cv.parity, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    write_jsonl(out / "dependencies.jsonl", cv.deps)
    print(f"{summary['views']} views, {summary['explores']} explores, {summary['dashboards']} dashboards, "
          f"{summary['needs_human']} needs_human -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

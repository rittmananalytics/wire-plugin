#!/usr/bin/env python3
"""
LookML to Omni model converter (wire#258, bi_migration release type, pair looker_to_omni).

Deterministic: the same LookML input produces byte-identical output. No AI call.
It implements every `mechanical` and `assisted` row of
wire/bi_pairs/looker_to_omni/translation_guide.md, and refuses every `redesign`
row into needs_human.json. The agent running /wire:omni-model-generate does the
judgement this script cannot: topic design, naming, and what to do with each
needs_human item. The agent never hand-writes what this script emits.

Usage:
    python3 wire/scripts/lookml_to_omni.py --lookml <dir> --out <dir>
        [--views a,b] [--explores e1,e2] [--overrides <dir>]
        [--report needs_human.json] [--default-schema SCHEMA]

Output layout (an Omni model repo):
    <out>/<SCHEMA>/<view_name>.view      one per LookML view, dimensions and measures keyed by name
    <out>/<explore_name>.topic           one per LookML explore
    <out>/relationships.yaml             global join definitions
    <out>/needs_human.json               every construct the script did not, or could not, translate
    <out>/conversion_summary.json        counts per construct and class, converter version
    <out>/ir/views/<view>.json           typed intermediate representation per view: identity, fields with
                                         class, references, emitted Omni body, unsupported constructs, source file
    <out>/ir/topics/<topic>.json         the same per explore
    <out>/dependencies.jsonl             edges: view contains field, field references field, topic base_view,
                                         topic joins view, topic join_on field

Omni facts this script relies on (see the pair's translation_guide.md for sources):
    - Omni has no ${TABLE}. A plain column dimension auto-maps by name; `sql:` uses
      ${field} or ${view.field}. A LookML timeframe reference ${created_month} becomes
      ${created[month]}.
    - Measure `filters:` values are operator objects ({is: x}), never bare scalars.
    - Aggregate types: sum, count, count_distinct, average, min, max, median, list,
      percentile, and the *_distinct_on variants.
    - Relationship types: one_to_one, many_to_one, one_to_many, many_to_many (and Omni's own
      assumed_many_to_one). Join types: always_left, inner, full_outer, cross, right_left, left_right.
    - An aliased join (`join: alias { from: v }`) is a relationship with join_to_view_as.

Requires: lkml (pip install lkml), pyyaml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

try:
    import lkml  # type: ignore
except ImportError:  # pragma: no cover
    lkml = None

import yaml

# ---------------------------------------------------------------------------
# Mapping tables (the deterministic core). property_mapping.md documents them.
# ---------------------------------------------------------------------------

VALUE_FORMAT_NAME = {
    "usd": "currency_2", "usd_0": "currency_0", "usd_2": "currency_2",
    "eur": "eurcurrency_2", "eur_0": "eurcurrency_0", "gbp": "gbpcurrency_2", "gbp_0": "gbpcurrency_0",
    "decimal_0": "number_0", "decimal_1": "number_1", "decimal_2": "number_2",
    "decimal_3": "number_3", "decimal_4": "number_4",
    "percent_0": "percent_0", "percent_1": "percent_1", "percent_2": "percent_2",
    "percent_3": "percent_3", "percent_4": "percent_4",
    "id": "id",
}

VALUE_FORMAT_STRING = {
    "#,##0": "number_0", "#,##0.0": "number_1", "#,##0.00": "number_2",
    "0": "number_0", "0.0": "number_1", "0.00": "number_2",
    "0%": "percent_0", "0.0%": "percent_1", "0.00%": "percent_2",
    "$#,##0": "currency_0", "$#,##0.00": "currency_2",
    "£#,##0": "gbpcurrency_0", "£#,##0.00": "gbpcurrency_2",
    "€#,##0": "eurcurrency_0", "€#,##0.00": "eurcurrency_2",
}

# LookML timeframe -> Omni timeframe. `time` is dropped: Omni's `raw` covers it.
TIMEFRAMES = {
    "raw": "raw", "time": None, "date": "date", "week": "week", "month": "month",
    "quarter": "quarter", "year": "year", "hour": "hour", "minute": "minute",
    "second": "second", "millisecond": "millisecond",
    "day_of_week": "day_of_week_name", "day_of_week_index": "day_of_week_num",
    "day_of_month": "day_of_month", "day_of_year": "day_of_year",
    "hour_of_day": "hour_of_day", "month_name": "month_name", "month_num": "month_num",
    "quarter_of_year": "quarter_of_year", "fiscal_quarter": "fiscal_quarter",
    "fiscal_year": "fiscal_year",
}
TIMEFRAME_TOKENS = sorted(TIMEFRAMES.keys(), key=len, reverse=True)

AGGREGATES = {
    "sum": "sum", "count": "count", "count_distinct": "count_distinct", "average": "average",
    "min": "min", "max": "max", "median": "median", "list": "list", "percentile": "percentile",
    "sum_distinct": "sum_distinct_on", "average_distinct": "average_distinct_on",
    "median_distinct": "median_distinct_on", "percentile_distinct": "percentile_distinct_on",
}
REDESIGN_MEASURE_TYPES = {"running_total", "percent_of_total", "percent_of_previous", "date", "string", "yesno"}

# Omni relationship_type values (docs.omni.co/modeling/relationships/parameters/relationship-type):
# one_to_one, many_to_one, one_to_many, many_to_many, assumed_many_to_one. Fan-out joins are
# supported; symmetric aggregates need primary_key on the joined views, which the lint checks.
RELATIONSHIPS = {"many_to_one": "many_to_one", "one_to_one": "one_to_one",
                 "one_to_many": "one_to_many", "many_to_many": "many_to_many"}
# Omni join_type values (…/parameters/join-type): always_left (default), inner, full_outer, cross,
# right_left, left_right.
JOIN_TYPES = {"left_outer": "always_left", "inner": "inner", "full_outer": "full_outer", "cross": "cross"}

PDT_KEYS = {"datagroup_trigger", "sql_trigger_value", "persist_for", "materialized_view", "increment_key", "cluster_keys", "partition_keys", "indexes", "distribution"}
DROPPED_DIMENSION_TYPES = {"string", "number", "date", "date_time", "yesno", "zipcode", "unquoted", "int"}
REDESIGN_DIMENSION_TYPES = {"location", "distance", "bin"}

LIQUID_RE = re.compile(r"\{%|%\}|\{\{|\}\}")
TABLE_REF_RE = re.compile(r'\$\{TABLE\}\.("?)([A-Za-z_][A-Za-z0-9_]*)\1')
TIMEFRAME_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_.]*?)_(" + "|".join(TIMEFRAME_TOKENS) + r")\}")


CONVERTER_VERSION = "1.1.0"   # bump on any change to the translation contract; recorded in baseline.yaml


def yes(v) -> bool:
    return str(v).strip().lower() in {"yes", "true"}


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

class Conversion:
    def __init__(self, project: str = "lookml") -> None:
        self.project = project                                          # identity namespace: looker:<project>:...
        self.views: "OrderedDict[str, OrderedDict]" = OrderedDict()   # view_name -> (schema, table, body)
        self.topics: "OrderedDict[str, OrderedDict]" = OrderedDict()
        self.relationships: list = []
        self.needs_human: list = []
        self.counts: dict = {}
        self.raw_views: list = []
        self.raw_explores: list = []

    def note(self, *, scope: str, name: str, field: str | None, construct: str, cls: str, reason: str, lkml_file: str, omni: str | None = None) -> None:
        entry = OrderedDict([
            ("scope", scope), ("name", name), ("field", field), ("construct", construct),
            ("class", cls), ("reason", reason), ("lkml_file", lkml_file),
        ])
        if omni:
            entry["omni"] = omni
        self.needs_human.append(entry)

    def count(self, construct: str, cls: str) -> None:
        self.counts.setdefault(construct, {}).setdefault(cls, 0)
        self.counts[construct][cls] += 1


# ---------------------------------------------------------------------------
# SQL and filter translation
# ---------------------------------------------------------------------------

def translate_sql(sql: str, groups_in_view: set[str]) -> str:
    """${TABLE}.col -> ${col}; ${group_timeframe} -> ${group[timeframe]}; strip ;;."""
    s = sql.strip()
    if s.endswith(";;"):
        s = s[:-2].strip()
    s = TABLE_REF_RE.sub(lambda m: "${" + m.group(2) + "}", s)

    def tf(m: "re.Match[str]") -> str:
        group, tfname = m.group(1), m.group(2)
        base = group.split(".")[-1]
        if base in groups_in_view and TIMEFRAMES.get(tfname):
            return "${" + group + "[" + TIMEFRAMES[tfname] + "]}"
        return m.group(0)
    return TIMEFRAME_REF_RE.sub(tf, s)


def is_plain_column(sql: str | None, name: str) -> bool:
    if sql is None:
        return True
    m = re.fullmatch(r'\s*\$\{TABLE\}\.("?)([A-Za-z_][A-Za-z0-9_]*)\1\s*;?;?\s*', sql)
    return bool(m and m.group(2).lower() == name.lower())


DATE_EXPR_RE = re.compile(
    r"^(\d+\s+(second|minute|hour|day|week|month|quarter|year)s?(\s+ago)?|"
    r"(last|this|next)\s+\w+|before\s+.*|after\s+.*|today|yesterday|tomorrow|\d{4}-\d{2}-\d{2}.*)$",
    re.I,
)


def translate_filter_value(raw: str, is_boolean_field: bool = False):
    """LookML filter expression -> Omni operator object, or None when not mechanical.

    Date expressions ("30 days", "last month", "before 2024-01-01") are never mechanical:
    Omni's date filter operators differ from Looker's grammar, so they go to needs_human.
    `Yes`/`No` map to booleans only when the caller knows the field is a yesno dimension.
    """
    v = str(raw).strip()
    if v == "":
        return None
    low = v.lower()
    if DATE_EXPR_RE.match(v):
        return None
    if low == "null":
        return OrderedDict([("is", None)])
    if low == "-null":
        return OrderedDict([("not", None)])
    if is_boolean_field and low in {"yes", "true"}:
        return OrderedDict([("is", True)])
    if is_boolean_field and low in {"no", "false"}:
        return OrderedDict([("is", False)])
    m = re.fullmatch(r"(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)", v)
    if m:
        op = {">": "greater_than", ">=": "greater_than_or_equal_to", "<": "less_than", "<=": "less_than_or_equal_to"}[m.group(1)]
        return OrderedDict([(op, _num(m.group(2)))])
    m = re.fullmatch(r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]", v)
    if m:
        return OrderedDict([("between", [_num(m.group(1)), _num(m.group(2))])])
    if v.startswith("%") and v.endswith("%") and len(v) > 2 and "%" not in v[1:-1]:
        return OrderedDict([("contains", v[1:-1])])
    if v.endswith("%") and "%" not in v[:-1]:
        return OrderedDict([("starts_with", v[:-1])])
    if v.startswith("%") and "%" not in v[1:]:
        return OrderedDict([("ends_with", v[1:])])
    if "%" in v or "_" in v and v.startswith("_"):
        return None
    if v.startswith("-"):
        rest = v[1:]
        if "," in rest:
            return OrderedDict([("is_not", [_scalar(x) for x in rest.split(",")])])
        return OrderedDict([("is_not", _scalar(rest))])
    if "," in v:
        parts = [p for p in v.split(",")]
        if any(p.strip().startswith("-") for p in parts):
            return None  # mixed include and exclude: not mechanical
        return OrderedDict([("is", [_scalar(p) for p in parts])])
    return OrderedDict([("is", _scalar(v))])


def _num(s: str):
    return float(s) if "." in s else int(s)


def _scalar(s: str):
    s = s.strip().strip('"')
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _filter_key_timeframe(key: str, groups: set[str]) -> str:
    if "." in key:
        v, fld = key.split(".", 1)
        return f"{v}.{timeframe_field_ref(fld, groups)}"
    return timeframe_field_ref(key, groups)


def translate_filters(filters, conv: Conversion, scope: str, name: str, field: str, lkml_file: str,
                      boolean_fields: set[str], construct: str = "measure_filter", groups: set[str] | None = None) -> tuple[OrderedDict | None, bool]:
    groups = groups or set()
    """lkml gives either a list of {field, value} dicts (legacy) or a list of single-key dicts.

    Returns (operator_dict, ok). ok is False when any expression could not be translated;
    the caller must then NOT emit the construct, because an unfiltered measure or an
    unfiltered topic silently changes the numbers.
    """
    if not filters:
        return None, True
    out: "OrderedDict[str, object]" = OrderedDict()
    ok = True
    for item in filters:
        if isinstance(item, dict) and "field" in item and "value" in item:
            fname, raw = item["field"], item["value"]
        elif isinstance(item, dict) and len(item) == 1:
            fname, raw = next(iter(item.items()))
        else:
            conv.note(scope=scope, name=name, field=field, construct=construct, cls="assisted",
                      reason=f"Unrecognised filter shape {item!r}; construct not emitted", lkml_file=lkml_file)
            ok = False
            continue
        op = translate_filter_value(raw, is_boolean_field=(fname.split(".")[-1] in boolean_fields))
        fname = _filter_key_timeframe(fname, groups)
        if op is None:
            conv.note(scope=scope, name=name, field=field, construct=construct, cls="assisted",
                      reason=f"Filter expression {raw!r} on {fname} has no mechanical Omni operator; construct not emitted, write the filter by hand",
                      lkml_file=lkml_file)
            ok = False
            continue
        out[fname] = op
    return (out or None), ok


# ---------------------------------------------------------------------------
# LookML loading
# ---------------------------------------------------------------------------

def load_lookml(root: Path) -> tuple[list, list]:
    if lkml is None:
        sys.exit("lkml is not installed: pip install lkml")
    views, explores = [], []
    files = sorted([*root.rglob("*.lkml"), *root.rglob("*.lookml")])
    for f in files:
        try:
            parsed = lkml.load(f.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"WARN  could not parse {f}: {exc}", file=sys.stderr)
            continue
        rel = str(f.relative_to(root))
        for v in parsed.get("views", []) or []:
            v["_file"] = rel
            views.append(v)
        for e in parsed.get("explores", []) or []:
            e["_file"] = rel
            explores.append(e)
    return merge_refinements(views), explores


def merge_refinements(views: list) -> list:
    """`view: +name { ... }` refinements are merged into their base view, field by field."""
    base: "OrderedDict[str, dict]" = OrderedDict()
    refinements = []
    for v in views:
        name = v.get("name", "")
        if name.startswith("+"):
            refinements.append(v)
        else:
            base[name] = v
    for r in refinements:
        target = r["name"][1:]
        if target not in base:
            continue
        b = base[target]
        b.setdefault("_refined_by", []).append(r.get("_file"))
        for key in ("dimensions", "dimension_groups", "measures", "filters", "parameters", "sets"):
            if key in r:
                existing = {f["name"]: f for f in b.get(key, [])}
                for f in r[key]:
                    existing[f["name"]] = {**existing.get(f["name"], {}), **f}
                b[key] = list(existing.values())
        for key, val in r.items():
            if key not in {"name", "dimensions", "dimension_groups", "measures", "filters", "parameters", "sets", "_file"}:
                b[key] = val
    return list(base.values())


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def split_table_name(raw: str) -> tuple[str | None, str | None]:
    s = raw.strip().rstrip(";").strip().strip("`").strip('"')
    s = s.replace("`", "").replace('"', "")
    parts = [p for p in s.split(".") if p]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    if len(parts) == 1:
        return None, parts[0]
    return None, None


def timeframe_field_ref(name: str, groups: set[str]) -> str:
    """created_month -> created[month] when `created` is a dimension group in scope; else unchanged."""
    m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*?)_(" + "|".join(TIMEFRAME_TOKENS) + r")", name)
    if m and m.group(1) in groups and TIMEFRAMES.get(m.group(2)):
        return f"{m.group(1)}[{TIMEFRAMES[m.group(2)]}]"
    return name


def expand_set_refs(fields: list, sets: dict, view: str, groups: set[str] | None = None) -> list:
    """Expand set references and qualify bare names; LookML timeframe fields become view.group[timeframe]."""
    out = []
    groups = groups or set()
    for f in fields:
        f = str(f)
        if f.endswith("*"):
            key = f[:-1]
            key = key.split(".")[-1]
            out.extend(expand_set_refs(sets.get(key, []), sets, view, groups))
        else:
            if "." in f:
                v, fld = f.split(".", 1)
                out.append(f"{v}.{timeframe_field_ref(fld, groups) if v == view else fld}")
            else:
                out.append(f"{view}.{timeframe_field_ref(f, groups)}")
    return out


CROSS_VIEW_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_][A-Za-z0-9_\[\]]*\}")


def cross_view_refs(sql: str | None, view: str) -> list[str]:
    """Views other than `view` referenced as ${other.field} in a field's SQL."""
    if not sql:
        return []
    return sorted({m for m in CROSS_VIEW_REF_RE.findall(sql) if m != view and m != "TABLE"})


def convert_view(v: dict, conv: Conversion, default_schema: str | None) -> None:
    name = v["name"]
    lk = v.get("_file", "")
    body: "OrderedDict[str, object]" = OrderedDict()
    schema = table = None

    if v.get("label"):
        body["label"] = v["label"]
    if v.get("description"):
        body["description"] = v["description"]

    derived = v.get("derived_table")
    if derived:
        if any(k in derived for k in PDT_KEYS):
            conv.note(scope="view", name=name, field=None, construct="pdt", cls="redesign",
                      reason="Persistent derived table: the plan rules dbt model or Omni query view; nothing emitted",
                      lkml_file=lk)
            conv.count("pdt", "redesign")
            return
        if "explore_source" in derived:
            conv.note(scope="view", name=name, field=None, construct="native_derived_table", cls="redesign",
                      reason="Native derived table (explore_source): rebuild as an Omni query view", lkml_file=lk)
            conv.count("native_derived_table", "redesign")
            return
        sql = derived.get("sql", "")
        if LIQUID_RE.search(sql):
            conv.note(scope="view", name=name, field=None, construct="derived_table_liquid", cls="redesign",
                      reason="Derived table SQL contains Liquid", lkml_file=lk)
            conv.count("derived_table", "redesign")
            return
        body["sql"] = translate_sql(sql, set())
        conv.count("derived_table", "mechanical")
        schema = default_schema
    elif v.get("sql_table_name"):
        raw = v["sql_table_name"]
        if LIQUID_RE.search(raw):
            conv.note(scope="view", name=name, field=None, construct="sql_table_name_liquid", cls="redesign",
                      reason="sql_table_name contains Liquid", lkml_file=lk)
            conv.count("sql_table_name", "redesign")
            schema = default_schema
        else:
            schema, table = split_table_name(raw)
            schema = schema or default_schema
            if table:
                body["schema"] = schema
                body["table_name"] = table
            conv.count("sql_table_name", "mechanical")
    else:
        schema = default_schema
        if not v.get("extends__all"):
            body["schema"] = schema
            body["table_name"] = name

    if v.get("extends__all"):
        bases = [b for group in v["extends__all"] for b in group]
        body["extends"] = bases
        conv.count("extends", "mechanical")
    if v.get("extension") == "required":
        body["template"] = True
    if v.get("required_access_grants"):
        body["required_access_grants"] = list(v["required_access_grants"])

    sets = {s["name"]: s.get("fields", []) for s in v.get("sets", []) or []}
    groups_in_view = {g["name"] for g in v.get("dimension_groups", []) or []}

    dims: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for d in v.get("dimensions", []) or []:
        res = convert_dimension(d, name, lk, conv, sets, groups_in_view)
        if res is not None:
            dims[d["name"]] = res
    for g in v.get("dimension_groups", []) or []:
        if g["name"] in dims:
            conv.note(scope="view", name=name, field=g["name"], construct="name_collision", cls="assisted",
                      reason="dimension_group name collides with a dimension of the same name; in Omni the group becomes one dimension, so rename one by hand. Group not emitted",
                      lkml_file=lk)
            continue
        res = convert_dimension_group(g, name, lk, conv, groups_in_view)
        if res is not None:
            dims[g["name"]] = res
    for f in v.get("filters", []) or []:
        conv.note(scope="view", name=name, field=f["name"], construct="filter_field", cls="redesign",
                  reason="Looker filter-only field: rebuild as an Omni dashboard control or templated filter", lkml_file=lk)
        conv.count("filter_field", "redesign")
    for p in v.get("parameters", []) or []:
        conv.note(scope="view", name=name, field=p["name"], construct="parameter", cls="redesign",
                  reason="Looker parameter: rebuild as an Omni templated filter or dashboard control", lkml_file=lk)
        conv.count("parameter", "redesign")

    boolean_fields = {d["name"] for d in v.get("dimensions", []) or [] if (d.get("type") or "") == "yesno"}
    measures: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for m in v.get("measures", []) or []:
        res = convert_measure(m, name, lk, conv, sets, groups_in_view, boolean_fields)
        if res is not None:
            measures[m["name"]] = res

    if dims:
        body["dimensions"] = dims
    if measures:
        body["measures"] = measures
    conv.views[name] = OrderedDict([("schema", schema), ("body", body), ("lkml_file", lk)])
    conv.count("view", "mechanical")


def common_field_props(f: dict, body: OrderedDict, view: str, lk: str, conv: Conversion, sets: dict,
                       groups: set[str] | None = None) -> None:
    groups = groups or set()
    others = cross_view_refs(f.get("sql"), view)
    if others:
        conv.note(scope="view", name=view, field=f["name"], construct="cross_view_reference", cls="assisted",
                  reason=f"sql references another view ({', '.join(others)}); confirm every topic that exposes this field joins it",
                  lkml_file=lk)
    if f.get("label"):
        body["label"] = f["label"]
    if f.get("description"):
        body["description"] = f["description"]
    if f.get("group_label"):
        body["group_label"] = f["group_label"]
    if f.get("view_label"):
        body["view_label"] = f["view_label"]
    if yes(f.get("hidden", "no")):
        body["hidden"] = True
    fmt = None
    if f.get("value_format_name"):
        fmt = VALUE_FORMAT_NAME.get(f["value_format_name"])
        if fmt is None:
            conv.note(scope="view", name=view, field=f["name"], construct="value_format_name", cls="assisted",
                      reason=f"value_format_name {f['value_format_name']!r} has no entry in property_mapping.md; choose an Omni format",
                      lkml_file=lk)
    elif f.get("value_format"):
        fmt = VALUE_FORMAT_STRING.get(f["value_format"].strip('"'))
        if fmt is None:
            conv.note(scope="view", name=view, field=f["name"], construct="value_format", cls="assisted",
                      reason=f"custom value_format {f['value_format']!r}; choose an Omni format", lkml_file=lk)
    if fmt:
        body["format"] = fmt
    if f.get("drill_fields"):
        body["drill_fields"] = expand_set_refs(f["drill_fields"], sets, view, groups)
    if f.get("required_access_grants"):
        body["required_access_grants"] = list(f["required_access_grants"])
    if f.get("suggestions"):
        body["suggestion_list"] = list(f["suggestions"])
    if f.get("suggest_dimension"):
        body["suggest_from_field"] = f["suggest_dimension"]
    if f.get("order_by_field"):
        body["order_by_field"] = f["order_by_field"]
    if f.get("links"):
        body["links"] = [OrderedDict([("label", l.get("label")), ("url", l.get("url"))]) for l in f["links"]]
        conv.note(scope="view", name=view, field=f["name"], construct="links", cls="assisted",
                  reason="Looker link URLs use Liquid tokens; confirm the Omni links syntax and Mustache tokens", lkml_file=lk)
    if f.get("html"):
        conv.note(scope="view", name=view, field=f["name"], construct="html", cls="redesign",
                  reason="html uses Liquid; Omni `markdown` uses Mustache; not emitted", lkml_file=lk)
        conv.count("html", "redesign")


def convert_dimension(d: dict, view: str, lk: str, conv: Conversion, sets: dict, groups: set[str]) -> OrderedDict | None:
    name, dtype, sql = d["name"], (d.get("type") or "string"), d.get("sql")
    body: "OrderedDict[str, object]" = OrderedDict()
    # Liquid in sql or label makes the whole field redesign. Liquid in html does not:
    # the dimension is still a plain column; only its html is withheld (common_field_props).
    for key in ("sql", "label"):
        if d.get(key) and LIQUID_RE.search(str(d[key])):
            conv.note(scope="view", name=view, field=name, construct="liquid", cls="redesign",
                      reason=f"Liquid in {key}; rebuild with Omni templated filters or Mustache", lkml_file=lk)
            conv.count("dimension", "redesign")
            return None
    if dtype in REDESIGN_DIMENSION_TYPES:
        conv.note(scope="view", name=view, field=name, construct=f"type_{dtype}", cls="redesign",
                  reason=f"dimension type {dtype} has no Omni equivalent", lkml_file=lk)
        conv.count("dimension", "redesign")
        return None
    if yes(d.get("primary_key", "no")):
        body["primary_key"] = True
    if dtype == "tier":
        if sql:
            body["sql"] = translate_sql(sql, groups)
        tiers = [_num(str(t)) for t in d.get("tiers", [])]
        body["bin_boundaries"] = tiers
        conv.count("dimension_tier", "mechanical")
    elif d.get("case"):
        groups_out = case_to_groups(d["case"])
        if groups_out is None:
            conv.note(scope="view", name=view, field=name, construct="case", cls="assisted",
                      reason="case dimension with non-equality conditions; write the Omni sql or groups by hand", lkml_file=lk)
            conv.count("dimension_case", "assisted")
            return None
        field_ref, grp, else_label = groups_out
        body["sql"] = translate_sql(field_ref, groups)
        body["groups"] = grp
        if else_label is not None:
            body["else"] = else_label
        conv.count("dimension_case", "assisted")
        conv.note(scope="view", name=view, field=name, construct="case", cls="assisted",
                  reason="case dimension emitted as Omni groups; confirm the labels and the else bucket", lkml_file=lk)
    else:
        if not is_plain_column(sql, name):
            body["sql"] = translate_sql(sql, groups)
        conv.count("dimension", "mechanical")
    common_field_props(d, body, view, lk, conv, sets, groups)
    return body


def case_to_groups(case: dict):
    """LookML case { when: { sql: ${x} = 'a' ;; label: "A" } else: "Other" } -> (field_ref, groups, else)."""
    whens = case.get("whens") or case.get("when") or []
    if isinstance(whens, dict):
        whens = [whens]
    field_ref = None
    groups = []
    for w in whens:
        sql = str(w.get("sql", "")).strip().rstrip(";").strip()
        m = re.fullmatch(r"(\$\{[A-Za-z_][A-Za-z0-9_.]*\})\s*(?:=\s*['\"]([^'\"]*)['\"]|IN\s*\((.*)\))", sql, re.I)
        if not m:
            return None
        ref = m.group(1)
        if field_ref is None:
            field_ref = ref
        elif field_ref != ref:
            return None
        if m.group(2) is not None:
            values = [m.group(2)]
        else:
            values = [x.strip().strip("'\"") for x in m.group(3).split(",")]
        groups.append(OrderedDict([("filter", OrderedDict([("is", values)])), ("name", w.get("label"))]))
    if field_ref is None:
        return None
    return field_ref, groups, case.get("else")


def convert_dimension_group(g: dict, view: str, lk: str, conv: Conversion, groups: set[str]) -> OrderedDict | None:
    name, gtype = g["name"], g.get("type", "time")
    body: "OrderedDict[str, object]" = OrderedDict()
    for key in ("sql", "sql_start", "sql_end", "label"):
        if g.get(key) and LIQUID_RE.search(str(g[key])):
            conv.note(scope="view", name=view, field=name, construct="liquid", cls="redesign",
                      reason=f"Liquid in {key}", lkml_file=lk)
            conv.count("dimension_group", "redesign")
            return None
    if gtype == "time":
        sql = g.get("sql")
        if not is_plain_column(sql, name):
            body["sql"] = translate_sql(sql, groups) if sql else None
            if body["sql"] is None:
                del body["sql"]
        tfs = []
        for tf in g.get("timeframes", []) or ["raw", "date", "week", "month", "quarter", "year"]:
            if tf not in TIMEFRAMES:
                conv.note(scope="view", name=view, field=name, construct="timeframe", cls="assisted",
                          reason=f"timeframe {tf!r} has no Omni equivalent; dropped from the list", lkml_file=lk)
                continue
            mapped = TIMEFRAMES[tf]
            if mapped and mapped not in tfs:
                tfs.append(mapped)
        body["timeframes"] = tfs
        if str(g.get("convert_tz", "yes")).lower() == "no":
            body["convert_tz"] = False
        conv.count("dimension_group_time", "mechanical")
    elif gtype == "duration":
        body["duration"] = OrderedDict([
            ("start", translate_sql(g.get("sql_start", ""), groups)),
            ("end", translate_sql(g.get("sql_end", ""), groups)),
            ("intervals", list(g.get("intervals", []) or ["day"])),
        ])
        conv.note(scope="view", name=view, field=name, construct="dimension_group_duration", cls="assisted",
                  reason="duration group emitted as Omni `duration`; confirm the parameter shape against the Omni docs", lkml_file=lk)
        conv.count("dimension_group_duration", "assisted")
    else:
        conv.note(scope="view", name=view, field=name, construct="dimension_group", cls="redesign",
                  reason=f"dimension_group type {gtype!r} not supported", lkml_file=lk)
        conv.count("dimension_group", "redesign")
        return None
    common_field_props(g, body, view, lk, conv, {}, groups)
    return body


def convert_measure(m: dict, view: str, lk: str, conv: Conversion, sets: dict, groups: set[str],
                    boolean_fields: set[str]) -> OrderedDict | None:
    name, mtype, sql = m["name"], (m.get("type") or "count"), m.get("sql")
    body: "OrderedDict[str, object]" = OrderedDict()
    for key in ("sql", "label"):
        if m.get(key) and LIQUID_RE.search(str(m[key])):
            conv.note(scope="view", name=view, field=name, construct="liquid", cls="redesign",
                      reason=f"Liquid in {key}", lkml_file=lk)
            conv.count("measure", "redesign")
            return None
    if mtype in REDESIGN_MEASURE_TYPES:
        conv.note(scope="view", name=view, field=name, construct=f"measure_type_{mtype}", cls="redesign",
                  reason=f"measure type {mtype}: Omni does this as a table calculation or a query-view measure", lkml_file=lk)
        conv.count("measure", "redesign")
        return None
    if mtype == "number":
        if sql:
            body["sql"] = translate_sql(sql, groups)
        conv.note(scope="view", name=view, field=name, construct="measure_number", cls="assisted",
                  reason="derived measure (type: number) emitted without aggregate_type; validate it resolves on the branch", lkml_file=lk)
        conv.count("measure_number", "assisted")
    elif mtype in AGGREGATES:
        if sql:
            body["sql"] = translate_sql(sql, groups)
        body["aggregate_type"] = AGGREGATES[mtype]
        if mtype.startswith("percentile") and m.get("percentile") is not None:
            body["percentile"] = _num(str(m["percentile"]))
        if mtype.endswith("_distinct") and m.get("sql_distinct_key"):
            body["custom_primary_key_sql"] = translate_sql(m["sql_distinct_key"], groups)
        conv.count("measure", "mechanical")
    else:
        conv.note(scope="view", name=view, field=name, construct=f"measure_type_{mtype}", cls="redesign",
                  reason=f"measure type {mtype!r} not supported", lkml_file=lk)
        conv.count("measure", "redesign")
        return None
    filters = m.get("filters__all") or m.get("filters")
    if filters:
        flat = []
        for item in filters:
            flat.extend(item if isinstance(item, list) else [item])
        fo, ok = translate_filters(flat, conv, "view", view, name, lk, boolean_fields, groups=groups)
        if not ok:
            conv.count("measure", "assisted")
            return None
        if fo:
            body["filters"] = fo
    common_field_props(m, body, view, lk, conv, sets, groups)
    return body


# ---------------------------------------------------------------------------
# Explores -> topics and relationships
# ---------------------------------------------------------------------------

def convert_explore(e: dict, conv: Conversion, known_views: set[str]) -> None:
    name, lk = e["name"], e.get("_file", "")
    base_view = e.get("from") or e.get("view_name") or name
    topic: "OrderedDict[str, object]" = OrderedDict()
    topic["base_view"] = base_view
    if e.get("label"):
        topic["label"] = e["label"]
    if e.get("description"):
        topic["description"] = e["description"]
    if e.get("group_label"):
        topic["group_label"] = e["group_label"]
    if yes(e.get("hidden", "no")):
        topic["hidden"] = True
    if e.get("extends__all"):
        topic["extends"] = [b for group in e["extends__all"] for b in group]

    explore_view_names = [base_view] + [j["name"] for j in (e.get("joins", []) or [])]
    if e.get("fields"):
        fields_out: list[str] = []
        for f in e["fields"]:
            f = str(f)
            if f.startswith("ALL_FIELDS"):
                fields_out.extend(f"{vn}.*" for vn in explore_view_names if f"{vn}.*" not in fields_out)
            elif f.endswith("*"):
                fields_out.append(f)  # a view-scoped set reference such as users.detail*; expanded by hand
                conv.note(scope="explore", name=name, field=f, construct="fields_set_ref", cls="assisted",
                          reason="set reference in explore fields; expand to view.field entries by hand", lkml_file=lk)
            else:
                fields_out.append(f)
        topic["fields"] = fields_out

    if e.get("sql_always_where"):
        sql = e["sql_always_where"]
        if LIQUID_RE.search(sql):
            conv.note(scope="explore", name=name, field=None, construct="sql_always_where_liquid", cls="redesign",
                      reason="sql_always_where contains Liquid", lkml_file=lk)
        else:
            topic["always_where_sql"] = translate_sql(sql, set())
            conv.note(scope="explore", name=name, field=None, construct="sql_always_where", cls="assisted",
                      reason="emitted as always_where_sql; confirm field references resolve on the topic", lkml_file=lk)
    if e.get("always_filter") or e.get("conditionally_filter"):
        src = e.get("always_filter") or e.get("conditionally_filter")
        flt = src.get("filters__all") or src.get("filters") or []
        flat = []
        for item in flt:
            flat.extend(item if isinstance(item, list) else [item])
        fo, ok = translate_filters(flat, conv, "explore", name, "(topic)", lk, set(), construct="always_filter")
        if ok and fo:
            topic["default_filters"] = fo
            conv.note(scope="explore", name=name, field=None, construct="always_filter", cls="assisted",
                      reason="emitted as default_filters (user-removable); use always_where_filters if it must not be removable", lkml_file=lk)
    if e.get("access_filter"):
        afs = e["access_filter"] if isinstance(e["access_filter"], list) else [e["access_filter"]]
        topic["access_filters"] = [OrderedDict([("field", a.get("field")), ("user_attribute", a.get("user_attribute"))]) for a in afs]
        conv.note(scope="explore", name=name, field=None, construct="access_filter", cls="assisted",
                  reason="emitted as access_filters; confirm the user attributes exist in Omni (omni-target-setup)", lkml_file=lk)

    join_tree: "OrderedDict[str, OrderedDict]" = OrderedDict()
    parent_of: dict[str, str] = {}
    topic_rels: list = []
    explore_views = {base_view}
    for j in e.get("joins", []) or []:
        explore_views.add(j["name"])
    for j in e.get("joins", []) or []:
        jname = j["name"]
        sql_on = j.get("sql_on")
        if not sql_on or LIQUID_RE.search(sql_on):
            conv.note(scope="explore", name=name, field=jname, construct="join", cls="redesign",
                      reason="join without sql_on, or sql_on contains Liquid; not emitted", lkml_file=lk)
            conv.count("join", "redesign")
            continue
        on_sql = translate_sql(sql_on, set())
        refs = re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\.", on_sql)
        from_view = next((r for r in refs if r != jname and r in explore_views), base_view)
        rel_raw = j.get("relationship", "many_to_one")
        jtype_raw = j.get("type", "left_outer")
        rel = OrderedDict()
        # `join: alias { from: v }` is Omni's join_to_view_as: the relationship targets the real
        # view and names the alias; on_sql and the topic's joins use the alias. Kept topic-scoped
        # so alias names cannot collide across topics.
        aliased = bool(j.get("from")) and j["from"] != jname
        rel["join_from_view"] = from_view
        rel["join_to_view"] = j["from"] if aliased else jname
        if aliased:
            rel["join_to_view_as"] = jname
        rel["on_sql"] = on_sql
        if rel_raw in RELATIONSHIPS:
            rel["relationship_type"] = RELATIONSHIPS[rel_raw]
            conv.count("join", "mechanical")
        else:
            conv.note(scope="explore", name=name, field=jname, construct=f"join_{rel_raw}", cls="redesign",
                      reason=f"relationship {rel_raw!r} has no Omni relationship_type; not emitted", lkml_file=lk)
            conv.count("join", "redesign")
            continue
        if jtype_raw in JOIN_TYPES:
            rel["join_type"] = JOIN_TYPES[jtype_raw]
        else:
            conv.note(scope="explore", name=name, field=jname, construct="join_type", cls="redesign",
                      reason=f"join type {jtype_raw!r} has no Omni join_type", lkml_file=lk)
            continue
        if j.get("sql_where"):
            conv.note(scope="explore", name=name, field=jname, construct="join_sql_where", cls="assisted",
                      reason="join sql_where has no direct Omni equivalent; fold into on_sql or a topic filter", lkml_file=lk)
        if aliased:
            topic_rels.append(rel)
        else:
            if rel not in conv.relationships:
                conv.relationships.append(rel)
        parent_of[jname] = from_view

    for jname, parent in parent_of.items():
        node = _tree_node(join_tree, parent, base_view, parent_of)
        node.setdefault(jname, OrderedDict())
    if join_tree:
        topic["joins"] = join_tree
    if topic_rels:
        topic["relationships"] = topic_rels
    conv.topics[name] = OrderedDict([("body", topic), ("lkml_file", lk)])
    conv.count("explore", "mechanical")


def _tree_node(tree: OrderedDict, view: str, base: str, parent_of: dict) -> OrderedDict:
    if view == base:
        return tree
    path = []
    cur = view
    while cur != base and cur in parent_of:
        path.append(cur)
        cur = parent_of[cur]
    node = tree
    for step in reversed(path):
        node = node.setdefault(step, OrderedDict())
    return node


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------

class _Dumper(yaml.SafeDumper):
    pass


def _represent_ordereddict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


def _represent_none(dumper, _):
    return dumper.represent_scalar("tag:yaml.org,2002:null", "null")


_Dumper.add_representer(OrderedDict, _represent_ordereddict)
_Dumper.add_representer(type(None), _represent_none)


def dump_yaml(obj) -> str:
    return yaml.dump(obj, Dumper=_Dumper, sort_keys=False, allow_unicode=True, default_flow_style=False, width=1000)


def convert(lookml_dir: Path, views_filter: set[str] | None, explores_filter: set[str] | None,
            default_schema: str | None, overrides_dir: Path | None, project: str = "lookml") -> Conversion:
    apply_overrides(overrides_dir)
    views, explores = load_lookml(lookml_dir)
    conv = Conversion(project=project)
    conv.raw_views = [v for v in views if not views_filter or v["name"] in views_filter]
    conv.raw_explores = [e for e in explores if not explores_filter or e["name"] in explores_filter]
    for v in sorted(views, key=lambda x: x.get("name", "")):
        if views_filter and v["name"] not in views_filter:
            continue
        convert_view(v, conv, default_schema)
    known = set(conv.views.keys())
    for e in sorted(explores, key=lambda x: x.get("name", "")):
        if explores_filter and e["name"] not in explores_filter:
            continue
        convert_explore(e, conv, known)
    conv.needs_human.sort(key=lambda n: (n["scope"], n["name"], n["field"] or "", n["construct"], n["reason"]))
    return conv


def apply_overrides(overrides_dir: Path | None) -> None:
    """Optional engagement overrides: <dir>/property_mapping.yml with value_format_name / value_format / timeframes maps."""
    if not overrides_dir:
        return
    f = overrides_dir / "property_mapping.yml"
    if not f.exists():
        return
    data = yaml.safe_load(f.read_text()) or {}
    VALUE_FORMAT_NAME.update(data.get("value_format_name", {}) or {})
    VALUE_FORMAT_STRING.update(data.get("value_format", {}) or {})
    TIMEFRAMES.update(data.get("timeframes", {}) or {})



# ---------------------------------------------------------------------------
# Intermediate representation and dependency graph (persisted with the emitted model)
# ---------------------------------------------------------------------------

FIELD_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?(?:\[[a-z_]+\])?\}")


def identity(conv: Conversion, kind: str, *parts: str) -> str:
    return "looker:" + conv.project + ":" + kind + ":" + ":".join(parts)


def _field_refs(sql: str | None, view: str) -> list[str]:
    """Fields referenced as ${x} or ${v.x} in SQL, as view.field, excluding ${TABLE}."""
    if not sql:
        return []
    out = []
    for m in FIELD_REF_RE.finditer(sql):
        a, b = m.group(1), m.group(2)
        if a == "TABLE":
            continue
        ref = f"{a}.{b}" if b else f"{view}.{a}"
        if ref not in out:
            out.append(ref)
    return out


def build_ir(conv: Conversion) -> tuple[OrderedDict, OrderedDict, list]:
    """Typed IR per view and topic, plus dependency edges. Every field keeps its source
    location, its class and its unsupported constructs; nothing disappears into a guess."""
    notes_by = {}
    for n in conv.needs_human:
        notes_by.setdefault((n["scope"], n["name"], n["field"]), []).append(n)
    views_ir: "OrderedDict[str, OrderedDict]" = OrderedDict()
    edges: list = []

    def edge(src: str, dst: str, kind: str) -> None:
        e = OrderedDict([("from", src), ("to", dst), ("kind", kind)])
        if e not in edges:
            edges.append(e)

    for v in sorted(conv.raw_views, key=lambda x: x["name"]):
        name = v["name"]
        emitted = conv.views.get(name)
        body = emitted["body"] if emitted else {}
        vid = identity(conv, "view", name)
        view_notes = notes_by.get(("view", name, None), [])
        fields = []
        for kind, coll in (("dimension", "dimensions"), ("dimension_group", "dimension_groups"), ("measure", "measures"), ("filter", "filters"), ("parameter", "parameters")):
            for f in v.get(coll, []) or []:
                fname = f["name"]
                section = "measures" if kind == "measure" else "dimensions"
                omni = body.get(section, {}).get(fname) if body else None
                fnotes = notes_by.get(("view", name, fname), [])
                if omni is not None and not fnotes:
                    cls = "mechanical"
                elif omni is not None:
                    cls = "assisted"
                else:
                    cls = max((n["class"] for n in fnotes), key=lambda c: ["mechanical", "assisted", "redesign"].index(c), default="redesign")
                sql = f.get("sql") or f.get("sql_start")
                refs = _field_refs(sql, name) + _field_refs(f.get("sql_end"), name)
                fid = identity(conv, "field", name, fname)
                edge(vid, fid, "contains")
                for r in refs:
                    rv, rf = r.split(".", 1)
                    edge(fid, identity(conv, "field", rv, rf), "references")
                fields.append(OrderedDict([
                    ("identity", fid), ("name", fname), ("kind", kind),
                    ("lookml_type", f.get("type")),
                    ("source_sql", sql.strip().rstrip(";").strip() if isinstance(sql, str) else None),
                    ("references", refs),
                    ("class", cls),
                    ("emitted", omni is not None),
                    ("omni", omni),
                    ("unsupported", [OrderedDict([("construct", n["construct"]), ("class", n["class"]), ("reason", n["reason"])]) for n in fnotes]),
                    ("source", OrderedDict([("file", v.get("_file")), ("view", name)])),
                ]))
        views_ir[name] = OrderedDict([
            ("identity", vid), ("name", name),
            ("schema", emitted["schema"] if emitted else None),
            ("table_name", (body.get("table_name") if body else None)),
            ("emitted", emitted is not None),
            ("class", "mechanical" if emitted and not view_notes else ("assisted" if emitted else (view_notes[0]["class"] if view_notes else "redesign"))),
            ("unsupported", [OrderedDict([("construct", n["construct"]), ("class", n["class"]), ("reason", n["reason"])]) for n in view_notes]),
            ("source", OrderedDict([("file", v.get("_file")), ("refined_by", v.get("_refined_by", []))])),
            ("fields", fields),
        ])

    topics_ir: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for e in sorted(conv.raw_explores, key=lambda x: x["name"]):
        name = e["name"]
        emitted = conv.topics.get(name)
        body = emitted["body"] if emitted else {}
        tid = identity(conv, "topic", name)
        base = body.get("base_view") if body else (e.get("from") or e.get("view_name") or name)
        edge(tid, identity(conv, "view", base), "base_view")
        joins = []
        for j in e.get("joins", []) or []:
            jname = j["name"]
            jview = j.get("from") or jname
            edge(tid, identity(conv, "view", jview), "joins")
            for r in _field_refs(j.get("sql_on"), base):
                rv, rf = r.split(".", 1)
                edge(tid, identity(conv, "field", (jview if rv == jname else rv), rf), "join_on")
            jnotes = notes_by.get(("explore", name, jname), [])
            joins.append(OrderedDict([
                ("name", jname), ("view", jview), ("alias", jname if jview != jname else None),
                ("relationship", j.get("relationship", "many_to_one")), ("type", j.get("type", "left_outer")),
                ("on_sql", (j.get("sql_on") or "").strip()),
                ("emitted", not any(n["class"] == "redesign" for n in jnotes)),
                ("unsupported", [OrderedDict([("construct", n["construct"]), ("class", n["class"]), ("reason", n["reason"])]) for n in jnotes]),
            ]))
        tnotes = notes_by.get(("explore", name, None), []) + notes_by.get(("explore", name, "(topic)"), [])
        topics_ir[name] = OrderedDict([
            ("identity", tid), ("name", name), ("base_view", base),
            ("emitted", emitted is not None),
            ("fields", body.get("fields") if body else None),
            ("joins", joins),
            ("unsupported", [OrderedDict([("construct", n["construct"]), ("class", n["class"]), ("reason", n["reason"])]) for n in tnotes]),
            ("source", OrderedDict([("file", e.get("_file"))])),
        ])
    edges.sort(key=lambda d: (d["kind"], d["from"], d["to"]))
    return views_ir, topics_ir, edges


def write_output(conv: Conversion, out: Path, report: Path | None, default_schema: str | None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for vname, rec in conv.views.items():
        schema = rec["schema"] or default_schema or "_unresolved"
        d = out / schema
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{vname}.view").write_text(dump_yaml(rec["body"]), encoding="utf-8")
    for tname, rec in conv.topics.items():
        (out / f"{tname}.topic").write_text(dump_yaml(rec["body"]), encoding="utf-8")
    if conv.relationships:
        (out / "relationships.yaml").write_text(dump_yaml(conv.relationships), encoding="utf-8")
    report = report or (out / "needs_human.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(conv.needs_human, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = OrderedDict([
        ("converter_version", CONVERTER_VERSION),
        ("project", conv.project),
        ("views_emitted", len(conv.views)),
        ("topics_emitted", len(conv.topics)),
        ("relationships_emitted", len(conv.relationships)),
        ("needs_human", len(conv.needs_human)),
        ("needs_human_by_class", _by_class(conv.needs_human)),
        ("constructs", OrderedDict(sorted((k, OrderedDict(sorted(v.items()))) for k, v in conv.counts.items()))),
    ])
    (out / "conversion_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    views_ir, topics_ir, edges = build_ir(conv)
    (out / "ir" / "views").mkdir(parents=True, exist_ok=True)
    (out / "ir" / "topics").mkdir(parents=True, exist_ok=True)
    for name, rec in views_ir.items():
        (out / "ir" / "views" / f"{name}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, rec in topics_ir.items():
        (out / "ir" / "topics" / f"{name}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "dependencies.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in edges), encoding="utf-8")


def _by_class(items: list) -> OrderedDict:
    out: "OrderedDict[str, int]" = OrderedDict()
    for cls in ("mechanical", "assisted", "redesign", "drop"):
        n = sum(1 for i in items if i["class"] == cls)
        if n:
            out[cls] = n
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lookml", required=True, type=Path, help="LookML project directory")
    ap.add_argument("--out", required=True, type=Path, help="Output directory (Omni model layout)")
    ap.add_argument("--views", default="", help="Comma-separated view names to convert (default: all)")
    ap.add_argument("--explores", default="", help="Comma-separated explore names to convert (default: all)")
    ap.add_argument("--overrides", type=Path, default=None, help="Engagement override directory (property_mapping.yml)")
    ap.add_argument("--report", type=Path, default=None, help="Path for needs_human.json (default: <out>/needs_human.json)")
    ap.add_argument("--default-schema", default=None, help="Schema for views whose sql_table_name has none")
    ap.add_argument("--project", default="lookml", help="LookML project name used in identities (looker:<project>:view:<name>)")
    args = ap.parse_args(argv)
    conv = convert(
        args.lookml,
        {v for v in args.views.split(",") if v} or None,
        {e for e in args.explores.split(",") if e} or None,
        args.default_schema,
        args.overrides,
        project=args.project,
    )
    write_output(conv, args.out, args.report, args.default_schema)
    print(f"views {len(conv.views)}  topics {len(conv.topics)}  relationships {len(conv.relationships)}  needs_human {len(conv.needs_human)}  ir {len(conv.raw_views)} views / {len(conv.raw_explores)} topics")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
dbt Charts board scaffold for a dbt project's warehouse layer (Wire `dbtcharts` artifact).

Deterministic: the same manifest and catalog produce byte-identical boards. No AI call,
no warehouse call. It reads dbt's own artifacts (target/manifest.json and, when present,
target/catalog.json), groups the warehouse-layer models by subject area (the folder each
model sits in), classifies each model and its columns from Wire's dbt naming conventions
(`_fact`/`_dim`/`_xa`, `_dt`/`_ts`, `_amount`, `_pk`/`_fk`, `is_`/`has_`), and writes one
dbt Charts board per subject area under charts/. The agent running
/wire:dbtcharts-generate does the judgement this script cannot: which of the proposed
charts matter, titles that read as business language, and what to do with each
needs_human item. The agent never hand-writes what this script emits.

Usage:
    python3 wire/scripts/dbtcharts_scaffold.py --manifest target/manifest.json --out charts
        [--catalog target/catalog.json] [--layer-path models/warehouse]
        [--subject-area w_sales,w_crm] [--dialect bigquery|snowflake|postgres|duckdb]
        [--source-name warehouse] [--write-anchor dbt_charts.yml --profile NAME --target prod]
        [--theme vivid] [--currency £] [--title "Client Warehouse"] [--logo path/to/logo.svg]
        [--trend-months 24] [--breakdown-limit 10] [--kpi-row-height 120] [--frame-width 1440]
        [--include-other]

    The presentation flags take their values from the resolved design convention
    (.wire/conventions/dbtcharts.yml in the engagement, else wire/conventions/dbtcharts.yml);
    /wire:dbtcharts-generate reads the convention and passes them. The script stays stdlib-only.

Output layout:
    <out>/<subject_area>.yml          one board per subject area (the warehouse folder, `w_`/`wh_` stripped)
    <out>/meta.yml                    project-wide defaults every board inherits (theme, frame width); written only when absent
    <out>/index.yml                   the landing page dct serves at /: one card per board, optional logo; written only when absent
    <out>/scaffold_summary.json       boards, models, the columns chosen for each, chart counts, converter version
    <out>/needs_human.json            every model the script did not chart, or charted with a gap, and why
    <anchor path>                     dbt_charts.yml with a dbt_profile source; written only when absent

Board shape (dbt Charts language, see `dct docs cheatsheet`):
    - every query is SQL over {{ ref('<model>') }} so `dct validate` checks the model name
      against the manifest and `dct validate --warehouse` dry-runs it
    - a fact gets a KPI row (record count plus up to three measures, each with a number format),
      a monthly trend of its first measure over the last 24 months, and a top-10 breakdown by its
      first categorical column
    - a dimension gets a record-count KPI and a breakdown by its first categorical column
    - a subject area's board covers the facts in its folder plus the dimensions they join to,
      wherever those sit: a dimension the fact `ref()`s (manifest depends_on) or whose `<x>_pk`
      matches a fact `<x>_fk` column. `--subject-area w_sales` therefore charts the sales facts
      and, say, wh_companies_dim from w_crm; the summary marks each linked dimension with the
      fact and the link that brought it in
    - money measures (`_amount`, `_revenue`, `_cost`, `_price`, `_value`, `_spend`) are formatted
      with `--currency`: `$` uses dbt Charts' currency presets; any other symbol becomes a KPI/table
      prefix, and chart axes fall back to plain compact numbers because axis tick formats cannot
      carry a non-dollar symbol (dct 0.8)
    - trends set `style.axis_x.time_unit: yearmonth` and `style.axis_y.position: left`
    - every query and chart carries `notes:`; every KPI has `label:`; every other chart `title:`
    - `type: values` (inline data) is never emitted: a scaffolded board reads the warehouse
    - the theme is set once in `<out>/meta.yml`, never per board; `dbt_charts.yml` holds only
      the sources registry (a `serve:` key is rejected by dct 0.8)

Requires: Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Classification rules. Order inside each tuple is priority order.
# ---------------------------------------------------------------------------
FACT_PATTERNS = (r"_fact$", r"_fact_", r"^fct_", r"_fct$", r"_xa$", r"^mart_", r"_mart$")
DIM_PATTERNS = (r"_dim$", r"^dim_", r"_dim_")

KEY_SUFFIXES = ("_pk", "_fk", "_id", "_key", "_hash", "_sk")
MONEY_SUFFIXES = ("_amount", "_revenue", "_cost", "_price", "_value", "_spend", "_gbp", "_usd", "_eur")
TREND_MONTHS = 24          # default; --trend-months (conventions windows.trend_months)
KPI_ROW_HEIGHT = 120       # default; --kpi-row-height (conventions board_shape.kpi_row_height)
NUMERIC_TYPES = {
    "INT64", "INTEGER", "INT", "SMALLINT", "BIGINT", "TINYINT", "FLOAT64", "FLOAT", "DOUBLE",
    "REAL", "NUMERIC", "BIGNUMERIC", "DECIMAL", "NUMBER", "DOUBLE PRECISION",
}
DATE_TYPES = {"DATE"}
TIMESTAMP_TYPES = {"DATETIME", "TIMESTAMP", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ", "TIMESTAMP_TZ",
                   "TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP WITH TIME ZONE"}
STRING_TYPES = {"STRING", "VARCHAR", "TEXT", "CHAR", "CHARACTER VARYING", "NVARCHAR"}
BOOL_TYPES = {"BOOL", "BOOLEAN"}

NUMERIC_SUFFIXES = ("_amount", "_revenue", "_cost", "_price", "_value", "_total", "_count",
                    "_qty", "_quantity", "_num", "_hours", "_days", "_duration", "_score",
                    "_rate", "_pct", "_percent", "_ratio", "_avg", "_sum", "_points", "_minutes",
                    "_seconds", "_size", "_length")
DATE_SUFFIXES = ("_dt", "_date")
TIMESTAMP_SUFFIXES = ("_ts", "_timestamp", "_at")
BOOL_PREFIXES = ("is_", "has_", "was_")

# Measure priority: lower tier first. A column matches the first tier whose suffix it ends with.
MEASURE_TIERS = (
    ("_amount",),
    ("_revenue", "_cost", "_price", "_value", "_total"),
    ("_count", "_qty", "_quantity", "_num"),
    ("_hours", "_days", "_duration", "_minutes", "_seconds"),
)
AVERAGE_SUFFIXES = ("_rate", "_pct", "_percent", "_ratio", "_avg", "_score")

# Date priority: tier by suffix, then by the business word the name carries.
DATE_TIERS = (("_dt",), ("_date",), ("date", "day", "_day", "_month", "_week"), ("_ts", "_timestamp", "_at"))
DATE_WORDS = ("created", "transaction", "invoice", "order", "event", "start", "closed", "sent", "session", "activity")

# Breakdown dimension priority.
DIMENSION_TIERS = (
    ("_status",), ("_type",), ("_stage",), ("_category",), ("_source", "_channel"),
    ("_region", "_country", "_territory"), ("_segment", "_tier", "_priority", "_industry"),
)
DIMENSION_EXCLUDE_SUFFIXES = ("_url", "_email", "_description", "_text", "_notes", "_body",
                              "_json", "_html", "_phone", "_address", "_uuid", "_guid")
NAME_SUFFIX = "_name"

MAX_KPI_MEASURES = 3
BREAKDOWN_LIMIT = 10


def die(msg: str) -> None:
    sys.stderr.write(f"dbtcharts_scaffold: {msg}\n")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Reading dbt artifacts
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"{path} not found")
    except json.JSONDecodeError as exc:
        die(f"{path} is not valid JSON: {exc}")
    return {}


def model_nodes(manifest: dict, layer_path: str) -> list[dict]:
    """Enabled, non-ephemeral models whose original_file_path starts with layer_path."""
    prefix = layer_path.rstrip("/") + "/"
    out = []
    for uid, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue
        cfg = node.get("config", {}) or {}
        if cfg.get("enabled") is False or cfg.get("materialized") == "ephemeral":
            continue
        ofp = node.get("original_file_path", "") or ""
        if not ofp.startswith(prefix):
            continue
        out.append({"unique_id": uid, "name": node["name"], "path": ofp,
                    "description": (node.get("description") or "").strip(),
                    "manifest_columns": node.get("columns", {}) or {},
                    "depends_on": list((node.get("depends_on", {}) or {}).get("nodes", []) or [])})
    out.sort(key=lambda n: (n["path"], n["name"]))
    return out


def subject_area_of(node: dict, layer_path: str) -> str:
    """The folder directly under the layer path, else the `wh_<group>__` name prefix, else the layer folder."""
    prefix = layer_path.rstrip("/") + "/"
    rest = node["path"][len(prefix):]
    parts = rest.split("/")
    if len(parts) > 1:
        return parts[0]
    m = re.match(r"^(?:wh|w)_([a-z0-9]+)__", node["name"])
    if m:
        return m.group(1)
    return Path(layer_path.rstrip("/")).name


def slug_of(subject_area: str) -> str:
    s = re.sub(r"^(wh_|w_)", "", subject_area)
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s or "warehouse"


def label_of(identifier: str) -> str:
    s = re.sub(r"^(wh_[a-z0-9]+__|wh_|w_|fct_|dim_|mart_)", "", identifier)
    s = re.sub(r"(_fact|_dim|_xa|_fct)$", "", s)
    return " ".join(w.capitalize() for w in s.replace("__", "_").split("_") if w) or identifier


def catalog_columns(catalog: dict | None, unique_id: str) -> "OrderedDict[str, str]":
    """Column name -> upper-cased type, in catalog (warehouse) order."""
    cols: "OrderedDict[str, str]" = OrderedDict()
    if not catalog:
        return cols
    node = (catalog.get("nodes", {}) or {}).get(unique_id)
    if not node:
        return cols
    for name, meta in sorted((node.get("columns") or {}).items(), key=lambda kv: kv[1].get("index", 0)):
        cols[name] = str(meta.get("type", "")).upper()
    return cols


def merged_columns(node: dict, catalog: dict | None) -> "list[tuple[str, str | None]]":
    """[(column_name, type_or_None)] — catalog order first, then manifest-only columns in schema.yml order."""
    cat = catalog_columns(catalog, node["unique_id"])
    out: "list[tuple[str, str | None]]" = [(n, t or None) for n, t in cat.items()]
    seen = set(cat)
    for name, meta in node["manifest_columns"].items():
        if name in seen:
            continue
        dt = (meta.get("data_type") or "").upper() or None
        out.append((name, dt))
    return out


# ---------------------------------------------------------------------------
# Column classification
# ---------------------------------------------------------------------------
def classify_column(name: str, dtype: str | None) -> str:
    """One of key, boolean, date, timestamp, numeric, string, unknown."""
    lname = name.lower()
    if lname.startswith("_"):
        return "key"
    if "." in lname:
        # A nested (STRUCT / RECORD) field as the catalog lists it. Charting one needs an
        # alias and a judgement about the parent; left to the agent.
        return "nested"
    if lname.endswith(KEY_SUFFIXES) or lname in ("id", "pk", "fk"):
        return "key"
    if lname.startswith(BOOL_PREFIXES):
        # Wire convention: is_/has_/was_ is a flag whatever the warehouse type says.
        return "boolean"
    if dtype:
        base = dtype.split("(")[0].strip().upper()
        if base in BOOL_TYPES:
            return "boolean"
        if base in DATE_TYPES:
            return "date"
        if base in TIMESTAMP_TYPES:
            return "timestamp"
        if base in NUMERIC_TYPES:
            return "numeric"
        if base in STRING_TYPES:
            return "string"
        return "unknown"
    if lname.endswith(DATE_SUFFIXES) or lname in ("date", "day"):
        return "date"
    if lname.endswith(TIMESTAMP_SUFFIXES):
        return "timestamp"
    if lname.endswith(NUMERIC_SUFFIXES):
        return "numeric"
    if lname.endswith(NAME_SUFFIX) or lname.endswith(("_status", "_type", "_stage", "_category",
                                                       "_source", "_channel", "_region", "_country",
                                                       "_segment", "_tier", "_priority", "_industry")):
        return "string"
    return "unknown"


def tier_index(lname: str, tiers) -> int:
    for i, suffixes in enumerate(tiers):
        for s in suffixes:
            if lname.endswith(s) or lname == s.lstrip("_"):
                return i
    return len(tiers)


def word_index(lname: str, words) -> int:
    for i, w in enumerate(words):
        if w in lname:
            return i
    return len(words)


def pick_date(columns: "list[tuple[str, str | None]]") -> "tuple[str, str] | None":
    cands = []
    for pos, (name, dtype) in enumerate(columns):
        cls = classify_column(name, dtype)
        if cls in ("date", "timestamp"):
            ln = name.lower()
            cands.append((tier_index(ln, DATE_TIERS), word_index(ln, DATE_WORDS), pos, name, cls))
    if not cands:
        return None
    cands.sort()
    return cands[0][3], cands[0][4]


def pick_measures(columns: "list[tuple[str, str | None]]") -> "list[str]":
    cands = []
    for pos, (name, dtype) in enumerate(columns):
        if classify_column(name, dtype) != "numeric":
            continue
        ln = name.lower()
        cands.append((tier_index(ln, MEASURE_TIERS), pos, name))
    cands.sort()
    return [c[2] for c in cands]


def aggregate_for(measure: str) -> str:
    return "AVG" if measure.lower().endswith(AVERAGE_SUFFIXES) else "SUM"


def pick_dimension(columns: "list[tuple[str, str | None]]") -> "str | None":
    cands = []
    for pos, (name, dtype) in enumerate(columns):
        if classify_column(name, dtype) != "string":
            continue
        ln = name.lower()
        if ln.endswith(DIMENSION_EXCLUDE_SUFFIXES):
            continue
        tier = tier_index(ln, DIMENSION_TIERS)
        if tier == len(DIMENSION_TIERS) and ln.endswith(NAME_SUFFIX):
            tier += 1  # a name column is high-cardinality; last resort
        cands.append((tier, pos, name))
    if not cands:
        return None
    cands.sort()
    return cands[0][2]


def linked_dimensions(fact: dict, fact_columns, dims: "list[tuple[dict, list]]") -> "list[tuple[dict, str]]":
    """Dimensions a fact joins to, found two ways from dbt's own artifacts: the fact `ref()`s the
    dimension (manifest depends_on), or a fact `<x>_fk` column matches the dimension's `<x>_pk`.
    Returns [(dim_node, "ref" | "fk")] in dimension order, each dimension once."""
    out: "list[tuple[dict, str]]" = []
    seen: set = set()
    fk_stems = {c[:-3].lower() for c, _ in fact_columns if c.lower().endswith("_fk")}
    for dim, dim_columns in dims:
        if dim["name"] == fact["name"]:
            continue
        via = None
        if dim["unique_id"] in fact["depends_on"]:
            via = "ref"
        elif any(c.lower().endswith("_pk") and c[:-3].lower() in fk_stems for c, _ in dim_columns):
            via = "fk"
        if via and dim["name"] not in seen:
            seen.add(dim["name"])
            out.append((dim, via))
    return out


def classify_model(name: str) -> str:
    ln = name.lower()
    if any(re.search(p, ln) for p in FACT_PATTERNS):
        return "fact"
    if any(re.search(p, ln) for p in DIM_PATTERNS):
        return "dim"
    return "other"


# ---------------------------------------------------------------------------
# SQL per dialect
# ---------------------------------------------------------------------------
def month_expr(column: str, cls: str, dialect: str) -> str:
    if dialect == "bigquery":
        # DATE_TRUNC(col, MONTH) is what a person would write, but dct's static column
        # check reads the bare MONTH keyword as a column of the model and fails the
        # board. EXTRACT(MONTH FROM ...) is parsed correctly and is equivalent.
        inner = f"DATE({column})" if cls == "timestamp" else column
        return f"DATE(EXTRACT(YEAR FROM {inner}), EXTRACT(MONTH FROM {inner}), 1)"
    if dialect == "snowflake":
        return f"DATE_TRUNC('MONTH', {column})"
    # postgres, duckdb, redshift
    inner = f"CAST({column} AS DATE)" if cls == "timestamp" else column
    return f"DATE_TRUNC('month', {inner})"


def window_expr(column: str, cls: str, dialect: str, months: int) -> str:
    """WHERE fragment keeping the last `months` complete months of `column`, per dialect."""
    d = f"DATE({column})" if cls == "timestamp" else column
    if dialect == "bigquery":
        # EXTRACT form, not DATE_TRUNC(x, MONTH): dct's static column check reads the bare MONTH
        # keyword as a column of the model (see month_expr and the dbtcharts skill).
        this_month = "DATE(EXTRACT(YEAR FROM CURRENT_DATE()), EXTRACT(MONTH FROM CURRENT_DATE()), 1)"
        return (f"{d} >= DATE_SUB({this_month}, INTERVAL {months} MONTH)"
                f" AND {d} < {this_month}")
    if dialect == "snowflake":
        return (f"{d} >= DATE_TRUNC('month', DATEADD(month, -{months}, CURRENT_DATE()))"
                f" AND {d} < DATE_TRUNC('month', CURRENT_DATE())")
    # postgres, redshift, duckdb
    return (f"{d} >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '{months} months')"
            f" AND {d} < DATE_TRUNC('month', CURRENT_DATE)")


def is_money(column: str) -> bool:
    return column.lower().endswith(MONEY_SUFFIXES)


def kpi_format(column: str, currency: str):
    """KPI value format: a preset name, or a {spec, prefix} mapping for a non-dollar currency."""
    if not is_money(column):
        return "number"
    if currency == "$":
        return "currency_whole"
    return OrderedDict([("spec", ",.0f"), ("prefix", currency)])


def axis_format(column: str, currency: str) -> str:
    """Axis number format. Only `$` has a currency preset; other symbols fall back to `number`."""
    if is_money(column) and currency == "$":
        return "currency"
    return "number"


def unit_suffix(column: str, currency: str) -> str:
    """Subtitle suffix naming the currency when the axis cannot show it (non-dollar money)."""
    return f" ({currency})" if is_money(column) and currency != "$" else ""


def ref(model: str) -> str:
    return "{{ ref('" + model + "') }}"


# ---------------------------------------------------------------------------
# YAML emission (block style, one key per line, deterministic)
# ---------------------------------------------------------------------------
def yq(s: str) -> str:
    """Quote a YAML scalar when it needs it."""
    if s == "" or re.search(r"[:#{}\[\],&*?|<>=!%@`\"'\n]|^\s|\s$|^-|^(true|false|null|yes|no|~)$", s, re.I):
        return json.dumps(s, ensure_ascii=False)
    return s


def emit_block_scalar(key: str, text: str, indent: int) -> "list[str]":
    pad = " " * indent
    lines = [f"{pad}{key}: |"]
    for line in text.rstrip("\n").split("\n"):
        lines.append(f"{pad}  {line}" if line else "")
    return lines


def emit_mapping(m: dict, indent: int) -> "list[str]":
    """Nested mapping as block YAML; a mapping whose values are all scalars and that sits under
    a `format` key is emitted inline (`{ spec: ",.0f", prefix: "£" }`), the dbt Charts idiom."""
    pad = " " * indent
    out: "list[str]" = []
    for k, v in m.items():
        if isinstance(v, dict):
            if k == "format":
                inner = ", ".join(f"{ik}: {yq(str(iv))}" for ik, iv in v.items())
                out.append(f"{pad}{k}: {{ {inner} }}")
            else:
                out.append(f"{pad}{k}:")
                out += emit_mapping(v, indent + 2)
        else:
            out.append(f"{pad}{k}: {yq(str(v))}")
    return out


class Board:
    def __init__(self, subject_area: str, slug: str, source: str, currency: str = "$"):
        self.subject_area = subject_area
        self.slug = slug
        self.source = source
        self.currency = currency
        self.title = label_of(subject_area)
        self.models: "list[dict]" = []
        self.linked: "list[tuple[str, str, str, str]]" = []   # (dim, home area, via, from fact)
        self.queries: "OrderedDict[str, dict]" = OrderedDict()
        self.charts: "OrderedDict[str, dict]" = OrderedDict()
        self.rows: "list" = []

    def add_query(self, name: str, sql: str, notes: str) -> str:
        self.queries[name] = {"sql": sql, "notes": notes}
        return name

    def add_chart(self, name: str, spec: dict) -> str:
        self.charts[name] = spec
        return name

    def to_yaml(self, generated_from: str) -> str:
        L: "list[str]" = []
        L.append(f"# Scaffolded by wire/scripts/dbtcharts_scaffold.py v{VERSION} from {generated_from}.")
        L.append("# Subject area: " + self.subject_area + ". Edit freely; regenerate with --force to start again.")
        L.append(f"title: {yq(self.title)}")
        L += emit_block_scalar("notes", self.notes_text(), 0)
        L.append(f"tags: [wire, {yq(self.slug)}]")
        L.append(f"source: {self.source}")
        L.append("")
        L.append("queries:")
        for qname, q in self.queries.items():
            L.append(f"  {qname}:")
            L += emit_block_scalar("sql", q["sql"], 4)
            L.append(f"    notes: {yq(q['notes'])}")
        L.append("")
        L.append("charts:")
        for cname, c in self.charts.items():
            L.append(f"  {cname}:")
            for k, v in c.items():
                if k == "style":
                    L.append("    style:")
                    L += emit_mapping(v, 6)
                elif k == "sort":
                    L.append(f"    sort: {{ by: {v['by']}, order: {v['order']} }}")
                elif isinstance(v, list):
                    L.append(f"    {k}: [{', '.join(v)}]")
                else:
                    L.append(f"    {k}: {yq(str(v))}")
        L.append("")
        L.append("rows:")
        for row in self.rows:
            if isinstance(row, str):
                L.append(f"  - {row}")
            elif "text" in row:
                L.append(f"  - text: {yq(row['text'])}")
            elif "height" in row:
                L.append(f"  - height: {row['height']}")
                L.append(f"    cols: [{', '.join(row['cols'])}]")
            else:
                L.append(f"  - cols: [{', '.join(row['cols'])}]")
        L.append("")
        return "\n".join(L)

    def notes_text(self) -> str:
        names = ", ".join(m["name"] for m in self.models)
        linked = ""
        if self.linked:
            parts = [f"{d} from {a} ({'ref() in' if v == 'ref' else 'foreign key of'} {f})"
                     for d, a, v, f in self.linked]
            linked = " Linked dimensions read from other folders: " + "; ".join(parts) + "."
        return (f"Scaffolded board for the {self.title} subject area: {len(self.models)} model(s) "
                f"({names}). Each fact has a KPI row, a {TREND_MONTHS}-month trend and a breakdown; each "
                f"dimension a record count and a breakdown. Queries read dbt models through ref(). "
                f"A starting point: curate it into a dashboard (KPI row with prior-period deltas, one hero "
                f"trend, a few breakdowns, a detail table) as the dbtcharts skill describes." + linked)


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------
def scaffold(manifest: dict, catalog: dict | None, args) -> "tuple[dict[str, Board], list[dict], dict]":
    nodes = model_nodes(manifest, args.layer_path)
    if not nodes:
        die(f"no enabled models found under {args.layer_path} in the manifest")

    wanted = set(a.strip() for a in args.subject_area.split(",")) if args.subject_area else None
    by_area: "OrderedDict[str, list[dict]]" = OrderedDict()
    for n in nodes:
        n["home_area"] = subject_area_of(n, args.layer_path)
        by_area.setdefault(n["home_area"], []).append(n)

    # A subject area's board covers the facts in its folder plus the dimensions those facts join
    # to, wherever those dimensions sit. Linked dimensions are copied into the area's model list
    # (a dimension can appear on several boards) and marked so the summary and notes say why.
    all_dims = [(n, merged_columns(n, catalog)) for n in nodes if classify_model(n["name"]) == "dim"]
    for area, models in by_area.items():
        present = {m["name"] for m in models}
        for fact in [m for m in models if classify_model(m["name"]) in ("fact", "other")]:
            for dim, via in linked_dimensions(fact, merged_columns(fact, catalog), all_dims):
                if dim["name"] in present:
                    continue
                present.add(dim["name"])
                linked = dict(dim)
                linked.update({"linked_from": fact["name"], "linked_via": via})
                models.append(linked)

    if wanted:
        by_area = OrderedDict((a, ms) for a, ms in by_area.items() if a in wanted or slug_of(a) in wanted)
    if wanted and not by_area:
        die(f"no models matched --subject-area {args.subject_area}; areas present: "
            + ", ".join(sorted({subject_area_of(n, args.layer_path) for n in nodes})))

    # Slugs must be unique; fall back to the full folder name on a collision.
    slugs: "dict[str, str]" = {}
    seen: "dict[str, str]" = {}
    for area in by_area:
        s = slug_of(area)
        if s in seen and seen[s] != area:
            s = re.sub(r"[^a-z0-9]+", "_", area.lower()).strip("_")
        seen[s] = area
        slugs[area] = s

    needs_human: "list[dict]" = []
    summary_boards: "list[dict]" = []
    boards: "OrderedDict[str, Board]" = OrderedDict()

    for area, models in by_area.items():
        board = Board(area, slugs[area], args.source_name, args.currency)
        summary_models = []
        for n in models:
            role = classify_model(n["name"])
            if role == "other" and not args.include_other:
                needs_human.append({"model": n["name"], "subject_area": area, "reason": "unknown_role",
                                    "detail": "name matches neither a fact nor a dimension convention; "
                                              "pass --include-other to chart it as a fact"})
                continue
            if role == "other":
                role = "fact"
            columns = merged_columns(n, catalog)
            if not columns:
                needs_human.append({"model": n["name"], "subject_area": area, "reason": "no_column_metadata",
                                    "detail": "no columns in the manifest (schema.yml) or the catalog; "
                                              "run `dbt docs generate` or document the model, then re-run"})
                continue
            typed = sum(1 for _, t in columns if t)
            chosen = chart_model(board, n, role, columns, args.dialect, args.currency)
            chosen.update({"model": n["name"], "role": role, "columns_seen": len(columns),
                           "columns_typed": typed})
            if n.get("linked_from"):
                chosen.update({"linked_from": n["linked_from"], "linked_via": n["linked_via"],
                               "home_subject_area": n["home_area"]})
                board.linked.append((n["name"], n["home_area"], n["linked_via"], n["linked_from"]))
            summary_models.append(chosen)
            board.models.append(n)
            for gap in chosen.get("gaps", []):
                needs_human.append({"model": n["name"], "subject_area": area, "reason": gap["reason"],
                                    "detail": gap["detail"]})
        if board.charts:
            boards[area] = board
            summary_boards.append({"subject_area": area, "file": f"{board.slug}.yml", "title": board.title,
                                   "models": summary_models, "queries": len(board.queries),
                                   "charts": len(board.charts)})
        else:
            needs_human.append({"model": None, "subject_area": area, "reason": "empty_subject_area",
                                "detail": "no model in this folder produced a chart; nothing written"})

    summary = {
        "scaffold_version": VERSION,
        "manifest": args.manifest,
        "catalog": args.catalog,
        "layer_path": args.layer_path,
        "dialect": args.dialect,
        "source_name": args.source_name,
        "currency": args.currency,
        "theme": args.theme,
        "trend_months": TREND_MONTHS,
        "boards": summary_boards,
        "needs_human_count": len(needs_human),
    }
    return boards, needs_human, summary


def chart_model(board: Board, node: dict, role: str, columns, dialect: str, currency: str = "$") -> dict:
    """Add the queries, charts and layout rows for one model. Returns what was chosen."""
    name = node["name"]
    label = label_of(name)
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    chosen: dict = {"date": None, "measures": [], "dimension": None, "gaps": []}
    date = pick_date(columns) if role == "fact" else None
    measures = pick_measures(columns) if role == "fact" else []
    dimension = pick_dimension(columns)
    chosen["date"] = date[0] if date else None
    chosen["measures"] = measures[:MAX_KPI_MEASURES]
    chosen["dimension"] = dimension

    if role == "fact" and not date:
        chosen["gaps"].append({"reason": "no_date_column",
                               "detail": "no date or timestamp column found by type or by the _dt/_date/_ts "
                                         "convention; no trend chart written"})
    if role == "fact" and not measures:
        chosen["gaps"].append({"reason": "no_measure_column",
                               "detail": "no numeric non-key column found; charts use COUNT(*) as the measure"})
    if not dimension:
        chosen["gaps"].append({"reason": "no_breakdown_dimension",
                               "detail": "no low-cardinality text column found; no breakdown chart written"})

    section_charts: "list[str]" = []
    kpi_cols: "list[str]" = []

    # --- KPI row ---
    select_parts = ["COUNT(*) AS record_count"]
    for m in measures[:MAX_KPI_MEASURES]:
        select_parts.append(f"{aggregate_for(m)}({m}) AS {m}")
    q_kpis = board.add_query(
        f"{key}_kpis",
        "SELECT\n  " + ",\n  ".join(select_parts) + f"\nFROM {ref(name)}",
        f"One row: record count{' and headline measures' if measures else ''} for {name} over all time.",
    )
    # KPI labels carry no entity prefix: the section heading above the row already names it, and a
    # long label is truncated on the card (WARN-KPI-LABEL-TRUNCATED).
    c = board.add_chart(f"{key}_records", OrderedDict([
        ("query", q_kpis), ("type", "kpi"), ("label", "Records"), ("value", "record_count"),
        ("notes", f"How many rows {name} holds."),
        ("style", OrderedDict([("value", OrderedDict([("format", "integer")]))])),
    ]))
    kpi_cols.append(c)
    for m in measures[:MAX_KPI_MEASURES]:
        c = board.add_chart(f"{key}_{m}", OrderedDict([
            ("query", q_kpis), ("type", "kpi"), ("label", label_of(m)), ("value", m),
            ("notes", f"{aggregate_for(m).capitalize()} of {m} across all rows of {name}."),
            ("style", OrderedDict([("value", OrderedDict([("format", kpi_format(m, currency))]))])),
        ]))
        kpi_cols.append(c)

    # --- Trend: one measure (two measures in different units share an axis badly and their
    # end-of-line labels collide), last TREND_MONTHS complete months, not the whole history ---
    trend_chart = None
    if role == "fact" and date:
        dcol, dcls = date
        if measures:
            m = measures[0]
            agg = f"{aggregate_for(m)}({m}) AS {m}"
            ycol = m
        else:
            agg = "COUNT(*) AS record_count"
            ycol = "record_count"
        q_trend = board.add_query(
            f"{key}_by_month",
            f"SELECT\n  {month_expr(dcol, dcls, dialect)} AS month,\n  {agg}"
            + f"\nFROM {ref(name)}\nWHERE {dcol} IS NOT NULL\n  AND {window_expr(dcol, dcls, dialect, TREND_MONTHS)}"
            + "\nGROUP BY 1\nORDER BY 1",
            f"Monthly {ycol} from {name} by {dcol}, last {TREND_MONTHS} complete months.",
        )
        trend_chart = board.add_chart(f"{key}_trend", OrderedDict([
            ("query", q_trend), ("type", "line"), ("title", f"{label} by month"),
            ("subtitle", f"{label_of(ycol)}{unit_suffix(ycol, currency)}, last {TREND_MONTHS} months"),
            ("x", "month"), ("y", ycol),
            ("notes", f"How {ycol} moves month by month, dated by {dcol}, over the last {TREND_MONTHS} months."),
            ("style", OrderedDict([
                ("number_format", axis_format(ycol, currency)),
                ("axis_x", OrderedDict([("time_unit", "yearmonth")])),
                ("axis_y", OrderedDict([("position", "left")])),
            ])),
        ]))

    # --- Breakdown ---
    breakdown_chart = None
    if dimension:
        if role == "fact" and measures:
            m = measures[0]
            agg = f"{aggregate_for(m)}({m}) AS {m}"
            ycol = m
        else:
            agg = "COUNT(*) AS record_count"
            ycol = "record_count"
        q_bd = board.add_query(
            f"{key}_by_{dimension}",
            f"SELECT\n  {dimension},\n  {agg}\nFROM {ref(name)}\nWHERE {dimension} IS NOT NULL\n"
            f"GROUP BY 1\nORDER BY 2 DESC\nLIMIT {BREAKDOWN_LIMIT}",
            f"Top {BREAKDOWN_LIMIT} {dimension} values in {name} by {ycol}.",
        )
        breakdown_chart = board.add_chart(f"{key}_by_{dimension}", OrderedDict([
            ("query", q_bd), ("type", "bar"), ("title", f"{label} by {label_of(dimension).lower()}"),
            ("subtitle", f"{label_of(ycol)}{unit_suffix(ycol, currency)}, all time, top {BREAKDOWN_LIMIT}"),
            ("x", dimension), ("y", ycol),
            ("sort", {"by": ycol, "order": "desc"}),
            ("notes", f"Which {dimension} values carry the most {ycol} in {name}."),
            ("style", OrderedDict([("orientation", "horizontal"),
                                   ("number_format", axis_format(ycol, currency))])),
        ]))

    # --- Layout for this model: a heading, the KPI row, then trend beside breakdown ---
    board.rows.append({"text": f"## {label}"})
    board.rows.append({"height": KPI_ROW_HEIGHT, "cols": kpi_cols})
    lower = [c for c in (trend_chart, breakdown_chart) if c]
    if len(lower) == 2:
        board.rows.append({"cols": lower})
    elif len(lower) == 1:
        board.rows.append(lower[0])
    section_charts.extend(kpi_cols + lower)
    chosen["charts"] = section_charts
    return chosen


# ---------------------------------------------------------------------------
# Anchor file
# ---------------------------------------------------------------------------
def anchor_yaml(source_name: str, profile: str, target: str | None) -> str:
    # Only the sources registry lives here. dct 0.8 rejects any other key (`serve:`, `theme:`,
    # `style:`) with "Extra inputs are not permitted"; presentation defaults go in charts/meta.yml
    # and the SQL dialect is inferred from the dbt profile target.
    lines = [
        "# dbt charts project configuration, written by wire/scripts/dbtcharts_scaffold.py.",
        "# Boards under charts/ read the warehouse through this source. Credentials stay in profiles.yml.",
        "sources:",
        f"  {source_name}:",
        "    type: dbt_profile",
        f"    profile: {profile}",
    ]
    if target:
        lines.append(f"    target: {target}")
    lines.append("")
    return "\n".join(lines)


def meta_yaml(theme: str, frame_width: int = 1440) -> str:
    return "\n".join([
        "# Project-wide defaults for every board under charts/, written by wire/scripts/dbtcharts_scaffold.py.",
        "# A board file may override any of these. Built-in themes: clarity, paper, stark, vivid, neon.",
        f"theme: {theme}",
        "style:",
        "  frame:",
        f"    width: {frame_width}",
        "",
    ])


def logo_data_uri(path: Path) -> str:
    """Embed an image as a data: URI. dct serves no static files and markdown images with a
    relative path render blank, so the logo travels inside the board."""
    import base64
    media = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
             ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(path.suffix.lower())
    if not media:
        die(f"--logo: unsupported image type {path.suffix!r} (svg, png, jpg, webp)")
    return f"data:{media};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def index_yaml(boards: "list[Board]", title: str, logo_uri: str | None, cards_per_row: int = 3) -> str:
    """The landing page dct serves at / in place of its default file listing: a heading (with the
    logo top-aligned beside it when given) and one bordered card per board, linking to it."""
    L = [
        "# Landing page for the dbt Charts server, written by wire/scripts/dbtcharts_scaffold.py.",
        "# dct serves charts/index.yml at / instead of a file listing. Text-only: no queries.",
        "# The heading lives in the first row rather than title: so a logo can sit level with it.",
        "notes: |",
        f"  Home page for the {title} dashboards: one card per subject-area board. Links open the board.",
        "tags: [wire, home]",
        "",
        "rows:",
        "  - cols:",
        f"      - width: {yq('84%' if logo_uri else '100%')}",
        "        text: |",
        f"          # {title}",
        "",
        f"          {len(boards)} dashboards over the warehouse, one per subject area. Each opens with a",
        "          KPI row, then a trend, a few breakdowns and a detail table.",
    ]
    if logo_uri:
        L += [
            '      - width: "16%"',
            "        notes: Logo embedded as a data URI; dct serves no static files.",
            "        text: |",
            f"          ![Logo]({logo_uri})",
        ]
    L.append("")
    for i in range(0, len(boards), cards_per_row):
        L.append("  - cols:")
        for b in boards[i:i + cards_per_row]:
            first = b.notes_text().split(":", 1)[0]
            L += [
                "      - text: |",
                f"          ### [{b.title}]({b.slug}.yml)",
                f"          {len(b.models)} model(s), {len(b.charts)} chart(s). {first}.",
                "        style:",
                "          border: { width: 1, color: dbt-grays.border, radius: 8 }",
                "          background: dbt-grays.canvas",
                '          padding: "20px"',
            ]
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    global TREND_MONTHS, BREAKDOWN_LIMIT, KPI_ROW_HEIGHT
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", required=True, help="path to dbt target/manifest.json")
    ap.add_argument("--catalog", default=None, help="path to dbt target/catalog.json (column types)")
    ap.add_argument("--out", required=True, help="output directory for the boards (usually charts/)")
    ap.add_argument("--layer-path", default="models/warehouse",
                    help="original_file_path prefix of the layer to chart (default models/warehouse)")
    ap.add_argument("--subject-area", default=None,
                    help="comma-separated folder names (or slugs) to scaffold; default all")
    ap.add_argument("--dialect", default="bigquery", choices=["bigquery", "snowflake", "postgres", "duckdb", "redshift"])
    ap.add_argument("--source-name", default="warehouse", help="source name boards reference (default warehouse)")
    ap.add_argument("--theme", default="vivid", choices=["clarity", "paper", "stark", "vivid", "neon"],
                    help="dbt Charts built-in theme, written once to <out>/meta.yml (default vivid)")
    ap.add_argument("--currency", default="$",
                    help="currency symbol for money measures (default $). Non-dollar symbols become a KPI "
                         "prefix; chart axes then use plain numbers because dct has no such axis preset")
    ap.add_argument("--title", default=None,
                    help="heading of the landing page <out>/index.yml (default: the dbt project name)")
    ap.add_argument("--logo", default=None,
                    help="path to an svg/png/jpg/webp logo, embedded in the landing page as a data URI")
    ap.add_argument("--trend-months", type=int, default=TREND_MONTHS,
                    help=f"trend charts cover the last N complete months (default {TREND_MONTHS}; "
                         "conventions windows.trend_months)")
    ap.add_argument("--breakdown-limit", type=int, default=BREAKDOWN_LIMIT,
                    help=f"top-N for breakdown charts (default {BREAKDOWN_LIMIT}; conventions chart_defaults.ranking.limit)")
    ap.add_argument("--kpi-row-height", type=int, default=KPI_ROW_HEIGHT,
                    help=f"height: on the KPI row (default {KPI_ROW_HEIGHT}; conventions board_shape.kpi_row_height)")
    ap.add_argument("--frame-width", type=int, default=1440,
                    help="style.frame.width written to meta.yml (default 1440; conventions presentation.frame_width)")
    ap.add_argument("--include-other", action="store_true",
                    help="chart models that match neither fact nor dimension conventions, as facts")
    ap.add_argument("--write-anchor", default=None, help="path to dbt_charts.yml to write if absent")
    ap.add_argument("--profile", default=None, help="dbt profile name for the anchor (default: manifest metadata)")
    ap.add_argument("--target", default=None, help="dbt target name for the anchor")
    ap.add_argument("--force", action="store_true", help="overwrite board files that already exist")
    args = ap.parse_args(argv)
    TREND_MONTHS, BREAKDOWN_LIMIT, KPI_ROW_HEIGHT = args.trend_months, args.breakdown_limit, args.kpi_row_height

    manifest = load_json(Path(args.manifest))
    catalog = load_json(Path(args.catalog)) if args.catalog else None
    boards, needs_human, summary = scaffold(manifest, catalog, args)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    skipped = []
    # Basenames only, so the same artifacts give the same file whichever directory the
    # scaffold was invoked from.
    generated_from = Path(args.manifest).name + (f" and {Path(args.catalog).name}" if args.catalog else "")
    for area, board in boards.items():
        path = out / f"{board.slug}.yml"
        if path.exists() and not args.force:
            skipped.append(str(path))
            continue
        path.write_text(board.to_yaml(generated_from), encoding="utf-8")
        written.append(str(path))
    summary["written"] = written
    summary["skipped_existing"] = skipped

    # Project defaults and landing page: written once, never over a curated file without --force.
    project_name = (manifest.get("metadata", {}) or {}).get("project_name") or "Warehouse"
    landing_title = args.title or label_of(project_name)
    for fname, text in (("meta.yml", meta_yaml(args.theme, args.frame_width)),
                        ("index.yml", index_yaml(list(boards.values()), landing_title,
                                                 logo_data_uri(Path(args.logo)) if args.logo else None))):
        path = out / fname
        if path.exists() and not args.force:
            print(f"{fname} exists, left unchanged: {path}")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"{fname} written: {path}")
    (out / "scaffold_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / "needs_human.json").write_text(json.dumps(needs_human, indent=2) + "\n", encoding="utf-8")

    if args.write_anchor:
        anchor = Path(args.write_anchor)
        if anchor.exists():
            print(f"anchor exists, left unchanged: {anchor}")
        else:
            profile = args.profile or (manifest.get("metadata", {}) or {}).get("project_name") or "default"
            anchor.write_text(anchor_yaml(args.source_name, profile, args.target), encoding="utf-8")
            print(f"anchor written: {anchor}")

    print(f"boards written: {len(written)}" + (f", skipped existing: {len(skipped)} (use --force)" if skipped else ""))
    for b in summary["boards"]:
        print(f"  {b['file']}: {len(b['models'])} model(s), {b['charts']} chart(s)")
    print(f"needs_human items: {len(needs_human)} -> {out / 'needs_human.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Tableau to LookML converter (wire#287, bi_migration, pair tableau_to_looker). EXPERIMENTAL.

Reads a Tableau snapshot (written by tableau_export.py: inventory.json, workbooks/*.twb,
datasources/*.tds) and does three jobs, all deterministic, no AI call:

    audit    classify every construct and write the audit catalogs, the data source
             fingerprints, the tool-neutral IR (bi_ir.py) and dependencies.jsonl
    convert  write LookML: views, a model file with explores, LookML dashboards,
             needs_human.json and conversion_summary.json (plus the IR and dependencies)
    lint     fail when emitted LookML still holds a Tableau expression

The agent running /wire:lookml-model-generate decides what the script refuses (every
needs_human item: LOD expressions, table calculations, blends, sets, actions, joins whose
cardinality Tableau never declared) and explore design. It never hand-writes LookML the
script emits.

Usage:
    python3 wire/scripts/twb_to_lookml.py audit   --snapshot <dir> --out <dir> [--site s]
    python3 wire/scripts/twb_to_lookml.py convert --snapshot <dir> --out <dir> [--site s]
        [--model NAME] [--connection NAME] [--dialect bigquery|snowflake]
        [--datasets id1,id2] [--workbooks w1,w2]
    python3 wire/scripts/twb_to_lookml.py lint <lookml_dir>

Rules (the pair ruleset is wire/bi_pairs/tableau_to_looker/translation_guide.md):
    - Identity is the internal name ([Calculation_1234]), never the caption.
    - Row-level calculations in the supported function subset are translated; division
      becomes a / NULLIF(b, 0), matching Tableau's null on divide by zero.
    - Aggregate calculations become type: number measures over emitted measures.
    - LOD expressions, table calculations, blends and extracts are redesign: never emitted.
    - Physical joins carry no cardinality in Tableau: emitted many_to_one and assisted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bi_ir  # noqa: E402

VERSION = "0.1.0"
FRAGMENT_MAX = 2000

# ---------------------------------------------------------------------------
# Mapping tables (property_mapping.md documents them)
# ---------------------------------------------------------------------------
DATATYPE_DIM = {"string": "string", "integer": "number", "real": "number", "boolean": "yesno",
                "date": "date", "datetime": "datetime"}
AGG_MEASURE = {"sum": ("sum", "total"), "avg": ("average", "average"), "min": ("min", "min"),
               "max": ("max", "max"), "countd": ("count_distinct", "count_distinct")}
# Connection classes that are files, not warehouse tables (the plan rules each: load to the warehouse, or drop)
FILE_CLASSES = {"excel-direct", "excel", "textscan", "csv", "google-sheets", "ogrdirect", "pdf", "json", "statfile"}
EXTRACT_CLASSES = {"hyper", "dataengine"}

DEFAULT_AGG = {"Sum": "sum", "Avg": "avg", "Min": "min", "Max": "max", "CountD": "countd"}
DERIVATION = {"none": None, "sum": "sum", "avg": "avg", "min": "min", "max": "max", "ctd": "countd",
              "usr": "user", "tyr": "year", "tqr": "quarter", "tmn": "month", "twk": "week", "tdy": "date",
              "yr": "year", "mn": "month", "attr": "attr", "cnt": "count"}
MARK_TYPE = {"bar": "looker_column", "line": "looker_line", "area": "looker_area", "pie": "looker_pie",
             "circle": "looker_scatter", "shape": "looker_scatter", "text": "looker_grid",
             "square": "looker_grid", "map": "looker_map", "multipolygon": "looker_map"}
TIMEFRAMES_DATE = ["raw", "date", "week", "month", "quarter", "year"]
TIMEFRAMES_TIME = ["raw", "time", "date", "week", "month", "quarter", "year"]

LOD = re.compile(r"\{\s*(FIXED|INCLUDE|EXCLUDE)\b", re.I)
TABLE_CALC = {"WINDOW_SUM", "WINDOW_AVG", "WINDOW_MIN", "WINDOW_MAX", "WINDOW_COUNT", "WINDOW_MEDIAN",
              "RUNNING_SUM", "RUNNING_AVG", "RUNNING_MIN", "RUNNING_MAX", "RUNNING_COUNT", "INDEX", "RANK",
              "RANK_DENSE", "RANK_MODIFIED", "RANK_UNIQUE", "RANK_PERCENTILE", "LOOKUP", "FIRST", "LAST",
              "SIZE", "TOTAL", "PREVIOUS_VALUE"}
AGG_FUNCS = {"SUM", "AVG", "MIN", "MAX", "COUNTD", "COUNT", "MEDIAN", "ATTR", "STDEV", "VAR", "PERCENTILE"}
ROW_FUNCS = {"IFNULL", "ZN", "IIF", "ISNULL", "CONTAINS", "UPPER", "LOWER", "TRIM", "LTRIM", "RTRIM", "ABS",
             "ROUND", "LEN", "LEFT", "RIGHT", "DATETRUNC", "DATEDIFF", "DATEPART", "YEAR", "MONTH", "DAY",
             "STR", "INT", "FLOAT", "STARTSWITH", "ENDSWITH", "REPLACE", "SQRT", "POWER", "FLOOR", "CEILING"}


class ConvertError(Exception):
    pass


# ---------------------------------------------------------------------------
# Snapshot reading
# ---------------------------------------------------------------------------

def read_xml(path: Path) -> ET.Element:
    if path.suffix in (".twbx", ".tdsx"):
        with zipfile.ZipFile(path) as z:
            inner = sorted(n for n in z.namelist() if n.endswith((".twb", ".tds")) and "/" not in n.strip("/"))
            if not inner:
                raise ConvertError(f"{path}: no .twb or .tds inside the package")
            return ET.fromstring(z.read(inner[0]))
    return ET.parse(path).getroot()


def fragment(el: ET.Element) -> str:
    s = ET.tostring(el, encoding="unicode")
    return s if len(s) <= FRAGMENT_MAX else s[:FRAGMENT_MAX] + "...<truncated>"


def load_snapshot(snap: Path):
    inv_path = snap / "inventory.json"
    inv = json.loads(inv_path.read_text()) if inv_path.exists() else {"objects": [], "site": "local"}
    objs = {o["path"]: o for o in inv.get("objects", [])}
    items = []
    for sub, kind in (("workbooks", "workbook"), ("datasources", "datasource")):
        for p in sorted((snap / sub).glob("*")) if (snap / sub).is_dir() else []:
            if p.suffix not in (".twb", ".twbx", ".tds", ".tdsx"):
                continue
            rel = f"{sub}/{p.name}"
            meta = objs.get(rel, {"id": p.stem, "name": p.stem, "updated_at": None, "sha256": None})
            items.append((kind, p, rel, meta))
    if not items:
        raise ConvertError(f"{snap}: no workbooks or data sources")
    return inv, items


# ---------------------------------------------------------------------------
# Tableau calculation language: tokenizer, parser, classifier, SQL emitter
# ---------------------------------------------------------------------------
TOKEN = re.compile(r"""
    (?P<ws>\s+|//[^\n]*)
  | (?P<field>\[[^\]]+\](?:\.\[[^\]]+\])?)
  | (?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<number>\d+(?:\.\d*)?|\.\d+)
  | (?P<op><=|>=|<>|!=|==|[-+*/%=<>(),{}:])
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
""", re.X)
KEYWORDS = {"IF", "THEN", "ELSEIF", "ELSE", "END", "CASE", "WHEN", "AND", "OR", "NOT", "TRUE", "FALSE",
            "NULL", "IN", "FIXED", "INCLUDE", "EXCLUDE"}


def tokenize(text: str):
    toks, pos = [], 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ConvertError(f"cannot tokenise at {text[pos:pos + 20]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        val = m.group(kind)
        if kind == "word" and val.upper() in KEYWORDS:
            kind, val = "kw", val.upper()
        toks.append((kind, val))
    return toks


def classify_formula(formula: str):
    """Return (kind, functions, refs). kind: lod | table_calc | aggregate | row."""
    toks = tokenize(formula)
    funcs = {v.upper() for i, (k, v) in enumerate(toks) if k == "word" and i + 1 < len(toks) and toks[i + 1] == ("op", "(")}
    refs = [v for k, v in toks if k == "field"]
    if LOD.search(formula):
        return "lod", funcs, refs
    if funcs & TABLE_CALC:
        return "table_calc", funcs, refs
    if funcs & AGG_FUNCS:
        return "aggregate", funcs, refs
    return "row", funcs, refs


class Unsupported(Exception):
    pass


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=None, v=None):
        if self.i >= len(self.t):
            return False
        tk, tv = self.t[self.i]
        return (k is None or tk == k) and (v is None or tv == v)

    def take(self, k=None, v=None):
        if not self.peek(k, v):
            got = self.t[self.i] if self.i < len(self.t) else ("end", "")
            raise Unsupported(f"expected {v or k}, got {got[1]!r}")
        self.i += 1
        return self.t[self.i - 1]

    def parse(self):
        e = self.expr()
        if self.i != len(self.t):
            raise Unsupported(f"unexpected {self.t[self.i][1]!r}")
        return e

    def expr(self):
        e = self.and_()
        while self.peek("kw", "OR"):
            self.take()
            e = ("bin", "OR", e, self.and_())
        return e

    def and_(self):
        e = self.not_()
        while self.peek("kw", "AND"):
            self.take()
            e = ("bin", "AND", e, self.not_())
        return e

    def not_(self):
        if self.peek("kw", "NOT"):
            self.take()
            return ("not", self.not_())
        return self.cmp()

    def cmp(self):
        e = self.add()
        if self.peek("op") and self.t[self.i][1] in ("=", "==", "!=", "<>", "<", "<=", ">", ">="):
            op = self.take()[1]
            op = {"==": "=", "!=": "<>"}.get(op, op)
            e = ("bin", op, e, self.add())
        return e

    def add(self):
        e = self.mul()
        while self.peek("op") and self.t[self.i][1] in ("+", "-"):
            op = self.take()[1]
            e = ("bin", op, e, self.mul())
        return e

    def mul(self):
        e = self.unary()
        while self.peek("op") and self.t[self.i][1] in ("*", "/", "%"):
            op = self.take()[1]
            e = ("bin", op, e, self.unary())
        return e

    def unary(self):
        if self.peek("op", "-"):
            self.take()
            return ("neg", self.unary())
        return self.primary()

    def primary(self):
        if self.peek("number"):
            return ("num", self.take()[1])
        if self.peek("string"):
            return ("str", self.take()[1][1:-1])
        if self.peek("field"):
            return ("field", self.take()[1])
        if self.peek("kw", "TRUE") or self.peek("kw", "FALSE") or self.peek("kw", "NULL"):
            return ("lit", self.take()[1])
        if self.peek("op", "("):
            self.take()
            e = self.expr()
            self.take("op", ")")
            return e
        if self.peek("kw", "IF"):
            self.take()
            branches = []
            cond = self.expr()
            self.take("kw", "THEN")
            branches.append((cond, self.expr()))
            other = None
            while True:
                if self.peek("kw", "ELSEIF"):
                    self.take()
                    c = self.expr()
                    self.take("kw", "THEN")
                    branches.append((c, self.expr()))
                elif self.peek("kw", "ELSE"):
                    self.take()
                    other = self.expr()
                else:
                    break
            self.take("kw", "END")
            return ("case", branches, other)
        if self.peek("kw", "CASE"):
            self.take()
            subject = self.expr()
            branches, other = [], None
            while self.peek("kw", "WHEN"):
                self.take()
                v = self.expr()
                self.take("kw", "THEN")
                branches.append((("bin", "=", subject, v), self.expr()))
            if self.peek("kw", "ELSE"):
                self.take()
                other = self.expr()
            self.take("kw", "END")
            return ("case", branches, other)
        if self.peek("word"):
            name = self.take()[1].upper()
            self.take("op", "(")
            args = []
            if not self.peek("op", ")"):
                args.append(self.expr())
                while self.peek("op", ","):
                    self.take()
                    args.append(self.expr())
            self.take("op", ")")
            return ("call", name, args)
        got = self.t[self.i][1] if self.i < len(self.t) else "end"
        raise Unsupported(f"unexpected {got!r}")


class Emitter:
    """AST to SQL for one dialect. resolve(field_token, context) -> (sql_ref, data_type)."""

    def __init__(self, resolve, dialect: str, aggregate: bool):
        self.resolve, self.dialect, self.aggregate = resolve, dialect, aggregate
        self.used_params = []

    def q(self, s):
        if "'" in s:
            raise Unsupported("string literal containing a quote")
        return f"'{s}'"

    def is_str(self, n):
        return n[0] == "str" or (n[0] == "field" and self.resolve(n[1], "row")[1] == "string")

    def emit(self, n):
        k = n[0]
        if k == "num":
            return n[1].rstrip(".") if n[1].endswith(".") else n[1]
        if k == "str":
            return self.q(n[1])
        if k == "lit":
            return n[1]
        if k == "field":
            ref, _ = self.resolve(n[1], "row")
            if ref.startswith("{% parameter"):
                self.used_params.append(ref)
            return ref
        if k == "neg":
            return f"-{self.emit(n[1])}"
        if k == "not":
            return f"NOT ({self.emit(n[1])})"
        if k == "bin":
            _, op, a, b = n
            if op == "/":
                return f"({self.emit(a)}) / NULLIF({self.emit(b)}, 0)"
            if op == "%":
                return f"MOD({self.emit(a)}, {self.emit(b)})"
            if op == "+" and (self.is_str(a) or self.is_str(b)):
                return f"CONCAT({self.emit(a)}, {self.emit(b)})"
            return f"{self.emit(a)} {op} {self.emit(b)}"
        if k == "case":
            parts = " ".join(f"WHEN {self.emit(c)} THEN {self.emit(v)}" for c, v in n[1])
            other = f" ELSE {self.emit(n[2])}" if n[2] is not None else ""
            return f"CASE {parts}{other} END"
        if k == "call":
            return self.call(n[1], n[2])
        raise Unsupported(f"node {k}")

    def date_part(self, node):
        if node[0] != "str":
            raise Unsupported("date part must be a literal")
        part = node[1].lower()
        if part not in ("year", "quarter", "month", "week", "day", "hour", "minute", "second"):
            raise Unsupported(f"date part {part!r}")
        return part

    def call(self, f, a):
        bq = self.dialect == "bigquery"
        E = self.emit
        if f in AGG_FUNCS:
            if not self.aggregate:
                raise Unsupported(f"aggregate {f} in a row-level context")
            if f not in ("SUM", "AVG", "MIN", "MAX", "COUNTD"):
                raise Unsupported(f"aggregate {f} has no measure mapping")
            if len(a) != 1 or a[0][0] != "field":
                raise Unsupported(f"{f} over an expression (not a single field)")
            ref, _ = self.resolve(a[0][1], f.lower())
            return ref
        if f in ("IFNULL",):
            return f"COALESCE({E(a[0])}, {E(a[1])})"
        if f == "ZN":
            return f"COALESCE({E(a[0])}, 0)"
        if f == "ISNULL":
            return f"({E(a[0])} IS NULL)"
        if f == "IIF":
            other = f" ELSE {E(a[2])}" if len(a) > 2 else ""
            return f"CASE WHEN {E(a[0])} THEN {E(a[1])}{other} END"
        if f == "CONTAINS":
            return f"(STRPOS({E(a[0])}, {E(a[1])}) > 0)" if bq else f"CONTAINS({E(a[0])}, {E(a[1])})"
        if f in ("STARTSWITH", "ENDSWITH"):
            return f"{f[:-4]}S_WITH({E(a[0])}, {E(a[1])})" if bq else f"{f}({E(a[0])}, {E(a[1])})"
        if f in ("UPPER", "LOWER", "TRIM", "LTRIM", "RTRIM", "ABS", "SQRT", "FLOOR", "LEFT", "RIGHT", "REPLACE", "POWER"):
            return f"{f}({', '.join(E(x) for x in a)})"
        if f == "CEILING":
            return f"CEIL({E(a[0])})"
        if f == "ROUND":
            return f"ROUND({', '.join(E(x) for x in a)})"
        if f == "LEN":
            return f"LENGTH({E(a[0])})"
        if f == "DATETRUNC":
            part = self.date_part(a[0])
            if bq:
                fn = "TIMESTAMP_TRUNC" if self.dtype(a[1]) == "datetime" else "DATE_TRUNC"
                return f"{fn}({E(a[1])}, {part.upper()})"
            return f"DATE_TRUNC('{part}', {E(a[1])})"
        if f == "DATEDIFF":
            part = self.date_part(a[0])
            if bq:
                if self.dtype(a[1]) == "datetime" or self.dtype(a[2]) == "datetime":
                    return f"TIMESTAMP_DIFF(TIMESTAMP({E(a[2])}), TIMESTAMP({E(a[1])}), {part.upper()})"
                return f"DATE_DIFF({E(a[2])}, {E(a[1])}, {part.upper()})"
            return f"DATEDIFF('{part}', {E(a[1])}, {E(a[2])})"
        if f == "DATEPART":
            return f"EXTRACT({self.date_part(a[0]).upper()} FROM {E(a[1])})"
        if f in ("YEAR", "MONTH", "DAY"):
            return f"EXTRACT({f} FROM {E(a[0])})"
        if f == "STR":
            return f"CAST({E(a[0])} AS {'STRING' if bq else 'VARCHAR'})"
        if f == "INT":
            return f"CAST({E(a[0])} AS {'INT64' if bq else 'INTEGER'})"
        if f == "FLOAT":
            return f"CAST({E(a[0])} AS {'FLOAT64' if bq else 'FLOAT'})"
        raise Unsupported(f"function {f} has no SQL mapping")

    def dtype(self, node):
        return self.resolve(node[1], "row")[1] if node[0] == "field" else None


# ---------------------------------------------------------------------------
# Workbook and data source parsing into IR
# ---------------------------------------------------------------------------

def unq(s):
    return s[1:-1] if s and s.startswith("[") and s.endswith("]") else s


def object_relation(obj: ET.Element) -> str | None:
    """A logical-layer object's relation name; the object caption is a label and can differ."""
    r = obj.find("properties/relation")
    return r.get("name") if r is not None and r.get("name") else obj.get("caption")


def parse_datasource(ds: ET.Element, owner_id: str, site: str, file_rel: str, published_meta=None):
    """Return a dataset IR object (with private helper keys starting with '_')."""
    if published_meta:
        # a published .tds's formatted-name is often an internal id (federated.0abc) shared by copies;
        # the site name is unique per project and is what users see
        name = published_meta.get("name") or ds.get("formatted-name")
    else:
        name = ds.get("name") or ds.get("formatted-name")
    caption = ds.get("caption") or name
    conn = ds.find("connection")
    if published_meta:
        ident = bi_ir.identity("tableau", site, "datasource", published_meta["id"])
    else:
        ident = bi_ir.child(owner_id, "datasource", name)
    dataset = {"id": ident, "kind": "dataset", "name": name, "label": caption,
               "source": {"file": file_rel, "fragment": fragment(ds)}, "published": bool(published_meta),
               "fields": [], "joins": [], "relations": [], "materialisation": "live", "workbook": None
               if published_meta else owner_id, "unsupported": []}
    if conn is None and name != "Parameters":
        dataset["class"], dataset["reason"] = "drop", "no connection"
        return dataset
    if conn is None:
        conn = ET.Element("connection")
    if conn.get("class") == "sqlproxy":
        dataset["connection"] = {"class": "published", "database": conn.get("dbname"), "server": conn.get("server")}
        dataset["class"], dataset["reason"] = "mechanical", f"uses published data source {conn.get('dbname')}"
        dataset["_published_ref"] = conn.get("dbname")
        return dataset
    nc = conn.find("named-connections/named-connection/connection")
    dataset["connection"] = {"class": nc.get("class") if nc is not None else conn.get("class"),
                             "project": (nc.get("project") if nc is not None else None),
                             "server": nc.get("server") if nc is not None else None,
                             "schema": nc.get("schema") if nc is not None else None,
                             # file sources: two workbooks reading different files must not share a view
                             "database": (nc.get("dbname") or nc.get("filename") or None) if nc is not None else None}
    # relations
    relations, joins = [], []

    def walk(rel):
        t = rel.get("type")
        if t == "table":
            relations.append({"name": rel.get("name"), "table": rel.get("table"), "type": "table"})
        elif t == "text":
            relations.append({"name": rel.get("name"), "sql": (rel.text or "").strip(), "type": "custom_sql"})
        elif t == "collection":
            for k in rel.findall("relation"):
                walk(k)
        elif t == "join":
            kids = rel.findall("relation")
            for k in kids:
                walk(k)
            ex = rel.find("clause/expression")
            on = None
            if ex is not None and ex.get("op") == "=":
                sides = [e.get("op") for e in ex.findall("expression")]
                on = sides
            joins.append({"kind": "physical", "type": rel.get("join", "inner"),
                          "left": kids[0].get("name") if kids else None,
                          "right": kids[-1].get("name") if kids else None, "on": on, "cardinality": None})

    top = conn.find("relation")
    if top is not None:
        walk(top)
    og = ds.find("object-graph")
    if og is not None:
        objs = {o.get("id"): o for o in og.findall("objects/object")}
        for o in objs.values():
            r = o.find("properties/relation")
            if r is not None and not any(x["name"] == r.get("name") for x in relations):
                walk(r)
        for rel in og.findall("relationships/relationship"):
            ex = rel.find("expression")
            sides = [e.get("op") for e in ex.findall("expression")] if ex is not None else None
            a, b = rel.find("first-end-point"), rel.find("second-end-point")
            ua, ub = a.get("unique-key") == "true", b.get("unique-key") == "true"
            card = {(False, True): "many_to_one", (True, False): "one_to_many",
                    (True, True): "one_to_one"}.get((ua, ub), "many_to_many")
            joins.append({"kind": "relationship", "type": "left",
                          "left": object_relation(objs[a.get("object-id")]),
                          "right": object_relation(objs[b.get("object-id")]), "on": sides, "cardinality": card})
    dataset["relations"] = relations
    dataset["joins"] = joins
    # physical columns
    colmap = {m.get("key"): m.get("value") for m in conn.findall("cols/map")}
    meta = {}
    for mr in conn.findall("metadata-records/metadata-record"):
        if mr.get("class") != "column":
            continue
        local = mr.findtext("local-name")
        meta[local] = {"remote": mr.findtext("remote-name"), "parent": unq(mr.findtext("parent-name") or ""),
                       "type": mr.findtext("local-type"), "aggregation": mr.findtext("aggregation")}
    overrides = {c.get("name"): c for c in ds.findall("column")}
    for local in sorted(meta):
        m = meta[local]
        rel = m["parent"] or unq((colmap.get(local) or "").split("].[")[0] + "]")
        ov = overrides.get(local)
        dataset["fields"].append({
            "id": bi_ir.field_id("tableau", site, name, unq(local)), "name": unq(local),
            "label": (ov.get("caption") if ov is not None and ov.get("caption") else m["remote"]),
            "field_kind": "dimension" if m["type"] in ("string", "date", "datetime", "boolean") or m["aggregation"] in ("Count", "Year") else "measure",
            "source_type": m["type"], "data_type": m["type"], "aggregation": DEFAULT_AGG.get(m["aggregation"]),
            "expression": f"[{rel}].[{m['remote']}]", "hidden": bool(ov is not None and ov.get("hidden") == "true"),
            "format": ov.get("default-format") if ov is not None else None,
            "dataset": ident, "_relation": rel, "_remote": m["remote"],
        })
    # calculated fields, groups, bins, parameters
    for c in ds.findall("column"):
        calc = c.find("calculation")
        if calc is None:
            continue
        cname = unq(c.get("name"))
        base = {"id": bi_ir.field_id("tableau", site, name, cname), "name": cname, "label": c.get("caption") or cname,
                "source_type": c.get("datatype"), "data_type": c.get("datatype"), "dataset": ident,
                "format": c.get("default-format"), "hidden": c.get("hidden") == "true", "_role": c.get("role")}
        cls = calc.get("class")
        if ds.get("name") == "Parameters":
            members = [unq(m.get("value")).strip('"') for m in c.findall("members/member")]
            rng = c.find("range")
            base.update({"field_kind": "parameter", "expression": c.get("value"),
                         "_members": [re.sub(r"\\(.)", r"\1", m.get("value").strip('"')) for m in c.findall("members/member")],
                         "_range": dict(rng.attrib) if rng is not None else None})
        elif cls == "categorical-bin":
            bins = [(b.get("value").strip('"'), [v.text.strip('"') for v in b.findall("value")]) for b in calc.findall("bin")]
            base.update({"field_kind": "group", "expression": f"group of {calc.get('column')}",
                         "_column": calc.get("column"), "_bins": bins})
        elif cls == "bin":
            base.update({"field_kind": "bin", "expression": calc.get("formula"), "_size": calc.get("size"),
                         "_size_parameter": calc.get("size-parameter")})
        else:
            base.update({"field_kind": "calculation", "expression": calc.get("formula")})
        dataset["fields"].append(base)
    for g in ds.findall("group"):
        gname = unq(g.get("name"))
        dataset["fields"].append({"id": bi_ir.field_id("tableau", site, name, gname), "name": gname,
                                  "label": g.get("caption") or gname, "field_kind": "set",
                                  "expression": fragment(g), "dataset": ident})
    ext = ds.find("extract")
    if ext is not None and ext.get("enabled") == "true":
        ec = ext.find("connection")
        dataset["materialisation"] = "extract"
        dataset["_extract"] = {"last_refreshed": ec.get("update-time") if ec is not None else None}
    elif dataset["connection"]["class"] in EXTRACT_CLASSES:
        # published extract-only data: the .hyper file is the only copy, there is no live table
        dataset["materialisation"] = "extract"
        dataset["_extract"] = {"last_refreshed": None}
    elif dataset["connection"]["class"] in FILE_CLASSES:
        dataset["materialisation"] = "file"
    return dataset


def filter_detail(f: ET.Element) -> dict:
    """A worksheet filter as {column, value (Looker filter expression) or reason}."""
    out = {"column": f.get("column")}
    if f.get("class") == "quantitative":
        lo, hi = f.findtext("min"), f.findtext("max")
        lo, hi = (param_default(lo, "number") if lo else None), (param_default(hi, "number") if hi else None)
        if lo and hi:
            out["value"] = f"[{lo}, {hi}]"
        elif lo:
            out["value"] = f">={lo}"
        elif hi:
            out["value"] = f"<={hi}"
        else:
            out["reason"] = "quantitative filter with no range (relative date or all values)"
        return out
    if f.get("class") == "categorical":
        g = f.find("groupfilter")
        fn = g.get("function") if g is not None else None
        kids = g.findall("groupfilter") if g is not None else []
        members = [k.get("member") for k in kids if k.get("function") == "member"]
        if fn == "except" and members == ["%null%"] and any(k.get("function") == "level-members" for k in kids):
            out["value"] = "-NULL"
        elif fn == "member" and g.get("member"):
            out["value"] = categorical_value([g.get("member")])
        elif fn == "union" and members and len(members) == len(kids):
            out["value"] = categorical_value(members)
        elif fn == "level-members":
            out["value"] = None          # all values: no filter
        else:
            out["reason"] = f"categorical filter ({fn}) not mapped"
        return out
    out["reason"] = f"{f.get('class')} filter not mapped"
    return out


def categorical_value(members):
    vals = []
    for m in members:
        if m == "%null%":
            vals.append("NULL")
        else:
            vals.append(m.strip('"').replace(",", "^,"))
    return ",".join(vals)


def column_instance(name: str):
    """'[sum:sales:qk]' -> ('sum', 'sales', 'qk'); '[Calculation_1]' -> (None, 'Calculation_1', None)"""
    inner = unq(name)
    parts = inner.split(":")
    if len(parts) >= 3:
        return parts[0], ":".join(parts[1:-1]), parts[-1]
    return None, inner, None


def parse_workbook(root: ET.Element, meta: dict, site: str, file_rel: str):
    wid = bi_ir.identity("tableau", site, "workbook", meta["id"])
    datasets, reports, dashboards = [], [], []
    params = {}
    for ds in root.findall("datasources/datasource"):
        d = parse_datasource(ds, wid, site, file_rel)
        if ds.get("name") == "Parameters":
            for f in d["fields"]:
                params[f["name"]] = f
            d["class"], d["reason"] = "mechanical", "parameters"
        datasets.append(d)
    ds_by_name = {d["name"]: d for d in datasets}
    for ws in root.findall("worksheets/worksheet"):
        view = ws.find("table/view")
        used = [x.get("name") for x in view.findall("datasources/datasource")] if view is not None else []
        used = [u for u in used if u != "Parameters"]
        insts = []
        for dep in view.findall("datasource-dependencies") if view is not None else []:
            for ci in dep.findall("column-instance"):
                insts.append({"datasource": dep.get("datasource"), "instance": ci.get("name"),
                              "column": ci.get("column"), "derivation": ci.get("derivation")})
        shelves = {}
        for shelf in ("rows", "cols"):
            txt = ws.findtext(f"table/{shelf}") or ""
            shelves[shelf] = re.findall(r"\[([^\]]+)\]\.(\[[^\]]+\])", txt)
        enc = [(e.tag, e.get("column")) for e in ws.findall("table/encodings/*")]
        mark = ws.find("table/panes/pane/mark")
        filters = [f.get("column") for f in view.findall("filter")] if view is not None else []
        filter_details = [filter_detail(f) for f in view.findall("filter")] if view is not None else []
        sorts = [(s.get("column"), s.get("direction"), s.get("using"))
                 for s in (view.findall("sort") + view.findall("computed-sort"))] if view is not None else []
        reports.append({"id": bi_ir.child(wid, "sheet", ws.get("name")), "kind": "report", "name": ws.get("name"),
                        "source": {"file": file_rel, "fragment": fragment(ws)}, "workbook": wid,
                        "datasets": used, "blended": len(used) > 1,
                        "query": {"instances": insts, "rows": shelves["rows"], "cols": shelves["cols"],
                                  "encodings": enc, "filters": filters, "filter_details": filter_details,
                                  "sorts": sorts},
                        "visualisation": {"mark": (mark.get("class") if mark is not None else "Automatic")}})
    for db in root.findall("dashboards/dashboard"):
        size = db.find("size")
        zones = []

        def walkz(z):
            for c in z.findall("zone"):
                if c.get("type-v2", "").startswith("layout"):
                    walkz(c)
                    continue
                zones.append({"zone_id": c.get("id"), "type": c.get("type-v2") or "sheet", "name": c.get("name"),
                              "param": c.get("param"), "x": int(c.get("x", 0)), "y": int(c.get("y", 0)),
                              "w": int(c.get("w", 0)), "h": int(c.get("h", 0)),
                              "text": " ".join(r.text or "" for r in c.findall("formatted-text/run")).strip()})
                walkz(c)

        zr = db.find("zones")
        if zr is not None:
            walkz(zr)
        dashboards.append({"id": bi_ir.child(wid, "dashboard", db.get("name")), "kind": "dashboard", "name": db.get("name"),
                           "source": {"file": file_rel, "fragment": fragment(db)}, "workbook": wid,
                           "story": db.get("type") == "storyboard",
                           "size": {"width": int(size.get("maxwidth", 1000)) if size is not None else 1000,
                                    "height": int(size.get("maxheight", 800)) if size is not None else 800},
                           "zones": zones, "device_layouts": [d.get("name") for d in db.findall("devicelayouts/devicelayout")]})
    actions = []
    for a in root.findall("actions/action"):
        src = a.find("source")
        cmd = a.find("command")
        actions.append({"name": a.get("caption") or a.get("name"), "command": cmd.get("command") if cmd is not None else None,
                        "dashboard": src.get("dashboard") if src is not None else None,
                        "worksheet": src.get("worksheet") if src is not None else None,
                        "params": {p.get("name"): p.get("value") for p in (cmd.findall("param") if cmd is not None else [])},
                        "fragment": fragment(a)})
    return {"id": wid, "name": meta.get("name"), "meta": meta, "datasets": datasets, "reports": reports,
            "dashboards": dashboards, "actions": actions, "params": params, "ds_by_name": ds_by_name}


# ---------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------

def fingerprint(d: dict) -> str | None:
    if not d.get("relations"):
        return None
    conn = d.get("connection") or {}
    rels = sorted((r.get("table") or hashlib.sha256((r.get("sql") or "").encode()).hexdigest()) for r in d["relations"])
    joins = sorted(json.dumps([j.get("kind"), j.get("type"), j.get("left"), j.get("right"), j.get("on")]) for j in d["joins"])
    cols = sorted(f.get("_remote") + "@" + (f.get("_relation") or "") for f in d["fields"] if f.get("_remote"))
    payload = json.dumps([conn.get("class"), conn.get("project"), conn.get("server"), rels, joins, cols]
                         + ([conn["database"]] if conn.get("database") else []))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Estate: all workbooks and published data sources, with classification
# ---------------------------------------------------------------------------

class Estate:
    def __init__(self, snap: Path, site: str | None, dialect: str = "bigquery"):
        inv, items = load_snapshot(snap)
        self.site = site or inv.get("site") or "local"
        self.inventory = inv
        self.dialect = dialect
        self.workbooks, self.published, self.published_ref = [], {}, {}
        for kind, path, rel, meta in items:
            root = read_xml(path)
            if kind == "datasource":
                d = parse_datasource(root, None, self.site, rel, published_meta=meta)
                self.published[meta["id"]] = d
                # a workbook names a published source by its content URL (sqlproxy dbname); older files by name
                for key in (meta.get("content_url"), meta.get("name"), root.get("formatted-name")):
                    if key:
                        self.published_ref.setdefault(key, d)
            else:
                self.workbooks.append(parse_workbook(root, meta, self.site, rel))
        self.datasets = list(self.published.values()) + [d for w in self.workbooks for d in w["datasets"]]
        for d in self.datasets:
            d["fingerprint"] = fingerprint(d)
        self.view_names = {}
        self.classify()

    # -- naming -------------------------------------------------------------
    def dataset_of(self, d):
        if d.get("_published_ref") and d["_published_ref"] in self.published_ref:
            return self.published_ref[d["_published_ref"]]
        return d

    def view_for(self, d, rel_name):
        rel = next((r for r in d["relations"] if r["name"] == rel_name), None)
        if rel is None:
            return bi_ir.slug(rel_name)
        key = (json.dumps(d.get("connection"), sort_keys=True), rel.get("table") or rel.get("sql"))
        if key not in self.view_names:
            base = bi_ir.slug(rel.get("table", "").split("].[")[-1].strip("[]") if rel.get("table") else d["label"])
            name, n = base, 2
            while name in self.view_names.values():
                name, n = f"{base}_{n}", n + 1
            self.view_names[key] = name
        return self.view_names[key]

    def base_view(self, d):
        return self.view_for(d, d["relations"][0]["name"]) if d["relations"] else bi_ir.slug(d["label"])

    def model_name(self, d):
        """One explore per fingerprint group; different data sources with one caption get _2, _3."""
        if not hasattr(self, "_model_names"):
            self._model_names, used, groups = {}, set(), {}
            for x in self.datasets:
                if x.get("name") == "Parameters" or not x.get("relations"):
                    continue
                groups.setdefault(x.get("fingerprint") or x["id"], []).append(x)
            # larger groups name first; a group's name is its shortest caption (as in datasource_fingerprints.csv)
            for key in sorted(groups, key=lambda k: (-len(groups[k]), k)):
                caption = min((m["label"] for m in groups[key]), key=lambda c: (len(c), c))
                base = bi_ir.slug(caption)
                name, n = base, 2
                while name in used:
                    name, n = f"{base}_{n}", n + 1
                used.add(name)
                self._model_names[key] = name
        return self._model_names.get(d.get("fingerprint") or d["id"], bi_ir.slug(d["label"]))

    # -- field resolution ---------------------------------------------------
    def field(self, d, name):
        return next((f for f in d["fields"] if f["name"] == name), None)

    def lookml_name(self, f):
        if f.get("_remote"):
            n = bi_ir.slug(f["_remote"])
            return n
        return bi_ir.slug(f["label"])

    def column_ref(self, d, f, row_ctx=True):
        view = self.view_for(d, f["_relation"])
        n = self.lookml_name(f)
        if f["data_type"] in ("date", "datetime"):
            return f"${{{view}.{n}_raw}}", f["data_type"], view
        return f"${{{view}.{n}}}", f["data_type"], view

    def measure_name(self, f, agg):
        kind, prefix = AGG_MEASURE[agg]
        return f"{prefix}_{self.lookml_name(f)}"

    # -- classification -----------------------------------------------------
    def classify(self):
        for d in self.datasets:
            if d.get("class") == "drop" or d.get("name") == "Parameters":
                continue
            if d.get("_published_ref"):
                d.setdefault("class", "mechanical")
                continue
            reasons, cls = [], "mechanical"
            if any(r["type"] == "custom_sql" for r in d["relations"]):
                cls, reasons = "assisted", reasons + ["custom SQL relation: becomes a derived table, check the dialect"]
            if any(j["kind"] == "relationship" for j in d["joins"]):
                cls, reasons = "assisted", reasons + ["logical relationships: explore joins from declared cardinality"]
            if any(j["kind"] == "physical" for j in d["joins"]):
                cls, reasons = "assisted", reasons + ["physical join: Tableau declares no cardinality, many_to_one proposed"]
            if d["materialisation"] == "extract":
                cls, reasons = "redesign", reasons + ["extract: data is outside the warehouse, plan rules the disposition"]
            if d["materialisation"] == "file":
                cls, reasons = "redesign", reasons + [
                    f"file source ({d['connection']['class']}): no warehouse table, plan rules load or drop"]
            d["class"], d["reason"] = cls, "; ".join(reasons)
            for j in d["joins"]:
                j["class"] = "assisted"
                j["reason"] = ("relationship cardinality " + j["cardinality"]) if j["kind"] == "relationship" else \
                    "no cardinality in Tableau; many_to_one proposed; set primary keys"
                if j["kind"] == "relationship" and j["cardinality"] == "many_to_many":
                    j["reason"] = ("relationship declares no unique keys (Tableau's default), so many_to_many; "
                                   "confirm the cardinality and the primary keys")
                if not (j.get("on") and len(j["on"]) == 2 and all(unq(x) for x in j["on"])):
                    j["reason"] += "; the relationship has no key fields in Tableau, sql_on left for a person"
            for f in d["fields"]:
                self.classify_field(d, f)

    def classify_field(self, d, f):
        k = f["field_kind"]
        if f.get("_remote"):
            f["class"], f["reason"] = "mechanical", ""
            return
        if k == "parameter":
            f["class"], f["reason"] = "assisted", "LookML parameter; references use {% parameter %}"
            return
        if k == "group":
            f["class"], f["reason"] = "assisted", "group becomes a CASE dimension"
            return
        if k == "bin":
            f["class"], f["reason"] = "assisted", "bin becomes a FLOOR(x / size) * size dimension"
            return
        if k == "set":
            f["class"], f["reason"] = "assisted", "set: not emitted; becomes a yesno dimension or filter by hand"
            return
        kind, funcs, refs = classify_formula(f["expression"])
        f["_calc_kind"] = kind
        f["references"] = sorted({self.ref_id(d, r) for r in refs})
        if kind == "lod":
            f["class"], f["reason"] = "redesign", "LOD expression: derived table or symmetric aggregate, plan ruling"
        elif kind == "table_calc":
            f["class"], f["reason"] = "redesign", "table calculation: Looker table calculation on the tile, or drop"
        elif kind == "aggregate":
            f["class"], f["reason"] = "assisted", "aggregate calculation: type number measure over emitted measures"
        else:
            f["class"], f["reason"] = "assisted", "row-level calculation translated to SQL"
        unknown = funcs - ROW_FUNCS - AGG_FUNCS - TABLE_CALC
        if unknown and kind in ("row", "aggregate"):
            f["reason"] += f"; function(s) {', '.join(sorted(unknown))} have no SQL mapping"
        if any(r.startswith("[Parameters]") for r in refs):
            f["reason"] += "; references a parameter"

    def ref_id(self, d, token):
        if token.startswith("[Parameters]."):
            return bi_ir.field_id("tableau", self.site, "Parameters", unq(token.split(".", 1)[1]))
        return bi_ir.field_id("tableau", self.site, d["name"], unq(token.split("].[")[-1] if "].[" in token else token))

    # -- translation --------------------------------------------------------
    def translate(self, wb, d, f):
        """Return (sql, measure_refs) or raise Unsupported."""
        aggregate = f.get("_calc_kind") == "aggregate"
        needed = []

        def resolve(token, ctx):
            if token.startswith("[Parameters]."):
                p = wb["params"].get(unq(token.split(".", 1)[1])) if wb else None
                if p is None:
                    raise Unsupported(f"unknown parameter {token}")
                return f"{{% parameter {bi_ir.slug(p['label'])} %}}", p["data_type"]
            g = self.field(d, unq(token))
            if g is None:
                raise Unsupported(f"unknown field {token}")
            if g.get("_remote"):
                if ctx in ("sum", "avg", "min", "max", "countd"):
                    view = self.view_for(d, g["_relation"])
                    needed.append((view, g, ctx))
                    return f"${{{view}.{self.measure_name(g, ctx)}}}", g["data_type"]
                ref, dt, _ = self.column_ref(d, g)
                return ref, dt
            if g["field_kind"] == "calculation" and g.get("_calc_kind") == "row" and g.get("_sql"):
                if ctx != "row":
                    raise Unsupported(f"aggregate over calculated field {token}")
                return f"${{{self.base_view(d)}.{bi_ir.slug(g['label'])}}}", g["data_type"]
            raise Unsupported(f"reference to {g['field_kind']} {token} ({g.get('class')})")

        em = Emitter(resolve, self.dialect, aggregate)
        sql = em.emit(Parser(tokenize(f["expression"])).parse())
        return sql, needed


# ---------------------------------------------------------------------------
# LookML writer
# ---------------------------------------------------------------------------

def param_default(value, ptype: str) -> str:
    """'18.399999999999999' -> '18.4'; '50000.' -> '50000'; strings unquoted and unescaped."""
    v = str(value).strip('"')
    if ptype == "number":
        try:
            f = float(v)
            return str(int(f)) if f.is_integer() else repr(f)
        except ValueError:
            return v.rstrip(".")
    return re.sub(r"\\(.)", r"\1", v)


def quote_col(name: str, dialect: str) -> str:
    """A warehouse column name as SQL: bare when it is a plain identifier, quoted otherwise ('Row ID')."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return f"`{name}`" if dialect == "bigquery" else '"' + name.replace('"', '""') + '"'


def lk_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_estate(est: Estate, model: str, connection: str, only_datasets=None, only_workbooks=None, include_root=""):
    """Return (files: dict path->text, needs_human: list, summary: dict, objects: list, deps: list)."""
    views = {}          # view -> {"source": ..., "dims": {}, "measures": {}, "params": {}}
    explores = {}
    needs, deps = [], []
    counts = {}

    def count(construct, cls):
        counts.setdefault(construct, {}).setdefault(cls, 0)
        counts[construct][cls] += 1

    def need(obj_id, construct, cls, reason, proposal=None):
        needs.append({"object": obj_id, "construct": construct, "class": cls, "reason": reason,
                      "proposal": proposal})

    def view(name, d, rel):
        if name not in views:
            if rel["type"] == "custom_sql":
                src = {"derived_sql": rel["sql"]}
            else:
                src = {"table": rel["table"].replace("[", "`").replace("]", "`").replace("`.`", ".")}
            views[name] = {"source": src, "dims": {}, "measures": {}, "params": {}}
        return views[name]

    def dependency_order(fields):
        """Keep the given order, but move each calculation after the calculations it references."""
        by_name = {f["name"]: f for f in fields}
        out, seen = [], set()

        def visit(f, stack):
            if f["name"] in seen or f["name"] in stack:
                return
            stack.add(f["name"])
            if f.get("field_kind") == "calculation":
                for tok in re.findall(r"\[([^\]]+)\]", f.get("expression") or ""):
                    if tok in by_name:
                        visit(by_name[tok], stack)
            stack.discard(f["name"])
            seen.add(f["name"])
            out.append(f)

        for f in fields:
            visit(f, set())
        return out

    def source_ref(d, name):
        """(sql_ref, view, None) for the column or translated row-level calculation a group or bin is built on,
        else (None, None, reason)."""
        col = est.field(d, name)
        if col is None:
            return None, None, f"unknown field [{name}]"
        if col.get("_remote"):
            ref, _, vname = est.column_ref(d, col)
            return ref, vname, None
        if col.get("field_kind") == "calculation" and col.get("_calc_kind") == "row" and col.get("_sql"):
            base = est.base_view(d)
            return f"${{{base}.{bi_ir.slug(col['label'])}}}", base, None
        return None, None, f"built on {col.get('field_kind')} {col['label']!r}, which was not translated"

    def bin_size_parameter(wb, token):
        p = wb["params"].get(unq(token.split(".", 1)[1])) if wb and token.startswith("[Parameters].") else None
        if p is None:
            return None, f"bin size comes from parameter {token}, which is not in this workbook"
        return f"{{% parameter {bi_ir.slug(p['label'])} %}}", None

    wbs = [w for w in est.workbooks if not only_workbooks or w["meta"]["id"] in only_workbooks]
    in_scope = []
    for d in est.datasets:
        if d.get("name") == "Parameters" or d.get("_published_ref") or not d.get("relations"):
            continue
        if only_datasets and d["id"] not in only_datasets:
            continue
        if d.get("workbook") and only_workbooks and not any(d["workbook"] == w["id"] for w in wbs):
            continue
        if not d.get("workbook") and only_workbooks and not any(
                est.dataset_of(x) is d for w in wbs for x in w["datasets"] if x.get("_published_ref")):
            continue
        in_scope.append(d)

    for d in in_scope:
        wb = next((w for w in est.workbooks if w["id"] == d.get("workbook")), None)
        count("dataset", d["class"])
        if d["materialisation"] == "extract":
            need(d["id"], "extract", "redesign", "data source runs on an extract; views read the live tables",
                 "plan: dbt model, live connection, or drop")
        if d["materialisation"] == "file":
            need(d["id"], "file_source", "redesign",
                 f"data source reads a file ({d['connection']['class']}); view sql_table_name is a placeholder",
                 "plan: load the file to the warehouse (dbt seed or pipeline), or drop")
        for rel in d["relations"]:
            vname = est.view_for(d, rel["name"])
            v = view(vname, d, rel)
            if rel["type"] == "custom_sql":
                count("custom_sql", "assisted")
                need(bi_ir.child(d["id"], "relation", rel["name"]), "custom_sql", "assisted",
                     "custom SQL copied verbatim into a derived table; check dialect and references")
        # physical columns
        for f in d["fields"]:
            if not f.get("_remote"):
                continue
            vname = est.view_for(d, f["_relation"])
            v = views[vname]
            n = est.lookml_name(f)
            dt = DATATYPE_DIM.get(f["data_type"], "string")
            entry = {"label": f["label"], "hidden": f["hidden"] or f["field_kind"] == "measure",
                     "type": dt, "sql": f"${{TABLE}}.{quote_col(f['_remote'], est.dialect)}"}
            if dt in ("date", "datetime"):
                entry = {"group": True, "label": f["label"], "type": "time",
                         "timeframes": TIMEFRAMES_TIME if dt == "datetime" else TIMEFRAMES_DATE,
                         "datatype": "timestamp" if dt == "datetime" else "date", "sql": f"${{TABLE}}.{quote_col(f['_remote'], est.dialect)}"}
            prev = v["dims"].get(n)
            if prev is None or (prev.get("label") == f["_remote"] and f["label"] != f["_remote"]):
                v["dims"][n] = entry
            f["target"] = f"looker:{model}:field:{vname}.{n}"
            count("column", "mechanical")
            deps.append({"from": f["id"], "to": f"looker:{model}:view:{vname}", "kind": "contains"})
            if f["field_kind"] == "measure" and f.get("aggregation") in AGG_MEASURE:
                mt, prefix = AGG_MEASURE[f["aggregation"]]
                v["measures"].setdefault(f"{prefix}_{n}", {"type": mt, "sql": f"${{{n}}}", "label": f"{f['label']}",
                                                           "format": f.get("format")})
        # calculated fields: row-level first, so aggregates can reference them
        calcs = [f for f in d["fields"] if not f.get("_remote")]
        order = dependency_order(sorted(calcs, key=lambda f: (0 if f.get("_calc_kind") == "row" else 1, f["name"])))
        base = est.base_view(d)
        for f in order:
            k = f["field_kind"]
            name = bi_ir.slug(f["label"])
            if k == "group":
                ref, vname, why = source_ref(d, unq(f["_column"]))
                if ref is None:
                    count("group", "assisted")
                    need(f["id"], "group", "assisted", f"group not emitted: {why}", f"Tableau: group of {f['_column']}")
                    continue
                whens = " ".join(f"WHEN {ref} IN ({', '.join(repr(v).replace(chr(34), chr(39)) for v in vals)}) THEN '{lab}'"
                                 for lab, vals in f["_bins"])
                views[vname]["dims"][name] = {"label": f["label"], "type": "string", "sql": f"CASE {whens} ELSE {ref} END"}
                f["target"] = f"looker:{model}:field:{vname}.{name}"
                count("group", "assisted")
                continue
            if k == "bin":
                ref, vname, why = source_ref(d, unq(f["expression"]))
                size = f["_size"]
                if ref is not None and f.get("_size_parameter"):
                    size, why = bin_size_parameter(wb, f["_size_parameter"])
                    if size is None:
                        ref = None
                if ref is None:
                    count("bin", "assisted")
                    need(f["id"], "bin", "assisted", f"bin not emitted: {why}",
                         f"Tableau: bin of {f['expression']} size {f['_size'] or f.get('_size_parameter')}")
                    continue
                views[vname]["dims"][name] = {"label": f["label"], "type": "number",
                                              "sql": f"FLOOR({ref} / {size}) * {size}"}
                f["target"] = f"looker:{model}:field:{vname}.{name}"
                count("bin", "assisted")
                continue
            if k == "set":
                count("set", "assisted")
                need(f["id"], "set", "assisted", f["reason"], "yesno dimension listing the members, or a filter")
                continue
            if k != "calculation":
                continue
            ck = f.get("_calc_kind")
            if ck in ("lod", "table_calc"):
                count(ck, "redesign")
                need(f["id"], ck, "redesign", f["reason"], f"Tableau: {f['expression']}")
                continue
            try:
                sql, needed = est.translate(wb, d, f)
            except Unsupported as e:
                count(f"{ck}_calculation", "assisted")
                need(f["id"], f"{ck}_calculation", "assisted", f"not translated: {e}", f"Tableau: {f['expression']}")
                continue
            f["_sql"] = sql
            for vname, g, agg in needed:
                mt, prefix = AGG_MEASURE[agg]
                views[vname]["measures"].setdefault(f"{prefix}_{est.lookml_name(g)}",
                                                    {"type": mt, "sql": f"${{{est.lookml_name(g)}}}", "label": g["label"]})
            if ck == "aggregate":
                views[base]["measures"][name] = {"type": "number", "sql": sql, "label": f["label"], "format": f.get("format")}
            else:
                dt = DATATYPE_DIM.get(f["data_type"], "string")
                if dt in ("date", "datetime"):
                    views[base]["dims"][name] = {"group": True, "label": f["label"], "type": "time",
                                                 "timeframes": TIMEFRAMES_DATE, "datatype": "date", "sql": sql}
                else:
                    views[base]["dims"][name] = {"label": f["label"], "type": dt, "sql": sql}
                if f.get("_role") == "measure" and dt == "number":
                    views[base]["measures"][f"total_{name}"] = {"type": "sum", "sql": f"${{{name}}}", "label": f"Total {f['label']}"}
                    need(f["id"], "row_calculation", "assisted",
                         "row-level numeric calculation that Tableau sums by default: a sum of row values, check it is not a ratio",
                         f"measure total_{name} emitted")
            f["target"] = f"looker:{model}:field:{base}.{name}"
            count(f"{ck}_calculation", "assisted")
            for r in f.get("references", []):
                deps.append({"from": f["id"], "to": r, "kind": "references"})
        # parameters used by this dataset's workbook
        if wb:
            for p in wb["params"].values():
                pname = bi_ir.slug(p["label"])
                ptype = "number" if p["data_type"] in ("real", "integer") else ("yesno" if p["data_type"] == "boolean" else "string")
                entry = {"type": ptype, "label": p["label"], "default_value": param_default(p["expression"], ptype)}
                if p.get("_members"):
                    entry["allowed_values"] = p["_members"]
                views[base]["params"][pname] = entry
                p["target"] = f"looker:{model}:field:{base}.{pname}"
        # explore
        xname = est.model_name(d)
        joins = []
        for j in d["joins"]:
            left = est.view_for(d, j["left"]) if j["kind"] == "physical" else est.view_for(d, next(
                (r["name"] for r in d["relations"] if r["name"] == j["left"]), j["left"]))
            right = est.view_for(d, j["right"]) if j["kind"] == "physical" else est.view_for(d, next(
                (r["name"] for r in d["relations"] if r["name"] == j["right"]), j["right"]))
            on = None
            if j["on"] and len(j["on"]) == 2 and all(unq(x) for x in j["on"]):
                parts = []
                for side, vw in zip(j["on"], (left, right)):
                    tok = side.split("].[")[-1].strip("[]") if "].[" in side else unq(side)
                    fld = est.field(d, unq(side)) if "].[" not in side else None
                    col = fld["_remote"] if fld and fld.get("_remote") else tok
                    parts.append(f"${{{vw}.{bi_ir.slug(col)}}}")
                on = f"{parts[0]} = {parts[1]}"
            jt = {"left": "left_outer", "inner": "inner", "right": "left_outer", "full": "full_outer"}.get(j["type"], "left_outer")
            rel = j["cardinality"] or "many_to_one"
            joins.append({"view": right, "type": jt, "sql_on": on, "relationship": rel})
            count(f"{j['kind']}_join", "assisted")
            need(bi_ir.child(d["id"], "join", f"{left}:{right}"), f"{j['kind']}_join", "assisted", j["reason"],
                 f"relationship: {rel}; set primary_key on {right}")
            deps.append({"from": f"looker:{model}:explore:{xname}", "to": f"looker:{model}:view:{right}", "kind": "joins"})
        if xname in explores:
            need(d["id"], "duplicate_datasource", "assisted",
                 f"same definition as explore {xname} (fingerprint {d.get('fingerprint')}); content uses that explore",
                 "plan: confirm the consolidation ruling")
            continue
        explores[xname] = {"base": base, "label": d["label"], "joins": joins, "dataset": d["id"]}
        deps.append({"from": f"looker:{model}:explore:{xname}", "to": d["id"], "kind": "uses_dataset"})

    # dashboards
    dash_files, objects = {}, []
    for w in wbs:
        for r in w["reports"]:
            if r["blended"]:
                count("blend", "redesign")
                need(r["id"], "blend", "redesign", "worksheet blends two data sources", "model-level join or merged results")
        for a in w["actions"]:
            if a["command"] == "tsc:tsl-filter":
                count("filter_action", "assisted")
                need(bi_ir.child(w["id"], "action", a["name"]), "filter_action", "assisted",
                     "filter action: becomes dashboard filter listen or cross-filtering",
                     f"source sheet {a['worksheet']} on dashboard {a['dashboard']}")
            else:
                count("action", "assisted")
                need(bi_ir.child(w["id"], "action", a["name"]), "action", "assisted", f"{a['command']} action")
        on_dash = {z["name"] for db in w["dashboards"] for z in db["zones"] if z["type"] == "sheet"}
        for r in w["reports"]:
            if r["name"] not in on_dash and not r["blended"]:
                count("worksheet_standalone", "assisted")
                title = f"{r['name']} ({w['name']})"
                one = {"id": r["id"], "name": title, "story": False, "device_layouts": [],
                       "size": {"width": 1000, "height": 800},
                       "zones": [{"zone_id": "1", "type": "sheet", "name": r["name"], "param": None,
                                  "x": 0, "y": 0, "w": 100000, "h": 100000, "text": ""}]}
                text, dropped = emit_dashboard(est, w, one, model, explores, need, count, deps, kind="worksheet")
                if dropped:
                    need(r["id"], "worksheet_standalone", "assisted", "worksheet on no dashboard; its tile was not emitted",
                         "create a Look through the Looker API (looker_content), or drop")
                    continue
                dash_files[f"dashboards/{bi_ir.slug(title)}.dashboard.lookml"] = text
                need(r["id"], "worksheet_standalone", "assisted",
                     "worksheet on no dashboard: emitted as a one-tile LookML dashboard",
                     "keep it, make it a Look through the Looker API (looker_content), or drop")
        for db in w["dashboards"]:
            if db["story"]:
                count("story", "drop")
                need(db["id"], "story", "drop", "story: recreate by hand")
                continue
            text, dropped = emit_dashboard(est, w, db, model, explores, need, count, deps)
            dash_files[f"dashboards/{bi_ir.slug(db['name'])}.dashboard.lookml"] = text
            if db["device_layouts"]:
                count("device_layout", "drop")
                need(db["id"], "device_layout", "drop", f"device layouts dropped: {', '.join(db['device_layouts'])}")

    # Symmetric aggregates need a primary key on every joined view. Tableau records none; a single *_pk
    # column is proposed as the key (a naming convention, so it is a needs_human item to confirm).
    joined = {j["view"] for x in explores.values() for j in x["joins"]} | {x["base"] for x in explores.values() if x["joins"]}
    for vname in sorted(views):
        pks = [n for n, dm in views[vname]["dims"].items() if n.endswith("_pk") and not dm.get("group")]
        if len(pks) == 1:
            views[vname]["dims"][pks[0]]["primary_key"] = True
            count("primary_key", "assisted")
            need(f"looker:{model}:view:{vname}", "primary_key", "assisted",
                 f"primary key proposed from the column name {pks[0]}; confirm it is unique")
        elif vname in joined:
            count("primary_key", "assisted")
            need(f"looker:{model}:view:{vname}", "primary_key", "assisted",
                 "joined view with no primary key: totals across joins are wrong until one is set")

    # include_root: a folder in the client's repo that holds this output, so the model includes only these
    # views and dashboards (an existing project's /views/ would otherwise be pulled in, with name clashes)
    root = f"{include_root.strip('/')}/" if include_root.strip("/") else ""
    files = {}
    for vname in sorted(views):
        files[f"{root}views/{vname}.view.lkml"] = render_view(vname, views[vname])
    files[f"models/{model}.model.lkml"] = render_model(model, connection, explores, root)
    files.update({f"{root}{k}": v for k, v in dash_files.items()})
    needs.sort(key=lambda n: (n["object"], n["construct"]))
    summary = {"converter": "twb_to_lookml", "version": VERSION, "dialect": est.dialect, "model": model,
               "counts": {k: dict(sorted(v.items())) for k, v in sorted(counts.items())},
               "views": len(views), "explores": len(explores), "dashboards": len(dash_files),
               "needs_human": len(needs)}
    return files, needs, summary, deps


def instance_field(est, w, r, ds_name, inst_name):
    """Map a worksheet column instance to a LookML field name, or (None, reason)."""
    ds = w["ds_by_name"].get(ds_name)
    if ds is None:
        return None, f"unknown data source {ds_name}"
    d = est.dataset_of(ds)
    deriv, col, _ = column_instance(inst_name)
    f = est.field(d, col)
    if f is None:
        return None, f"unknown field {col}"
    if f.get("class") == "redesign":
        return None, f"field {f['label']} is {f['reason'].split(':')[0]}"
    target = f.get("target")
    if not target:
        return None, f"field {f['label']} was not emitted"
    vf = target.split(":field:")[1]
    vname, fname = vf.split(".")
    dv = DERIVATION.get((deriv or "none").lower(), "unknown")
    if f.get("_remote"):
        if f["data_type"] in ("date", "datetime"):
            tf = {"year": "year", "quarter": "quarter", "month": "month", "week": "week", "date": "date", None: "date"}.get(dv)
            return (f"{vname}.{fname}_{tf}", None) if tf else (None, f"date derivation {deriv}")
        if dv is None:
            return f"{vname}.{fname}", None
        if dv in AGG_MEASURE:
            return f"{vname}.{est.measure_name(f, dv)}", None
        return None, f"derivation {deriv} has no mapping"
    if dv in (None, "user"):
        return f"{vname}.{fname}", None
    if dv == "sum" and f.get("_role") == "measure":
        return f"{vname}.total_{fname}", None
    return None, f"derivation {deriv} on calculated field {f['label']}"


def emit_dashboard(est, w, db, model, explores, need, count, deps, kind="dashboard"):
    width, height = db["size"]["width"], db["size"]["height"]
    rows_total = 24 * height / width
    reports = {r["name"]: r for r in w["reports"]}
    elements, filters, dropped = [], [], []
    sheet_fields = {}

    def pos(z):
        col = min(23, max(0, round(z["x"] / 100000 * 24)))
        wd = max(1, min(24 - col, round(z["w"] / 100000 * 24)))
        row = max(0, round(z["y"] / 100000 * rows_total))
        ht = max(1, round(z["h"] / 100000 * rows_total))
        return {"row": row, "col": col, "width": wd, "height": ht}

    for z in sorted(db["zones"], key=lambda z: (z["y"], z["x"], z["zone_id"])):
        t = z["type"]
        if t == "text":
            elements.append({"name": f"text_{z['zone_id']}", "type": "text", "title_text": z["text"], **pos(z)})
            count("text_zone", "mechanical")
            continue
        if t == "filter":
            continue
        if t != "sheet":
            dropped.append(f"{t} zone {z['zone_id']}")
            count(f"{t}_zone", "drop")
            need(bi_ir.child(db["id"], "zone", z["zone_id"]), f"{t}_zone", "drop", f"{t} zone not migrated")
            continue
        r = reports.get(z["name"])
        if r is None:
            continue
        if r["blended"]:
            dropped.append(f"sheet {r['name']} (blend)")
            continue
        insts = {(i["datasource"], i["instance"]) for i in r["query"]["instances"]}
        fields, problems = [], []
        ordered = [(ds, inst) for ds, inst in r["query"]["rows"] + r["query"]["cols"]]
        ordered += [tuple(c[1:-1].split("].[", 1)) for _, c in r["query"]["encodings"] if c]
        ordered = [(ds, inst if inst.startswith("[") else f"[{inst}") for ds, inst in ordered]
        ordered = [(ds, inst if inst.endswith("]") else inst + "]") for ds, inst in ordered]
        for ds, inst in ordered:
            fld, why = instance_field(est, w, r, ds, inst)
            if fld and fld not in fields:
                fields.append(fld)
            elif why:
                problems.append(why)
        ds0 = r["datasets"][0] if r["datasets"] else None
        d = est.dataset_of(w["ds_by_name"][ds0]) if ds0 in w["ds_by_name"] else None
        xname = est.model_name(d) if d else None
        if problems or not fields or xname not in explores:
            reason = "; ".join(problems) or "no mapped fields"
            dropped.append(f"sheet {r['name']} ({reason})")
            count("worksheet", "redesign" if any("LOD" in p or "table" in p for p in problems) else "assisted")
            need(r["id"], "worksheet", "assisted", f"tile not emitted: {reason}")
            continue
        mark = r["visualisation"]["mark"].lower()
        dims_on_rows = any(column_instance(i)[0] in ("none", None) for _, i in r["query"]["rows"])
        if mark == "bar" and dims_on_rows:
            vtype = "looker_bar"
        elif mark == "automatic" and len(fields) == 1:
            vtype = "single_value"
        else:
            vtype = MARK_TYPE.get(mark, "looker_grid")
        el = {"name": bi_ir.slug(r["name"]), "title": r["name"], "model": model, "explore": xname,
              "type": vtype, "fields": fields}
        sorts = []
        for col, direction, using in r["query"]["sorts"]:
            if using:
                ds_u, inst_u = using[1:-1].split("].[", 1)
                fu, _ = instance_field(est, w, r, ds_u, f"[{inst_u}]")
                if fu:
                    sorts.append(f"{fu} {'desc' if (direction or '').upper() == 'DESC' else 'asc'}")
        if sorts:
            el["sorts"] = sorts
        el_filters = {}
        for fd in r["query"].get("filter_details", []):
            col = fd["column"] or ""
            if "].[" not in col or fd.get("value", "") is None:
                continue
            ds_f, inst_f = col[1:-1].split("].[", 1)
            ff, why = instance_field(est, w, r, ds_f, f"[{inst_f}]")
            if ff and fd.get("value"):
                el_filters[ff] = fd["value"]
            else:
                need(r["id"], "sheet_filter", "assisted",
                     f"sheet filter on {inst_f} not migrated: {fd.get('reason') or why}")
        if el_filters:
            el["filters"] = el_filters
        el["limit"] = 500
        el.update(pos(z))
        elements.append(el)
        sheet_fields[r["name"]] = (xname, fields, r)
        count("worksheet", "mechanical")
        if db["id"] != r["id"]:          # a one-tile dashboard for a standalone sheet is the sheet itself
            deps.append({"from": db["id"], "to": r["id"], "kind": "contains"})
    for z in db["zones"]:
        if z["type"] != "filter" or not z["param"]:
            continue
        ds, inst = z["param"][1:-1].split("].[", 1)
        anyr = next(iter(w["reports"]), None)
        fld, why = instance_field(est, w, anyr, ds, f"[{inst}]")
        if not fld:
            need(bi_ir.child(db["id"], "zone", z["zone_id"]), "quick_filter", "assisted", f"filter not emitted: {why}")
            continue
        listen = {}
        for name, (xname, fields, r) in sorted(sheet_fields.items()):
            if any(c == z["param"] for c in r["query"]["filters"]):
                listen[bi_ir.slug(name)] = fld
        title = fld.split(".")[1].replace("_", " ").title()
        filters.append({"name": title, "title": title, "type": "field_filter", "default_value": "",
                        "model": model, "explore": sheet_fields[next(iter(sorted(sheet_fields)))][0] if sheet_fields else None,
                        "field": fld, "listens_to_filters": []})
        for el in elements:
            if el.get("name") in listen:
                el.setdefault("listen", {})[title] = listen[el["name"]]
        count("quick_filter", "mechanical")
    doc = [{"dashboard": bi_ir.slug(db["name"]), "title": db["name"], "layout": "newspaper",
            "preferred_viewer": "dashboards-next", "description": f"Migrated from Tableau {kind} {db['name']} (twb_to_lookml {VERSION}, experimental)",
            **({"filters": filters} if filters else {}), "elements": elements}]
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000), dropped


def render_view(name, v):
    out = [f"view: {name} {{"]
    src = v["source"]
    if "table" in src:
        out.append(f"  sql_table_name: {src['table']} ;;")
    else:
        out.append("  derived_table: {")
        out.append(f"    sql: {src['derived_sql']} ;;")
        out.append("  }")
    for pname in sorted(v["params"]):
        p = v["params"][pname]
        out += ["", f"  parameter: {pname} {{", f"    type: {p['type'] if p['type'] != 'number' else 'number'}",
                f"    label: {lk_str(p['label'])}"]
        for av in p.get("allowed_values", []):
            out += ["    allowed_value: {", f"      label: {lk_str(av)}", f"      value: {lk_str(av)}", "    }"]
        out += [f"    default_value: {lk_str(p['default_value'])}", "  }"]
    for dname in sorted(v["dims"]):
        dm = v["dims"][dname]
        if dm.get("group"):
            out += ["", f"  dimension_group: {dname} {{", "    type: time",
                    f"    timeframes: [{', '.join(dm['timeframes'])}]", f"    datatype: {dm['datatype']}",
                    f"    label: {lk_str(dm['label'])}", f"    sql: {dm['sql']} ;;", "  }"]
            continue
        out += ["", f"  dimension: {dname} {{"]
        if dm.get("primary_key"):
            out.append("    primary_key: yes")
        out += [f"    type: {dm['type']}", f"    label: {lk_str(dm['label'])}"]
        if dm.get("hidden"):
            out.append("    hidden: yes")
        out += [f"    sql: {dm['sql']} ;;", "  }"]
    for mname in sorted(v["measures"]):
        m = v["measures"][mname]
        out += ["", f"  measure: {mname} {{", f"    type: {m['type']}", f"    label: {lk_str(m['label'])}",
                f"    sql: {m['sql']} ;;"]
        fmt = value_format(m.get("format"))
        if fmt:
            out.append(f"    value_format_name: {fmt}")
        out.append("  }")
    out.append("}")
    return "\n".join(out) + "\n"


def value_format(tableau_fmt):
    if not tableau_fmt:
        return None
    if tableau_fmt.startswith("p"):
        return "percent_1" if ".0" in tableau_fmt else "percent_0"
    if tableau_fmt.startswith("c"):
        return "gbp" if "£" in tableau_fmt else ("eur" if "€" in tableau_fmt else "usd")
    return None


def render_model(model, connection, explores, root=""):
    out = [f"connection: {lk_str(connection)}", "", f'include: "/{root}views/*.view.lkml"',
           f'include: "/{root}dashboards/*.dashboard.lookml"']
    for x in sorted(explores):
        e = explores[x]
        out += ["", f"explore: {x} {{", f"  label: {lk_str(e['label'])}", f"  view_name: {e['base']}" if x != e["base"] else None]
        out = [o for o in out if o is not None]
        for j in e["joins"]:
            out += [f"  join: {j['view']} {{", f"    type: {j['type']}", f"    relationship: {j['relationship']}",
                    f"    sql_on: {j['sql_on']} ;;" if j["sql_on"] else "    # sql_on: needs_human", "  }"]
        out.append("}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Audit outputs
# ---------------------------------------------------------------------------
MODEL_COLUMNS = ["object_type", "object_uri", "dataset", "model", "field_name", "label", "construct",
                 "translation_class", "complexity", "reason", "source_file", "workbook", "fingerprint"]
CONTENT_COLUMNS = ["object_type", "object_uri", "id", "title", "workbook", "project", "owner", "last_viewed",
                   "views_90d", "source_updated_at", "tile_count", "dataset_refs", "translation_class", "reason",
                   "views_total", "view_luid"]
FP_COLUMNS = ["fingerprint", "member_count", "members", "workbooks", "captions", "proposed_model"]
COMPLEXITY = {"mechanical": "Low", "assisted": "Medium", "redesign": "High", "drop": "Low"}


def audit_rows(est: Estate, usage: dict):
    model_rows, content_rows = [], []
    for d in sorted(est.datasets, key=lambda x: x["id"]):
        if d.get("name") == "Parameters":
            continue
        model_rows.append({"object_type": "dataset", "object_uri": d["id"], "dataset": d["label"],
                           "model": est.model_name(d) if d.get("relations") else "", "construct": "published_reference"
                           if d.get("_published_ref") else {"extract": "extract", "file": "file_source"}.get(d["materialisation"], "dataset"),
                           "translation_class": d.get("class", "mechanical"),
                           "complexity": COMPLEXITY[d.get("class", "mechanical")], "reason": d.get("reason", ""),
                           "source_file": d["source"]["file"], "workbook": d.get("workbook") or "",
                           "fingerprint": d.get("fingerprint") or ""})
        for j in d.get("joins", []):
            model_rows.append({"object_type": "join", "object_uri": bi_ir.child(d["id"], "join", f"{j['left']}:{j['right']}"),
                               "dataset": d["label"], "construct": f"{j['kind']}_join", "translation_class": j.get("class", "assisted"),
                               "complexity": "Medium", "reason": j.get("reason", ""), "source_file": d["source"]["file"],
                               "workbook": d.get("workbook") or ""})
        for f in sorted(d["fields"], key=lambda x: x["name"]):
            construct = "column" if f.get("_remote") else (f"{f.get('_calc_kind')}_calculation" if f["field_kind"] == "calculation" else f["field_kind"])
            cls = f.get("class", "mechanical")
            model_rows.append({"object_type": "field", "object_uri": f["id"], "dataset": d["label"],
                               "model": est.model_name(d) if d.get("relations") else "", "field_name": f["name"],
                               "label": f["label"], "construct": construct, "translation_class": cls,
                               "complexity": COMPLEXITY[cls], "reason": f.get("reason", ""),
                               "source_file": d["source"]["file"], "workbook": d.get("workbook") or ""})
    for w in sorted(est.workbooks, key=lambda x: x["id"]):
        m = w["meta"]
        u = usage.get(m["id"], {})
        luids = {v["name"]: v["id"] for v in m.get("views") or []}
        per_view = u.get("views", {})

        def total(name):
            return per_view.get(luids.get(name), "") if per_view else ""

        content_rows.append({"object_type": "workbook", "object_uri": w["id"], "id": m["id"], "title": m.get("name"),
                             "project": m.get("project") or "", "owner": m.get("owner") or "",
                             "last_viewed": u.get("last_viewed", "unknown"), "views_90d": u.get("views_90d", "unknown"),
                             "views_total": u.get("views_total", ""),
                             "source_updated_at": m.get("updated_at") or "", "translation_class": "", "reason": ""})
        for r in sorted(w["reports"], key=lambda x: x["name"]):
            cls, reason = ("redesign", "blend") if r["blended"] else ("mechanical", "")
            content_rows.append({"object_type": "sheet", "object_uri": r["id"], "id": r["name"], "title": r["name"],
                                 "workbook": w["id"], "dataset_refs": ";".join(r["datasets"]),
                                 "view_luid": luids.get(r["name"], ""), "views_total": total(r["name"]),
                                 "translation_class": cls, "reason": reason})
        for db in sorted(w["dashboards"], key=lambda x: x["name"]):
            kind = "story" if db["story"] else "dashboard"
            sheets = [z for z in db["zones"] if z["type"] == "sheet"]
            content_rows.append({"object_type": kind, "object_uri": db["id"], "id": db["name"], "title": db["name"],
                                 "workbook": w["id"], "tile_count": len(sheets),
                                 "view_luid": luids.get(db["name"], ""), "views_total": total(db["name"]),
                                 "translation_class": "drop" if db["story"] else "mechanical",
                                 "reason": "story: recreate by hand" if db["story"] else
                                 ("device layouts dropped" if db["device_layouts"] else "")})
    return model_rows, content_rows


def fingerprint_rows(est: Estate):
    groups = {}
    for d in est.datasets:
        if d.get("fingerprint"):
            groups.setdefault(d["fingerprint"], []).append(d)
    rows = []
    for fp in sorted(groups):
        ms = sorted(groups[fp], key=lambda x: x["id"])
        captions = sorted({m["label"] for m in ms})
        rows.append({"fingerprint": fp, "member_count": len(ms), "members": ";".join(m["id"] for m in ms),
                     "workbooks": ";".join(sorted({m.get("workbook") or "published" for m in ms})),
                     "captions": ";".join(captions), "proposed_model": bi_ir.slug(min(captions, key=lambda c: (len(c), c)))})
    return rows


def ir_objects(est: Estate, model_out=None):
    objs = []
    for d in est.datasets:
        if d.get("name") == "Parameters":
            continue
        o = {k: v for k, v in d.items() if not k.startswith("_")}
        o["fields"] = [{k: v for k, v in f.items() if not k.startswith("_")} for f in d["fields"]]
        if d.get("_extract"):
            objs.append({"id": bi_ir.child(d["id"], "extract", "main"), "kind": "extract", "name": f"{d['name']} extract",
                         "source": {"file": d["source"]["file"], "fragment": "<extract>"}, "dataset": d["id"],
                         "last_refreshed": d["_extract"]["last_refreshed"], "class": "redesign",
                         "reason": "extract disposition: plan ruling"})
        objs.append(o)
    for w in est.workbooks:
        for r in w["reports"]:
            o = {k: v for k, v in r.items()}
            o["class"] = "redesign" if r["blended"] else "mechanical"
            objs.append(o)
        for db in w["dashboards"]:
            objs.append({"id": db["id"], "kind": "dashboard", "name": db["name"], "source": db["source"],
                         "workbook": w["id"], "size": db["size"],
                         "tiles": [{"id": bi_ir.child(db["id"], "zone", z["zone_id"]), "report": bi_ir.child(w["id"], "sheet", z["name"]) if z["type"] == "sheet" else None,
                                    "position": {k: z[k] for k in ("x", "y", "w", "h")}} for z in db["zones"]],
                         "actions": [a["name"] for a in w["actions"] if a["dashboard"] == db["name"]],
                         "dropped": db["device_layouts"], "class": "drop" if db["story"] else "mechanical"})
    return objs


def write_csv(path: Path, rows, columns):
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    wr.writeheader()
    for r in rows:
        wr.writerow({c: r.get(c, "") for c in columns})
    path.write_text(buf.getvalue())


def write_jsonl(path: Path, rows):
    uniq = sorted({json.dumps(r, sort_keys=True) for r in rows})
    path.write_text("".join(u + "\n" for u in uniq))


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------
TABLEAU_ISMS = [
    (re.compile(r"\{\s*(FIXED|INCLUDE|EXCLUDE)\b", re.I), "LOD expression"),
    (re.compile(r"\b(ZN|IIF|COUNTD|DATETRUNC|ATTR|WINDOW_\w+|RUNNING_\w+)\s*\(", re.I), "Tableau function"),
    (re.compile(r"\[Parameters\]\."), "Tableau parameter reference"),
    (re.compile(r"(?<![$\w])\[[A-Za-z_][^\]\n]*\](?!\s*[,:])"), "Tableau field reference [..]"),
]


def lint(lookml_dir: Path):
    problems = []
    found = sorted(Path(lookml_dir).rglob("*.lkml"))
    if not found:
        return [f"{lookml_dir}: no .lkml files (nothing was converted, or the wrong folder)"]
    for p in found:
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if "sql" not in line:
                continue
            for rx, what in TABLEAU_ISMS:
                if rx.search(line.split("sql", 1)[1]):
                    problems.append(f"{p.relative_to(lookml_dir)}:{i}: {what}: {line.strip()}")
    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("audit", "convert"):
        s = sub.add_parser(name)
        s.add_argument("--snapshot", required=True)
        s.add_argument("--out", required=True)
        s.add_argument("--site")
        s.add_argument("--dialect", default="bigquery", choices=["bigquery", "snowflake"])
        if name == "convert":
            s.add_argument("--model", default="tableau_migration")
            s.add_argument("--connection", default="warehouse")
            s.add_argument("--include-root", default="",
                           help="folder in the target LookML repo for the views and dashboards (default: repo root)")
            s.add_argument("--datasets", default="")
            s.add_argument("--workbooks", default="")
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
        est = Estate(Path(a.snapshot), a.site, a.dialect)
    except (ConvertError, ET.ParseError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd == "audit":
        usage_path = Path(a.snapshot) / "usage.json"
        usage = json.loads(usage_path.read_text()).get("workbooks", {}) if usage_path.exists() else {}
        files, needs, summary, deps = emit_estate(est, "tableau_migration", "warehouse")
        model_rows, content_rows = audit_rows(est, usage)
        write_csv(out / "bi_model_catalog.csv", model_rows, MODEL_COLUMNS)
        write_csv(out / "bi_content_catalog.csv", content_rows, CONTENT_COLUMNS)
        write_csv(out / "datasource_fingerprints.csv", fingerprint_rows(est), FP_COLUMNS)
        write_jsonl(out / "dependencies.jsonl", deps)
        bi_ir.write(out / "ir", ir_objects(est))
        by = {}
        for r in model_rows + content_rows:
            if r.get("translation_class"):
                by[r["translation_class"]] = by.get(r["translation_class"], 0) + 1
        print(f"{len(est.workbooks)} workbooks, {len(est.datasets)} data sources, "
              f"{len(fingerprint_rows(est))} fingerprint groups; classes {dict(sorted(by.items()))} -> {out}")
        return 0
    only_d = {x for x in a.datasets.split(",") if x}
    only_w = {x for x in a.workbooks.split(",") if x}
    files, needs, summary, deps = emit_estate(est, bi_ir.slug(a.model), a.connection, only_d, only_w, a.include_root)
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / "needs_human.json").write_text(json.dumps(needs, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "conversion_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    write_jsonl(out / "dependencies.jsonl", deps)
    bi_ir.write(out / "ir", ir_objects(est))
    print(f"{summary['views']} views, {summary['explores']} explores, {summary['dashboards']} dashboards, "
          f"{summary['needs_human']} needs_human -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

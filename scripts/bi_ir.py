#!/usr/bin/env python3
"""
Tool-neutral BI intermediate representation (wire#287, bi_migration).

One IR shape for every BI migration pair. A reader (one per source tool) turns the
source estate into IR objects; a writer (one per target tool) turns IR objects into
target files; translation rules stay per pair, in wire/bi_pairs/<pair>/.

The schema is wire/schemas/bi_ir-schema.md. This module is its executable form:
object builders, identity helpers, a stable writer and validate(), which fails on any
key the schema does not list, so a tool-shaped key (lookml_type, omni, explore) cannot
creep into the neutral record unnoticed.

Used by wire/scripts/twb_to_lookml.py (Tableau reader, LookML writer, experimental) and
wire/scripts/mb_to_lookml.py (Metabase reader, LookML writer, experimental). wire/scripts/bi_to_omni.py writes Omni
from the same readers' converted model (experimental).
wire/scripts/lookml_to_omni.py keeps its own IR in 4.2.x; moving it onto this module
is a later, deliberate change (it would regenerate the Looker to Omni expected files).

Usage:
    python3 wire/scripts/bi_ir.py validate <ir_dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

SCHEMA_VERSION = "1.0"

# identity: <tool>:<scope>:<kind>:<id>[/<kind>:<id>]...
IDENTITY = re.compile(r"^[a-z][a-z0-9_]*:[^:/\s]+:[a-z_]+:[^\s]+$")
TOOLS = {"tableau", "looker", "lookerstudio", "omni", "metabase"}

CLASSES = {"mechanical", "assisted", "redesign", "drop"}

COMMON = {"id", "kind", "name", "label", "description", "class", "reason", "source", "unsupported"}
REQUIRED_COMMON = {"id", "kind", "name", "source"}

KINDS = {
    "dataset": COMMON | {"connection", "relations", "joins", "fields", "fingerprint", "published",
                         "materialisation", "workbook", "access_rules"},
    "model": COMMON | {"base_dataset", "datasets", "joins", "fingerprint_group"},
    "dashboard": COMMON | {"workbook", "size", "tiles", "controls", "actions", "dropped"},
    "report": COMMON | {"workbook", "datasets", "query", "visualisation", "blended"},
    "folder": COMMON | {"parent", "owner"},
    "schedule": COMMON | {"target", "frequency", "owner"},
    "extract": COMMON | {"dataset", "last_refreshed", "refresh_schedule"},
}

FIELD_KEYS = {"id", "name", "label", "description", "field_kind", "source_type", "expression",
              "data_type", "aggregation", "format", "hidden", "key", "class", "reason", "references",
              "target", "dataset"}
FIELD_KINDS = {"dimension", "measure", "parameter", "group", "bin", "set", "calculation"}
JOIN_KEYS = {"left", "right", "type", "on", "cardinality", "class", "reason", "kind"}
TILE_KEYS = {"id", "report", "position", "class", "reason"}
SOURCE_KEYS = {"file", "fragment", "sha256", "updated_at"}

# Keys that belong to one tool's vocabulary and must not appear in the neutral record.
FORBIDDEN = {"lookml_type", "omni", "explore", "explores", "topic", "topics", "view_name",
             "explore_name", "sql_table_name", "workbook_xml"}


def part(text) -> str:
    """Percent-encode one identity part: names may hold spaces, slashes and colons."""
    return quote(str(text), safe="._-()")


def identity(tool: str, scope: str, *parts) -> str:
    """identity("tableau", "halcyon", "workbook", "abc", "sheet", "Sales by Region")
    -> tableau:halcyon:workbook:abc/sheet:Sales%20by%20Region"""
    if tool not in TOOLS:
        raise ValueError(f"unknown tool {tool!r}")
    if not parts or len(parts) % 2:
        raise ValueError("identity needs kind/id pairs")
    segs = [f"{parts[i]}:{part(parts[i + 1])}" for i in range(0, len(parts), 2)]
    return f"{tool}:{part(scope)}:" + "/".join(segs)


def child(parent: str, kind: str, ident) -> str:
    """child("tableau:s:workbook:abc", "sheet", "Sales by Region") -> .../sheet:Sales%20by%20Region"""
    return f"{parent}/{kind}:{part(ident)}"


def field_id(tool: str, scope: str, dataset: str, name: str) -> str:
    """Field identity <tool>:<scope>:field:<dataset>:<internal name>, both parts encoded."""
    return f"{tool}:{part(scope)}:field:{part(dataset)}:{part(name)}"


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s or "unnamed"


def obj(kind: str, ident: str, name: str, source: dict, **extra) -> dict:
    o = {"id": ident, "kind": kind, "name": name, "source": source}
    o.update({k: v for k, v in extra.items() if v is not None})
    return o


def write(ir_dir: Path, objects) -> list:
    """Write one JSON file per object under ir_dir/<kind>s/<slug>.json. Returns the paths."""
    paths = []
    for o in sorted(objects, key=lambda x: (x["kind"], x["id"])):
        d = ir_dir / f"{o['kind']}s"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{slug(o['id'].split(':', 2)[2])}.json"
        p.write_text(json.dumps(o, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        paths.append(p)
    return paths


def _check_keys(where, d, allowed, errors):
    for k in d:
        if k in FORBIDDEN:
            errors.append(f"{where}: tool-specific key {k!r} is not allowed in the neutral IR")
        elif k not in allowed:
            errors.append(f"{where}: key {k!r} is not in the schema")


def validate_object(o: dict, where: str = "") -> list:
    errors = []
    kind = o.get("kind")
    if kind not in KINDS:
        return [f"{where}: unknown kind {kind!r}"]
    _check_keys(where, o, KINDS[kind], errors)
    for k in REQUIRED_COMMON:
        if k not in o:
            errors.append(f"{where}: missing {k!r}")
    if not IDENTITY.match(str(o.get("id", ""))) or o.get("id", "").split(":")[0] not in TOOLS:
        errors.append(f"{where}: bad identity {o.get('id')!r}")
    if "class" in o and o["class"] not in CLASSES:
        errors.append(f"{where}: bad class {o['class']!r}")
    if isinstance(o.get("source"), dict):
        _check_keys(f"{where}.source", o["source"], SOURCE_KEYS, errors)
        if "fragment" not in o["source"] and "file" not in o["source"]:
            errors.append(f"{where}.source: needs file or fragment (the raw source is kept on every object)")
    for i, f in enumerate(o.get("fields", []) or []):
        w = f"{where}.fields[{i}]"
        _check_keys(w, f, FIELD_KEYS, errors)
        if f.get("field_kind") not in FIELD_KINDS:
            errors.append(f"{w}: bad field_kind {f.get('field_kind')!r}")
        if "class" in f and f["class"] not in CLASSES:
            errors.append(f"{w}: bad class {f['class']!r}")
    for i, j in enumerate(o.get("joins", []) or []):
        _check_keys(f"{where}.joins[{i}]", j, JOIN_KEYS, errors)
    for i, t in enumerate(o.get("tiles", []) or []):
        _check_keys(f"{where}.tiles[{i}]", t, TILE_KEYS, errors)
    return errors


def validate(ir_dir: Path) -> list:
    errors = []
    files = sorted(Path(ir_dir).rglob("*.json"))
    if not files:
        return [f"{ir_dir}: no IR files"]
    for f in files:
        try:
            o = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f}: not JSON ({e})")
            continue
        errors += validate_object(o, str(f.relative_to(ir_dir)))
    return errors


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[0] != "validate":
        print(__doc__)
        return 2
    errs = validate(Path(argv[1]))
    for e in errs:
        print("ERROR", e)
    print(f"{'FAIL' if errs else 'PASS'}: {argv[1]}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())

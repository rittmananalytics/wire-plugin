#!/usr/bin/env python3
"""
Structural validation of an SMML semantic model tree.

Not a substitute for OAC's own consistency check — it catches the errors
worth catching before import: missing required properties, and dangling
fully-qualified-name references (a join/mapping/presentation column pointing
at an object that isn't there).

Every SMML object is wrapped in a singular key matching its type, e.g.
{"physicalTable": {"name": "DIM_DATE", ...}}. This validator unwraps that
before checking anything — see references/smml-schema.md.

A physical table *alias* (role-playing dimension) has a "sourceTable" and no
"physicalColumns" of its own — but per a real OAC export, its inherited
columns are still addressed under the alias's own name
(physicalColumn:DB.SCHEMA.<alias-name>.<col>), not the base table's name.
This validator resolves that inheritance before checking references, rather
than flagging every alias-column reference as dangling.

Usage:  python3 validate_smml.py <smml_dir>
Exit code 0 = clean, 1 = problems.
"""
import json, os, re, sys

REF = re.compile(r"^(physicalTable|physicalColumn|logicalTable|logicalColumn|"
                 r"businessModel|subjectArea|presentationTable|presentationColumn):")

WRAPPER_KEYS = {"database", "schema", "physicalTable", "businessModel",
                "logicalTable", "subjectArea", "presentationTable"}


def esc(p):
    return str(p).replace(".", "\\.")


def parse_fqn(s):
    """'physicalTable:A.B.C\\.D' -> ['A', 'B', 'C.D'] (unescaping \\. within a segment)."""
    _, path = s.split(":", 1)
    parts, cur, i = [], "", 0
    while i < len(path):
        if path[i] == "\\" and i + 1 < len(path) and path[i + 1] == ".":
            cur += "."
            i += 2
        elif path[i] == ".":
            parts.append(cur)
            cur = ""
            i += 1
        else:
            cur += path[i]
            i += 1
    parts.append(cur)
    return parts


def load(path):
    with open(path) as f:
        return json.load(f)


def unwrap(obj, fp):
    """Every SMML object is {"<type>": {...}} — return (type, body) or (None, obj) if unwrapped."""
    if isinstance(obj, dict) and len(obj) == 1:
        key = next(iter(obj))
        if key in WRAPPER_KEYS:
            return key, obj[key]
    return None, obj


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


def main(root):
    available, errors = set(), []
    base_columns = {}   # (db, schema, table) -> [column names]
    pending_aliases = []  # (fp, db, schema, alias_name, sourceTable_fqn)

    def add(*parts):
        available.add(parts[0] + ":" + ".".join(esc(p) for p in parts[1:]))

    files = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if n.endswith(".json"):
                files.append(os.path.join(dirpath, n))

    # Pass 1 — register every object and its columns as available FQNs
    for fp in files:
        rel = os.path.relpath(fp, root).split(os.sep)
        layer = rel[0]
        raw = load(fp)
        wrapper, obj = unwrap(raw, fp)
        if wrapper is None:
            errors.append(f"{fp}: not wrapped in a singular type key (e.g. {{'physicalTable': {{...}}}})")
            continue
        name = obj.get("name")
        if not name:
            errors.append(f"{fp}: missing required 'name'")
            continue
        is_alias = wrapper == "physicalTable" and "sourceTable" in obj and "physicalColumns" not in obj
        if layer == "physical":
            if len(rel) == 3:      # physical/<DB>/<SCHEMA>.json
                add("schema", rel[1], name)
            elif len(rel) == 4:    # physical/<DB>/<SCHEMA>/<TBL>.json
                db, sch = rel[1], rel[2]
                add("physicalTable", db, sch, name)
                if is_alias:
                    pending_aliases.append((fp, db, sch, name, obj["sourceTable"]))
                elif "physicalColumns" not in obj:
                    errors.append(f"{fp}: physical table missing 'physicalColumns' (and isn't an alias — no 'sourceTable')")
                else:
                    cols = [c["name"] for c in obj.get("physicalColumns", [])]
                    base_columns[(db, sch, name)] = cols
                    for cn in cols:
                        add("physicalColumn", db, sch, name, cn)
            else:
                add("database", name)
        elif layer == "logical":
            if len(rel) == 3:      # logical/<BM>/<LT>.json
                bm = rel[1]
                add("logicalTable", bm, name)
                if "type" not in obj:
                    errors.append(f"{fp}: logical table missing required 'type'")
                if "logicalColumns" not in obj:
                    errors.append(f"{fp}: logical table missing 'logicalColumns'")
                for c in obj.get("logicalColumns", []):
                    add("logicalColumn", bm, name, c["name"])
            else:
                add("businessModel", name)
        elif layer == "presentation":
            if len(rel) == 3:      # presentation/<SA>/<PT>.json
                sa = rel[1]
                add("presentationTable", sa, name)
                for c in obj.get("presentationColumns", []):
                    add("presentationColumn", sa, name, c["name"])
            else:
                add("subjectArea", name)

    # Pass 1b — resolve alias tables: inherit the source table's columns,
    # addressed under the alias's own name (ground-truth behavior).
    for fp, db, sch, alias_name, source_ref in pending_aliases:
        parts = parse_fqn(source_ref)
        if len(parts) != 3:
            errors.append(f"{fp}: alias 'sourceTable' isn't a physicalTable:<db>.<schema>.<table> reference -> {source_ref}")
            continue
        cols = base_columns.get(tuple(parts))
        if cols is None:
            errors.append(f"{fp}: alias sourceTable not found among physical tables -> {source_ref}")
            continue
        for cn in cols:
            add("physicalColumn", db, sch, alias_name, cn)

    # Pass 2 — every FQN reference must resolve
    for fp in files:
        _, obj = unwrap(load(fp), fp)
        for s in walk_strings(obj):
            if REF.match(s) and s not in available:
                errors.append(f"{fp}: dangling reference -> {s}")

    if errors:
        print(f"FAIL — {len(errors)} issue(s):")
        for e in errors:
            print("  -", e)
        return 1
    print(f"PASS — {len(files)} SMML files, all references resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "smml"))

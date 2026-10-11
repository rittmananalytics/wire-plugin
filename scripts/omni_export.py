#!/usr/bin/env python3
"""
Omni snapshot for the Omni to Looker pair (bi_migration, pair omni_to_looker). EXPERIMENTAL.

Reads an Omni instance through the Omni CLI (`omni`, a configured profile) and writes a snapshot the
converter (omni_to_lookml.py) reads. Read only: it never writes to Omni.

    snapshot   The shared model's YAML (model file, relationships, topics and the views they reach,
               with the extends chain and every view a dashboard tile queries), Omni's field list for
               those views (views.json, which says which fields are time fields), column types for the
               tables those views read (columns.json, from INFORMATION_SCHEMA, queried through Omni on the
               model's connection; Omni's YAML has none), the connection's dialect and project, and one
               document file per dashboard on the model (documents v2-get).
               Every object carries its SHA-256; documents carry updatedAt. Usage (visits, last viewed)
               stays in inventory.json, so a visit does not change an object file.
    diff       Compare two inventory.json files: content_drifted, model_drifted, removed, new.
    tile-data  Run one dashboard tile's query (as saved, from documents get-queries) and write its rows
               as CSV, raw values, with the tile's field names as the header, unpivoted unless
               --keep-pivots. The source side of parity.

Deterministic for the same Omni state: files are sorted and written with stable formatting.

Usage:
    python3 wire/scripts/omni_export.py snapshot --model-id <uuid> --out <dir> [--profile P]
        [--documents id,id] [--folders name,name] [--all-views] [--columns <columns.json>]
    python3 wire/scripts/omni_export.py diff --old <inventory.json> --new <inventory.json>
    python3 wire/scripts/omni_export.py tile-data --document <id> --query-key <key> --out <file.csv> [--profile P]
        [--branch-id <uuid>]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

VERSION = "0.1.0"
REF = re.compile(r"\$\{\s*(\w+)\.\w+")
SELECT_STAR = re.compile(r"\s*select\s+\*\s+from\s+`?([A-Za-z0-9_.\-]+)`?\s*;?\s*", re.I)
COLUMN_SQL = {
    "bigquery": "SELECT table_schema, table_name, column_name, data_type FROM `{db}.{schema}`.INFORMATION_SCHEMA.COLUMNS "
                "WHERE table_name IN ({tables}) ORDER BY 1, 2, 3",
    "snowflake": "SELECT table_schema, table_name, column_name, data_type FROM {db}.INFORMATION_SCHEMA.COLUMNS "
                 "WHERE table_schema = '{schema_u}' AND table_name IN ({tables_u}) ORDER BY 1, 2, 3",
}


class ExportError(Exception):
    pass


class Cli:
    """The Omni CLI, JSON out. Tests pass a fake with the same call()."""

    def __init__(self, profile: str | None = None):
        self.profile = profile

    def call(self, *args, body: str | None = None):
        cmd = ["omni", *args, "-o", "json", "--compact"]
        if self.profile:
            cmd += ["--profile", self.profile]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except FileNotFoundError:
            raise ExportError("the omni CLI is not installed (brew install exploreomni/tap/omni, then omni config init)")
        if r.returncode != 0:
            raise ExportError(f"omni {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:400]}")
        out = r.stdout.strip()
        if not out:
            return None
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return out

    def base_url(self) -> str:
        """The profile's API endpoint (omni config show), which names the instance."""
        cfg = self.call("config", "show") or {}
        prof = self.profile or cfg.get("defaultProfile")
        return ((cfg.get("profiles") or {}).get(prof) or {}).get("apiEndpoint") or ""

    def version(self) -> str:
        try:
            r = subprocess.run(["omni", "--version"], capture_output=True, text=True, timeout=30)
            return r.stdout.strip().split()[-1] if r.returncode == 0 and r.stdout.strip() else "unknown"
        except FileNotFoundError:
            return "unknown"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def dump(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def view_name_of(path: str) -> str | None:
    for suffix in (".query.view", ".view"):
        if path.endswith(suffix):
            return path[: -len(suffix)].replace("/", "__")
    return None


def records(resp, key):
    if isinstance(resp, dict):
        return resp.get(key) or resp.get("records") or []
    return resp or []


def all_documents(cli):
    out, cursor = [], None
    while True:
        args = ["documents", "list", "--page-size", "100"] + (["--cursor", cursor] if cursor else [])
        resp = cli.call(*args)
        out += records(resp, "records")
        page = (resp or {}).get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return out
        cursor = page.get("nextCursor")


def reachable_views(files: dict, docs: list) -> set:
    """Views a topic, relationship, extends chain, field reference or dashboard tile reaches."""
    parsed = {}
    for p, txt in files.items():
        try:
            parsed[p] = yaml.safe_load(txt) or {}
        except yaml.YAMLError:
            parsed[p] = {}
    by_name = {view_name_of(p): p for p in files if view_name_of(p)}
    want = set()
    for p, y in parsed.items():
        if p.endswith(".topic"):
            want.add(y.get("base_view"))

            def walk(tree):
                for k, v in (tree or {}).items():
                    want.add(k)
                    walk(v)
            walk(y.get("joins"))
            for r in y.get("relationships") or []:
                want |= {r.get("join_from_view"), r.get("join_to_view")}
    for r in parsed.get("relationships") or []:
        if isinstance(r, dict):
            want |= {r.get("join_from_view"), r.get("join_to_view")}
    for d in docs:
        for t in ((d.get("queryPresentations") or {}).get("data") or {}).values():
            q = t.get("query") or {}
            want.add(q.get("table"))
            for f in (q.get("fields") or []) + list((q.get("filters") or {}).keys()):
                if "." in f:
                    want.add(f.split(".")[0])
    want.discard(None)
    todo, seen = sorted(want), set()
    while todo:
        v = todo.pop()
        if v in seen or v not in by_name:
            continue
        seen.add(v)
        y = parsed[by_name[v]]
        nxt = set(y.get("extends") or []) | set(REF.findall(files[by_name[v]]))
        todo += sorted(n for n in nxt if n not in seen)
    return seen


def tables_of(files: dict, default_db: str | None) -> dict:
    """(database, schema) -> table names, for schema views and SELECT * query views."""
    out = {}
    for p, txt in files.items():
        if not view_name_of(p):
            continue
        try:
            y = yaml.safe_load(txt) or {}
        except yaml.YAMLError:
            continue
        if y.get("table_name") and y.get("schema"):
            db, sch, tab = y.get("catalog") or default_db, y["schema"], y["table_name"]
        elif isinstance(y.get("sql"), str) and SELECT_STAR.fullmatch(y["sql"]):
            parts = SELECT_STAR.fullmatch(y["sql"]).group(1).split(".")
            if len(parts) == 3:
                db, sch, tab = parts
            elif len(parts) == 2:
                db, (sch, tab) = default_db, parts
            else:
                continue
        else:
            continue
        if db:
            out.setdefault((db, sch), set()).add(tab)
    return out


def warehouse_columns(cli, model_id: str, dialect: str, tables: dict) -> tuple[dict, list]:
    """Column types from the warehouse's INFORMATION_SCHEMA, run through Omni as SQL on the model's connection."""
    cols, gaps = {}, []
    if dialect not in COLUMN_SQL:
        return cols, [f"column types not read: no INFORMATION_SCHEMA query for dialect {dialect}"]
    for (db, sch), tabs in sorted(tables.items()):
        names = sorted(tabs)
        sql = COLUMN_SQL[dialect].format(db=db, schema=sch, schema_u=sch.upper(),
                                         tables=", ".join(f"'{t}'" for t in names),
                                         tables_u=", ".join(f"'{t.upper()}'" for t in names))
        body = {"query": {"modelId": model_id, "fields": [], "userEditedSQL": sql, "limit": 100000},
                "resultType": "csv", "formatResults": False}
        try:
            text = cli.call("query", "run", "--body", json.dumps(body, sort_keys=True))
        except ExportError as e:
            gaps.append(f"{db}.{sch}: {e}")
            continue
        rows = list(csv.reader(io.StringIO(text if isinstance(text, str) else "")))
        for r in rows[1:]:
            if len(r) >= 4:
                cols.setdefault(f"{r[0]}.{r[1]}".lower(), {})[r[2]] = r[3]
        missing = sorted(t for t in names if f"{sch}.{t}".lower() not in cols)
        if missing:
            gaps.append(f"{db}.{sch}: no columns for {', '.join(missing)}")
    return dict(sorted(cols.items())), gaps


def snapshot(cli, model_id: str, out: Path, documents=None, folders=None, all_views=False, columns=None,
             now: str | None = None, cli_version: str | None = None, base_url: str | None = None,
             read_columns: bool = True) -> dict:
    models = records(cli.call("models", "list"), "records")
    model = next((m for m in models if m.get("id") == model_id), None)
    if model is None:
        raise ExportError(f"model {model_id} not found (omni models list)")
    if model.get("modelKind") not in (None, "SHARED", "SCHEMA"):
        raise ExportError(f"model {model_id} is a {model.get('modelKind')} model: snapshot the shared model")
    conns = records(cli.call("connections", "list"), "connections")
    conn = next((c for c in conns if c.get("id") == model.get("connectionId")), {}) or {}
    yml = cli.call("models", "yaml-get", model_id, "--mode", "combined") or {}
    files = dict(sorted((yml.get("files") or {}).items()))
    docs_meta = [d for d in all_documents(cli) if not d.get("deleted")]
    if documents:
        docs_meta = [d for d in docs_meta if d.get("identifier") in documents]
    if folders:
        docs_meta = [d for d in docs_meta if ((d.get("folder") or {}).get("name") or "") in folders]
    docs, inv_docs, skipped = {}, {}, {}
    for d in sorted(docs_meta, key=lambda x: x.get("identifier")):
        ident = d["identifier"]
        base = {"name": d.get("name"), "folder": (d.get("folder") or {}).get("name"), "updated_at": d.get("updatedAt"),
                "visits": d.get("visits"), "last_viewed_at": d.get("lastViewedAt")}
        if d.get("connectionId") and model.get("connectionId") and d["connectionId"] != model["connectionId"]:
            skipped[ident] = {**base, "reason": "on another connection"}
            continue
        if not d.get("hasDashboard"):
            skipped[ident] = {**base, "reason": "workbook with no dashboard"}
            continue
        body = cli.call("documents", "v2-get", ident)
        if not isinstance(body, dict):
            skipped[ident] = {**base, "reason": "document could not be read"}
            continue
        if body.get("modelId") and body["modelId"] != model_id:
            skipped[ident] = {**base, "reason": f"on another model ({body['modelId']})"}
            continue
        docs[ident] = body
        text = dump(body)
        inv_docs[ident] = {**base, "file": f"documents/{ident}.json", "sha256": sha(text)}
    keep_views = None if all_views else reachable_views(files, list(docs.values()))
    kept = {p: t for p, t in files.items()
            if not view_name_of(p) or keep_views is None or view_name_of(p) in keep_views}
    out.mkdir(parents=True, exist_ok=True)
    for p, txt in kept.items():
        fp = out / "model" / p
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(txt)
    for ident, body in docs.items():
        (out / "documents").mkdir(parents=True, exist_ok=True)
        (out / "documents" / f"{ident}.json").write_text(dump(body))
    reported = records(cli.call("models", "get-views", model_id), "views")
    names = {view_name_of(p) for p in kept if view_name_of(p)}
    views = sorted((v for v in reported if v.get("name") in names), key=lambda v: v["name"])
    (out / "views.json").write_text(dump({"views": [{"name": v["name"], "fields": v.get("fields", [])} for v in views]}))
    col_types, col_gaps = ({}, ["column types not read (--no-columns)"]) if not read_columns else \
        warehouse_columns(cli, model_id, (conn.get("dialect") or "").lower(), tables_of(kept, conn.get("database")))
    if columns:
        col_types.update(json.loads(Path(columns).read_text()))
    if col_types:
        (out / "columns.json").write_text(dump(col_types))
    host = re.sub(r"^https?://", "", base_url or "")
    inv = {
        "exporter": "omni_export", "version": VERSION,
        "exported_at": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "omni_cli_version": cli_version or cli.version(),
        "instance": re.sub(r"[^a-z0-9_-]+", "-", (host.split(".")[0] if host else "") or "omni"),
        "model": {"id": model_id, "name": model.get("name"), "connection_id": model.get("connectionId"),
                  "connection_name": conn.get("name"), "dialect": conn.get("dialect"), "database": conn.get("database"),
                  "default_schema": conn.get("defaultSchema")},
        "model_files": {p: {"sha256": sha(t)} for p, t in sorted(kept.items())},
        "model_files_total": len(files), "model_files_kept": len(kept),
        "documents": inv_docs, "skipped_documents": skipped,
        "column_tables": len(col_types), "column_gaps": col_gaps,
    }
    (out / "inventory.json").write_text(dump(inv))
    return inv


def diff(old: dict, new: dict) -> list:
    rows = []
    od, nd = old.get("documents") or {}, new.get("documents") or {}
    for ident in sorted(set(od) | set(nd)):
        o, n = od.get(ident), nd.get(ident)
        if o and not n:
            rows.append({"object": f"document:{ident}", "name": o.get("name"), "event": "removed"})
        elif n and not o:
            rows.append({"object": f"document:{ident}", "name": n.get("name"), "event": "new"})
        elif (n.get("updated_at") or "") > (o.get("updated_at") or "") or n.get("sha256") != o.get("sha256"):
            rows.append({"object": f"document:{ident}", "name": n.get("name"), "event": "content_drifted",
                         "old_updated_at": o.get("updated_at"), "new_updated_at": n.get("updated_at")})
    om, nm = old.get("model_files") or {}, new.get("model_files") or {}
    for p in sorted(set(om) | set(nm)):
        o, n = om.get(p), nm.get(p)
        if o and not n:
            rows.append({"object": f"model_file:{p}", "event": "removed"})
        elif n and not o:
            rows.append({"object": f"model_file:{p}", "event": "new"})
        elif o.get("sha256") != n.get("sha256"):
            rows.append({"object": f"model_file:{p}", "event": "model_drifted"})
    return rows


def tile_data(cli, document: str, key: str, out: Path, branch_id: str | None = None, keep_pivots=False,
              limit: int | None = None) -> dict:
    qs = records(cli.call("documents", "get-queries", document), "queries")
    q = next((x for x in qs if str(x.get("queryIdentifierMapKey")) == str(key)), None)
    if q is None:
        raise ExportError(f"document {document} has no query with key {key}")
    query = dict(q["query"])
    pivoted = bool(query.get("pivots")) and not keep_pivots
    if pivoted:
        # parity compares long rows: the pivot columns come back as rows
        query["pivots"] = []
    if limit:
        # a parity limit above the tile's own, so a top-N or capped tile can be compared in full on both sides
        query["limit"] = int(limit)
    body = {"query": query, "resultType": "csv", "formatResults": False}
    if branch_id:
        body["branchId"] = branch_id
    resp = cli.call("query", "run", "--body", json.dumps(body, sort_keys=True))
    text = resp if isinstance(resp, str) else ""
    if not text and isinstance(resp, list):
        rows = resp
        fields = q["query"].get("fields") or []
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(fields)
        for r in rows:
            w.writerow(list(r.values()))
        text = buf.getvalue()
    lines = list(csv.reader(io.StringIO(text)))
    fields = q["query"].get("fields") or []
    if lines and len(lines[0]) == len(fields):
        lines[0] = fields
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(lines)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(buf.getvalue())
    lim = query.get("limit")
    status = "truncated" if lim and len(lines) - 1 >= int(lim) else "complete"
    Path(str(out) + ".status").write_text(status + "\n")
    return {"rows": max(0, len(lines) - 1), "status": status, "fields": fields, "unpivoted": pivoted}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--model-id", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--profile")
    s.add_argument("--documents", default="")
    s.add_argument("--folders", default="")
    s.add_argument("--all-views", action="store_true", help="keep every view file, not only those reached")
    s.add_argument("--columns", help="extra column types: {\"schema.table\": {\"column\": \"TYPE\"}}, merged over those read")
    s.add_argument("--no-columns", action="store_true", help="do not read column types from INFORMATION_SCHEMA through Omni")
    d = sub.add_parser("diff")
    d.add_argument("--old", required=True)
    d.add_argument("--new", required=True)
    t = sub.add_parser("tile-data")
    t.add_argument("--document", required=True)
    t.add_argument("--query-key", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--profile")
    t.add_argument("--branch-id")
    t.add_argument("--keep-pivots", action="store_true", help="run the tile pivoted, as displayed (default: long rows)")
    t.add_argument("--limit", type=int, help="parity row limit in place of the tile's own; run the Looker side with the same")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "diff":
            rows = diff(json.loads(Path(a.old).read_text()), json.loads(Path(a.new).read_text()))
            print(json.dumps(rows, indent=1, sort_keys=True))
            return 0
        cli = Cli(a.profile)
        if a.cmd == "snapshot":
            sel = lambda s: {x.strip() for x in s.split(",") if x.strip()}  # noqa: E731
            inv = snapshot(cli, a.model_id, Path(a.out), sel(a.documents), sel(a.folders), a.all_views, a.columns,
                           base_url=cli.base_url(), read_columns=not a.no_columns)
            print(f"{inv['model_files_kept']} of {inv['model_files_total']} model files, {len(inv['documents'])} dashboards "
                  f"({len(inv['skipped_documents'])} documents skipped), column types for {inv['column_tables']} tables -> {a.out}")
            for g in inv["column_gaps"]:
                print(f"  note: {g}")
            return 0
        r = tile_data(cli, a.document, a.query_key, Path(a.out), a.branch_id, a.keep_pivots, a.limit)
        print(f"{r['rows']} rows ({r['status']}) -> {a.out}")
        return 0
    except ExportError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Metabase snapshot, drift and card data (bi_migration, pair metabase_to_looker). EXPERIMENTAL.

Metabase keeps its content in its application database, so this script takes the snapshot
the rest of the release reads. Three commands:

    api        Signs in with an API key (the x-api-key header), lists every card (question,
               model, metric) and dashboard, and saves each with the metadata of every table
               its queries read (fields, base and semantic types, primary and foreign keys),
               the SQL Metabase compiles for each query-builder card, the database
               connections (secret settings redacted), collections and usage counts.
               --dashboard limits the snapshot to those dashboards and the cards they need.
    diff       Two inventories in; drift per object: unchanged, content_drifted (updated_at
               newer, or SHA-256 changed when updated_at is absent), removed, new.
    card-data  Parity source side: one card's rows as CSV through POST /api/card/:id/query
               (raw values, not display formatting). With --dashboard and --dashcard the
               card runs as it does on that dashboard, with --param filter values. Writes
               <out>.status: ok, or truncated when Metabase capped the rows.

Snapshot layout (read by mb_to_lookml.py):
    <out>/inventory.json        tool, site, version, snapshot_source, exported_at, objects[],
                                databases[], collections[]
    <out>/usage.json            {"source": "metabase_view_count", "cards": {...}, "dashboards": {...}}
    <out>/cards/<id>.json       the card, usage counters removed
    <out>/dashboards/<id>.json  the dashboard with its dashcards
    <out>/tables/<id>.json      table query_metadata (fields, types, keys, fingerprints)
    <out>/compiled/<id>.sql     SQL Metabase compiles for a query-builder card

The API key is read from an environment variable; it is never written to the snapshot.
Deterministic for the same instance state: objects sorted, JSON keys sorted, usage counters
kept out of the object files, exported_at from --as-of when given (tests pin it).

Usage:
    python3 wire/scripts/metabase_export.py api --host-env MB_HOST --key-env MB_API_KEY --out <snapshot>
        [--dashboard ID ...] [--as-of TS]
    python3 wire/scripts/metabase_export.py diff --old inventory.json --new inventory.json
    python3 wire/scripts/metabase_export.py card-data --host-env MB_HOST --key-env MB_API_KEY --card ID
        [--dashboard ID --dashcard ID] [--param slug=value ...] --out rows.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

VERSION = "0.1.0"
# Counters and per-user flags that change without the content changing; kept out of object files
VOLATILE = {"view_count", "last_used_at", "last_viewed_at", "last_query_start", "can_write", "can_delete",
            "can_restore", "can_manage_db", "can_run_adhoc_query", "average_query_time", "query_average_duration",
            "last-edit-info", "creator", "dashboard_count", "parameter_usage_count", "is_remote_synced",
            "can_be_used_as_metric", "moderation_reviews"}
SECRET = re.compile(r"pass|secret|token|key|json|private|credential|cert", re.I)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def redact(details: dict) -> dict:
    out = {}
    for k, v in sorted((details or {}).items()):
        if SECRET.search(k) and k not in ("project-id", "dataset-filters-type"):
            out[k] = "[redacted]" if v not in (None, "", False) else v
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
    return out


def dumps(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode()


def site_of(host: str) -> str:
    h = urlparse(host).hostname or host
    return h.split(".")[0] if h.endswith("metabaseapp.com") else h


# ---------------------------------------------------------------------------
# MBQL walking: which tables, fields and cards a query needs
# ---------------------------------------------------------------------------

def stages(q: dict) -> list:
    """MBQL 5 ("stages") and legacy MBQL ("query" / "native") in one shape."""
    if "stages" in q:
        return q["stages"]
    if q.get("type") == "native":
        return [{"lib/type": "mbql.stage/native", "native": (q.get("native") or {}).get("query", "")}]
    inner, out = q.get("query") or {}, []
    while inner:
        st = {k: v for k, v in inner.items() if k != "source-query"}
        out.insert(0, st)
        inner = inner.get("source-query")
    return out


def refs(x, kind):
    """Every [kind, opts, id] clause under x."""
    found = []
    if isinstance(x, list):
        if len(x) >= 3 and x[0] == kind and isinstance(x[1], dict):
            found.append(x)
        for y in x:
            found += refs(y, kind)
    elif isinstance(x, dict):
        for v in x.values():
            found += refs(v, kind)
    return found


def needs(card: dict):
    """(table ids, field ids, card ids) a card's query reads."""
    tables, fields, cards = set(), set(), set()
    for st in stages(card.get("dataset_query") or {}):
        for s in [st] + [js for j in st.get("joins", []) for js in j.get("stages", [])]:
            if isinstance(s.get("source-table"), int):
                tables.add(s["source-table"])
            if isinstance(s.get("source-table"), str) and s["source-table"].startswith("card__"):
                cards.add(int(s["source-table"][6:]))
            if s.get("source-card"):
                cards.add(s["source-card"])
        for f in refs(st, "field"):
            if isinstance(f[2], int):
                fields.add(f[2])
            if isinstance(f[1].get("source-field"), int):
                fields.add(f[1]["source-field"])
        for m in refs(st, "metric"):
            if isinstance(m[2], int):
                cards.add(m[2])
        for tag in ((st.get("template-tags") or {}).values() if isinstance(st.get("template-tags"), dict) else []):
            if tag.get("type") == "card" and tag.get("card-id"):
                cards.add(tag["card-id"])
            if tag.get("type") == "dimension" and tag.get("dimension"):
                for f in refs([tag["dimension"]], "field"):
                    if isinstance(f[2], int):
                        fields.add(f[2])
    return tables, fields, cards


# ---------------------------------------------------------------------------
# API client behind a small interface, so the snapshot logic is testable with a fake
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, host: str, key: str):
        try:
            import requests  # type: ignore  (brings its own CA bundle; some Python installs have none)
        except ImportError:
            raise SystemExit("requests is not installed: python3 -m pip install requests")
        self.requests, self.host, self.key = requests, host.rstrip("/"), key

    def _call(self, method, path, body=None):
        r = self.requests.request(method, self.host + path, headers={"x-api-key": self.key}, json=body, timeout=120)
        if r.status_code >= 400:
            raise SystemExit(f"Metabase {method} {path}: HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def version(self):
        return (self._call("GET", "/api/session/properties").get("version") or {}).get("tag")

    def databases(self):
        d = self._call("GET", "/api/database")
        return d.get("data", d) if isinstance(d, dict) else d

    def collections(self):
        return self._call("GET", "/api/collection")

    def cards(self):
        return self._call("GET", "/api/card?f=all")

    def dashboards(self):
        return self._call("GET", "/api/dashboard")

    def dashboard(self, did):
        return self._call("GET", f"/api/dashboard/{did}")

    def table(self, tid):
        return self._call("GET", f"/api/table/{tid}/query_metadata?include_hidden_fields=true")

    def field(self, fid):
        return self._call("GET", f"/api/field/{fid}")

    def compile(self, dataset_query):
        return (self._call("POST", "/api/dataset/native", dict(dataset_query, pretty=True)) or {}).get("query")

    def card_rows(self, card_id, dashboard=None, dashcard=None, parameters=None):
        if dashboard:
            path = f"/api/dashboard/{dashboard}/dashcard/{dashcard}/card/{card_id}/query"
        else:
            path = f"/api/card/{card_id}/query"
        res = self._call("POST", path, {"parameters": parameters or []})
        data = res.get("data") or {}
        return data.get("cols", []), data.get("rows", []), bool(data.get("rows_truncated")) or res.get("row_count") == 2000


def export_api(client, out: Path, site: str, as_of: str | None, only_dashboards=None):
    all_cards = {c["id"]: c for c in client.cards()}
    dash_list = client.dashboards()
    if only_dashboards:
        dash_list = [d for d in dash_list if d["id"] in only_dashboards]
    dashboards = {d["id"]: client.dashboard(d["id"]) for d in dash_list}
    # cards in scope: all, or those the chosen dashboards show and everything they build on
    if only_dashboards:
        todo = [dc["card_id"] for d in dashboards.values() for dc in d.get("dashcards", []) if dc.get("card_id")]
        # a combined chart's extra series are card objects (id), not references (card_id)
        todo += [s.get("id") or s.get("card_id") for d in dashboards.values() for dc in d.get("dashcards", [])
                 for s in dc.get("series") or []]
    else:
        todo = list(all_cards)
    scope = set()
    while todo:
        cid = todo.pop()
        if cid in scope or cid not in all_cards:
            continue
        scope.add(cid)
        todo += list(needs(all_cards[cid])[2])
    cards = {cid: all_cards[cid] for cid in scope}
    # tables: every table a query reads, plus the tables behind its fields (implicit joins, FK targets)
    tables, fields_seen = {}, {}
    want_t, want_f = set(), set()
    for c in cards.values():
        t, f, _ = needs(c)
        want_t |= t
        want_f |= f
    while want_t or want_f:
        for tid in sorted(want_t):
            if tid not in tables:
                tables[tid] = client.table(tid)
                for fld in tables[tid].get("fields", []):
                    fields_seen[fld["id"]] = fld
                    if fld.get("fk_target_field_id"):
                        want_f.add(fld["fk_target_field_id"])
        want_t = set()
        for fid in sorted(want_f):
            if fid not in fields_seen:
                fld = client.field(fid)
                fields_seen[fid] = fld
                if fld.get("table_id") and fld["table_id"] not in tables:
                    want_t.add(fld["table_id"])
        want_f = set()
    payloads, objects = {}, []
    collections = {c["id"]: c for c in client.collections() if isinstance(c.get("id"), int)}
    usage = {"source": "metabase_view_count", "cards": {}, "dashboards": {}}
    for cid, c in sorted(cards.items()):
        body = dumps(strip(c))
        rel = f"cards/{cid}.json"
        payloads[rel] = body
        q = c.get("dataset_query") or {}
        native = any("native" in st for st in stages(q))
        if not native and not c.get("archived"):
            try:
                sql = client.compile(q)
                if sql:
                    payloads[f"compiled/{cid}.sql"] = (sql.rstrip() + "\n").encode()
            except SystemExit as e:
                payloads[f"compiled/{cid}.error"] = (str(e) + "\n").encode()
        coll = collections.get(c.get("collection_id"))
        objects.append({"kind": "card", "id": str(cid), "name": c.get("name"), "card_type": c.get("type") or "question",
                        "display": c.get("display"), "query_kind": "native" if native else "mbql",
                        "database_id": c.get("database_id"), "collection_id": c.get("collection_id"),
                        "collection": coll.get("name") if coll else None, "archived": bool(c.get("archived")),
                        "updated_at": c.get("updated_at"), "sha256": sha256(body), "path": rel})
        usage["cards"][str(cid)] = {"view_count": c.get("view_count"), "last_used_at": c.get("last_used_at")}
    for did, d in sorted(dashboards.items()):
        body = dumps(strip(d))
        rel = f"dashboards/{did}.json"
        payloads[rel] = body
        coll = collections.get(d.get("collection_id"))
        objects.append({"kind": "dashboard", "id": str(did), "name": d.get("name"), "collection_id": d.get("collection_id"),
                        "collection": coll.get("name") if coll else None, "archived": bool(d.get("archived")),
                        "updated_at": d.get("updated_at"), "sha256": sha256(body), "path": rel})
        usage["dashboards"][str(did)] = {"view_count": d.get("view_count"), "last_viewed_at": d.get("last_viewed_at")}
    for tid, t in sorted(tables.items()):
        payloads[f"tables/{tid}.json"] = dumps(strip(t))
    dbs_used = {c.get("database_id") for c in cards.values()} | {t.get("db_id") for t in tables.values()}
    databases = [{"id": d["id"], "name": d.get("name"), "engine": d.get("engine"), "details": redact(d.get("details"))}
                 for d in client.databases() if d["id"] in dbs_used]
    inv = {"tool": "metabase", "site": site, "version": client.version(), "snapshot_source": "api",
           "exporter": f"metabase_export.py {VERSION}",
           "exported_at": as_of or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "objects": sorted(objects, key=lambda o: (o["kind"], int(o["id"]))),
           "databases": sorted(databases, key=lambda d: d["id"]),
           "collections": sorted([{"id": c["id"], "name": c.get("name"), "location": c.get("location")}
                                  for c in collections.values()], key=lambda c: c["id"])}
    if out.exists():
        shutil.rmtree(out)
    for rel, data in payloads.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (out / "inventory.json").write_bytes(dumps(inv))
    (out / "usage.json").write_bytes(dumps(usage))
    return inv


# ---------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------

def diff(old: dict, new: dict):
    o = {(x["kind"], x["id"]): x for x in old.get("objects", [])}
    n = {(x["kind"], x["id"]): x for x in new.get("objects", [])}
    rows = []
    for key in sorted(set(o) | set(n)):
        a, b = o.get(key), n.get(key)
        if a is None:
            state, why = "new", "not in the pinned snapshot"
        elif b is None:
            state, why = "removed", "no longer on the instance"
        elif b.get("archived") and not a.get("archived"):
            state, why = "removed", "archived since the pinned snapshot"
        elif a.get("updated_at") and b.get("updated_at") and b["updated_at"] > a["updated_at"]:
            state, why = "content_drifted", f"updated_at {a['updated_at']} -> {b['updated_at']}"
        elif a.get("sha256") != b.get("sha256"):
            state, why = "content_drifted", "content SHA-256 changed"
        else:
            state, why = "unchanged", ""
        rows.append({"kind": key[0], "id": key[1], "state": state, "reason": why})
    return rows


def write_rows(out: Path, cols, rows, truncated):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow([c.get("name") for c in cols])
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    Path(str(out) + ".status").write_text("truncated\n" if truncated else "ok\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("api", "card-data"):
        s = sub.add_parser(name)
        s.add_argument("--host-env", default="MB_HOST")
        s.add_argument("--key-env", default="MB_API_KEY")
        s.add_argument("--out", required=True)
        if name == "api":
            s.add_argument("--dashboard", type=int, action="append", default=[])
            s.add_argument("--as-of")
        else:
            s.add_argument("--card", type=int, required=True)
            s.add_argument("--dashboard", type=int)
            s.add_argument("--dashcard", type=int)
            s.add_argument("--param", action="append", default=[], help="parameter id=value (dashboard filters)")
    d = sub.add_parser("diff")
    d.add_argument("--old", required=True)
    d.add_argument("--new", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "diff":
        print(json.dumps(diff(json.loads(Path(a.old).read_text()), json.loads(Path(a.new).read_text())), indent=1, sort_keys=True))
        return 0
    host, key = os.environ.get(a.host_env), os.environ.get(a.key_env)
    if not host or not key:
        print(f"ERROR: set {a.host_env} (instance URL) and {a.key_env} (API key)", file=sys.stderr)
        return 2
    client = APIClient(host, key)
    if a.cmd == "api":
        inv = export_api(client, Path(a.out), site_of(host), a.as_of, set(a.dashboard) or None)
        n = {k: sum(1 for o in inv["objects"] if o["kind"] == k) for k in ("card", "dashboard")}
        print(f"{n['card']} cards, {n['dashboard']} dashboards, {len(list(Path(a.out, 'tables').glob('*.json')))} tables "
              f"(Metabase {inv['version']}) -> {a.out}")
        return 0
    if bool(a.dashboard) != bool(a.dashcard):
        print("ERROR: --dashboard and --dashcard go together", file=sys.stderr)
        return 2
    params = []
    for p in a.param:
        pid, val = p.split("=", 1)
        params.append({"id": pid, "value": [val]})
    cols, rows, truncated = client.card_rows(a.card, a.dashboard, a.dashcard, params)
    write_rows(Path(a.out), cols, rows, truncated)
    print(f"card {a.card}: {len(rows)} rows{' (truncated)' if truncated else ''} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

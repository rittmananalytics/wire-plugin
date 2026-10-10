#!/usr/bin/env python3
"""
Tableau snapshot, drift and view data (wire#287, bi_migration, pair tableau_to_looker). EXPERIMENTAL.

Tableau has no git repository to register, so this script takes the snapshot the rest of
the release reads. Four commands:

    files      Desktop mode. A directory of .twb, .twbx, .tds, .tdsx in; a snapshot out.
               No network call. Pins each file by SHA-256; usage is unavailable.
    rest       Tableau Cloud or Server. Signs in with a personal access token, lists and
               downloads every workbook and published data source (without extracts),
               and records project, owner, updatedAt, extract refresh time and
               subscriptions in inventory.json. Needs tableauserverclient.
    diff       Two inventories in; drift per object: unchanged, content_drifted (updatedAt
               newer, or SHA-256 changed when updatedAt is absent), removed, new, and
               extract_refreshed_after_parity when a data source's extract refreshed after
               the pinned parity_as_of.
    view-data  Parity source side: one view's rows as CSV through REST Query View Data,
               with filters, plus the extract refresh time of the data behind it.

Snapshot layout (read by twb_to_lookml.py):
    <out>/inventory.json      tool, site, edition, snapshot_source, api_version, exported_at, objects[]
    <out>/usage.json          {"source": "admin_insights|repository|unavailable", "workbooks": {id: {...}}}
    <out>/workbooks/<id>.twb  (unzipped from .twbx)
    <out>/datasources/<id>.tds

Deterministic for the same input: objects are sorted, JSON keys sorted, and exported_at is
taken from --as-of when given (tests pin it).

Usage:
    python3 wire/scripts/tableau_export.py files --dir <files> --out <snapshot> --site <site> [--as-of TS]
    python3 wire/scripts/tableau_export.py rest --server URL --site SITE --token-name-env VAR
        --token-env VAR --out <snapshot> [--usage-csv admin_insights.csv]
    python3 wire/scripts/tableau_export.py diff --old inventory.json --new inventory.json [--parity-as-of TS]
    python3 wire/scripts/tableau_export.py view-data --server URL --site SITE --token-name-env VAR
        --token-env VAR --view-luid LUID [--filter field=value ...] --out rows.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

VERSION = "0.1.0"
SUFFIX = {".twb": ("workbook", "workbooks", ".twb"), ".twbx": ("workbook", "workbooks", ".twb"),
          ".tds": ("datasource", "datasources", ".tds"), ".tdsx": ("datasource", "datasources", ".tds")}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def unpack(path: Path) -> bytes:
    if path.suffix in (".twbx", ".tdsx"):
        with zipfile.ZipFile(path) as z:
            inner = sorted(n for n in z.namelist() if n.endswith((".twb", ".tds")) and "/" not in n)
            if not inner:
                raise SystemExit(f"{path}: no .twb or .tds at the top of the package")
            return z.read(inner[0])
    return path.read_bytes()


def write_snapshot(out: Path, inventory: dict, usage: dict, payloads: dict):
    if out.exists():
        shutil.rmtree(out)
    for rel, data in payloads.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    inventory["objects"] = sorted(inventory["objects"], key=lambda o: (o["kind"], o["id"]))
    (out / "inventory.json").write_text(json.dumps(inventory, indent=1, sort_keys=True) + "\n")
    (out / "usage.json").write_text(json.dumps(usage, indent=1, sort_keys=True) + "\n")


def export_files(src: Path, out: Path, site: str, as_of: str | None):
    objects, payloads = [], {}
    for p in sorted(src.rglob("*")):
        if p.suffix not in SUFFIX or not p.is_file():
            continue
        kind, sub, ext = SUFFIX[p.suffix]
        data = unpack(p)
        rel = f"{sub}/{p.stem}{ext}"
        if rel in payloads:
            raise SystemExit(f"two files map to {rel}; rename one")
        payloads[rel] = data
        objects.append({"id": p.stem, "kind": kind, "name": p.stem, "path": rel, "project": None, "owner": None,
                        "updated_at": None, "sha256": sha256(data), "source_file": str(p.relative_to(src)),
                        "extract_refreshed_at": None, "subscriptions": []})
    inv = {"tool": "tableau", "site": site, "edition": "desktop_files", "snapshot_source": "files",
           "api_version": None, "exporter": f"tableau_export.py {VERSION}",
           "exported_at": as_of or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "objects": objects}
    write_snapshot(out, inv, {"source": "unavailable", "workbooks": {}}, payloads)
    return inv


# ---------------------------------------------------------------------------
# REST (Tableau Cloud and Server) behind a small client interface, so the snapshot
# logic is testable with a fake client and no site.
# ---------------------------------------------------------------------------

class TSCClient:
    """Thin wrapper over tableauserverclient. Methods return plain dicts."""

    def __init__(self, server_url, site, token_name, token):
        try:
            import tableauserverclient as TSC  # type: ignore
        except ImportError:
            raise SystemExit("tableauserverclient is not installed: python3 -m pip install tableauserverclient")
        self.TSC = TSC
        self.server = TSC.Server(server_url, use_server_version=True)
        self.server.auth.sign_in(TSC.PersonalAccessTokenAuth(token_name, token, site_id=site))

    @property
    def api_version(self):
        return self.server.version

    @property
    def edition(self):
        return "cloud" if "online.tableau.com" in self.server.server_address else "server"

    def workbooks(self):
        out = []
        for w in self.TSC.Pager(self.server.workbooks):
            out.append({"id": w.id, "name": w.name, "project": w.project_name, "owner": w.owner_id,
                        "content_url": w.content_url,
                        "updated_at": w.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if w.updated_at else None})
        return out

    def datasources(self):
        out = []
        for d in self.TSC.Pager(self.server.datasources):
            out.append({"id": d.id, "name": d.name, "project": d.project_name, "owner": d.owner_id,
                        "content_url": d.content_url,
                        "updated_at": d.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if d.updated_at else None,
                        "has_extract": bool(getattr(d, "has_extracts", False))})
        return out

    def download(self, kind, luid, tmp: Path) -> Path:
        ep = self.server.workbooks if kind == "workbook" else self.server.datasources
        return Path(ep.download(luid, filepath=str(tmp), include_extract=False))

    def extract_refreshes(self):
        """LUID -> completion time of the last successful extract refresh in the site's job history.
        (A refresh task's schedule gives the next run, which is not evidence of what the data was.)"""
        out = {}
        try:
            opts = self.TSC.RequestOptions(pagesize=1000)
            jobs, _ = self.server.jobs.get(req_options=opts)
        except Exception:
            return out
        for j in jobs:
            if "refreshextract" not in str(getattr(j, "type", "")).lower().replace("_", ""):
                continue
            if str(getattr(j, "status", "")) != "Success":
                continue
            try:
                full = self.server.jobs.get_by_id(j.id)
            except Exception:
                continue
            target = full.datasource_id or full.workbook_id
            done = full.completed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if full.completed_at else None
            if target and done and done > (out.get(target) or ""):
                out[target] = done
        return out

    def views(self):
        """Every view on the site with its workbook, for parity (view-data takes a view LUID) and usage."""
        out, page = [], 1
        while True:
            items, pag = self.server.views.get(self.TSC.RequestOptions(pagenumber=page, pagesize=1000), usage=True)
            for v in items:
                out.append({"id": v.id, "name": v.name, "workbook": v.workbook_id, "content_url": v.content_url,
                            "total_views": v.total_views})
            if page * pag.page_size >= pag.total_available:
                return out
            page += 1

    def subscriptions(self):
        out = {}
        try:
            for s in self.TSC.Pager(self.server.subscriptions):
                out.setdefault(s.target.id, []).append({"id": s.id, "subject": s.subject, "user": s.user_id})
        except Exception:
            pass
        return out

    def view_csv(self, view_luid, filters):
        opts = self.TSC.CSVRequestOptions()
        for k, v in filters:
            opts.vf(k, v)
        view = self.server.views.get_by_id(view_luid)
        self.server.views.populate_csv(view, opts)
        return b"".join(view.csv)

    def sign_out(self):
        self.server.auth.sign_out()


def export_rest(client, out: Path, site: str, usage_csv: Path | None, as_of: str | None, tmp: Path):
    objects, payloads = [], {}
    refreshes = client.extract_refreshes()
    subs = client.subscriptions()
    tmp.mkdir(parents=True, exist_ok=True)
    views = sorted(client.views(), key=lambda v: (v["workbook"] or "", v["id"])) if hasattr(client, "views") else []
    views_by_wb = {}
    for v in views:
        views_by_wb.setdefault(v["workbook"], []).append(
            {"id": v["id"], "name": v["name"], "content_url": v.get("content_url")})
    for kind, items in (("workbook", client.workbooks()), ("datasource", client.datasources())):
        sub, ext = ("workbooks", ".twb") if kind == "workbook" else ("datasources", ".tds")
        for it in items:
            path = client.download(kind, it["id"], tmp)
            data = unpack(path)
            rel = f"{sub}/{it['id']}{ext}"
            payloads[rel] = data
            objects.append({"id": it["id"], "kind": kind, "name": it["name"], "path": rel,
                            "content_url": it.get("content_url"),
                            "project": it.get("project"), "owner": it.get("owner"), "updated_at": it.get("updated_at"),
                            "sha256": sha256(data), "extract_refreshed_at": refreshes.get(it["id"]),
                            "subscriptions": sorted(subs.get(it["id"], []), key=lambda s: s["id"])})
            if kind == "workbook":
                objects[-1]["views"] = views_by_wb.get(it["id"], [])
    usage = {"source": "unavailable", "workbooks": {}}
    if views and any(v.get("total_views") is not None for v in views):
        # all-time view counts from the REST API: weaker than Admin Insights (no window, no last viewed)
        usage["source"] = "rest_total_views"
        for v in views:
            u = usage["workbooks"].setdefault(v["workbook"], {"views_total": 0, "views": {}})
            u["views_total"] += int(v.get("total_views") or 0)
            u["views"][v["id"]] = int(v.get("total_views") or 0)
    if usage_csv:
        usage["workbooks"] = {}
        usage["source"] = "admin_insights"
        for row in csv.DictReader(usage_csv.open()):
            wid = row.get("Workbook LUID") or row.get("workbook_luid") or row.get("Item LUID")
            if wid:
                u = usage["workbooks"].setdefault(wid, {"views_90d": 0, "last_viewed": None})
                u["views_90d"] += int(row.get("Views") or row.get("views") or 0)
                last = row.get("Last Accessed At") or row.get("last_viewed")
                if last and (u["last_viewed"] is None or last > u["last_viewed"]):
                    u["last_viewed"] = last
    inv = {"tool": "tableau", "site": site, "edition": client.edition, "snapshot_source": "rest",
           "api_version": client.api_version, "exporter": f"tableau_export.py {VERSION}",
           "exported_at": as_of or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "objects": objects}
    write_snapshot(out, inv, usage, payloads)
    return inv


# ---------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------

def diff(old: dict, new: dict, parity_as_of: str | None = None):
    o = {(x["kind"], x["id"]): x for x in old.get("objects", [])}
    n = {(x["kind"], x["id"]): x for x in new.get("objects", [])}
    rows = []
    for key in sorted(set(o) | set(n)):
        a, b = o.get(key), n.get(key)
        if a is None:
            state, why = "new", "not in the pinned snapshot"
        elif b is None:
            state, why = "removed", "no longer on the site"
        elif a.get("updated_at") and b.get("updated_at"):
            if b["updated_at"] > a["updated_at"]:
                state, why = "content_drifted", f"updatedAt {a['updated_at']} -> {b['updated_at']}"
            else:
                state, why = "unchanged", ""
        elif a.get("sha256") != b.get("sha256"):
            state, why = "content_drifted", "file SHA-256 changed (no updatedAt to compare)"
        else:
            state, why = "unchanged", ""
        row = {"kind": key[0], "id": key[1], "state": state, "reason": why}
        ref = (b or {}).get("extract_refreshed_at")
        if parity_as_of and ref and ref > parity_as_of:
            row["extract_refreshed_after_parity"] = True
            row["reason"] = (row["reason"] + "; " if row["reason"] else "") + \
                f"extract refreshed {ref}, after parity_as_of {parity_as_of}: tiles on it are INCONCLUSIVE until re-run"
        rows.append(row)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("files")
    f.add_argument("--dir", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--site", default="local")
    f.add_argument("--as-of")
    for name in ("rest", "view-data"):
        r = sub.add_parser(name)
        r.add_argument("--server", required=True)
        r.add_argument("--site", required=True)
        r.add_argument("--token-name-env", required=True)
        r.add_argument("--token-env", required=True)
        r.add_argument("--out", required=True)
        if name == "rest":
            r.add_argument("--usage-csv")
            r.add_argument("--as-of")
        else:
            r.add_argument("--view-luid", required=True)
            r.add_argument("--filter", action="append", default=[])
    d = sub.add_parser("diff")
    d.add_argument("--old", required=True)
    d.add_argument("--new", required=True)
    d.add_argument("--parity-as-of")
    a = ap.parse_args(argv)

    if a.cmd == "files":
        inv = export_files(Path(a.dir), Path(a.out), a.site, a.as_of)
        print(f"{len(inv['objects'])} objects (files mode, usage unavailable) -> {a.out}")
        return 0
    if a.cmd == "diff":
        rows = diff(json.loads(Path(a.old).read_text()), json.loads(Path(a.new).read_text()), a.parity_as_of)
        print(json.dumps(rows, indent=1, sort_keys=True))
        return 0
    name, token = os.environ.get(a.token_name_env), os.environ.get(a.token_env)
    if not name or not token:
        print(f"ERROR: set {a.token_name_env} and {a.token_env} (personal access token name and secret)", file=sys.stderr)
        return 2
    client = TSCClient(a.server, a.site, name, token)
    try:
        if a.cmd == "rest":
            inv = export_rest(client, Path(a.out), a.site, Path(a.usage_csv) if a.usage_csv else None, a.as_of,
                              Path(a.out).with_suffix(".download"))
            shutil.rmtree(Path(a.out).with_suffix(".download"), ignore_errors=True)
            print(f"{len(inv['objects'])} objects ({inv['edition']}, API {inv['api_version']}) -> {a.out}")
        else:
            filters = [tuple(x.split("=", 1)) for x in a.filter]
            Path(a.out).write_bytes(client.view_csv(a.view_luid, filters))
            print(f"view {a.view_luid} -> {a.out}")
    finally:
        client.sign_out()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Looker Studio capture: Routes B and C (wire#278, bi_migration, pair looker_studio_to_omni).

Opens each report in a headed Chrome window signed in with the consultant's own Google
account, visits every page and every data source editor, and records the responses of
Looker Studio's internal calls:

    Route B  getReport, getSchema, getBlockDatasource   the report and data source definitions
    Route C  batchedDataV2                               each chart's query and the values it showed

It navigates only. It never clicks, types or saves, so it cannot change a report.
These endpoints are undocumented: Google can change them without notice. The Looker
Studio app version is recorded with every capture so a break can be traced.

Usage:
    python3 wire/scripts/looker_studio_capture.py --out <dir> <report_url> [<report_url> ...]
        [--no-data] [--screenshots] [--page-wait 6] [--profile ~/.wire/looker_studio/profile]
        [--allow-tracked]

Requires Playwright and Google Chrome:
    python3 -m pip install playwright

Sign-in: the first run opens Chrome on a separate profile under ~/.wire/looker_studio/
and waits up to 5 minutes for you to sign in. Later runs reuse the profile.

Output per report (read by looker_studio_extract.py and looker_studio_parity.py):
    <out>/<report_id>/meta.json, report/, datasources/<id>/, data/, screenshots/

The capture holds client data (Route C values) and can hold credentials stored in
connector settings. The output folder must be git-ignored; the script refuses to write
into a tracked folder unless --allow-tracked is given.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HOST = "https://datastudio.google.com"   # lookerstudio.google.com redirects here as application/binary
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
DEFINITIONS = re.compile(r"/(getReport|getSchema|getBlockDatasource)(\?|$)")
DATA = re.compile(r"/batchedDataV2(\?|$)")
DS_FIELD = re.compile(r'"datasourceId":\s*"([0-9a-f-]{36})"')
APP_VERSION = re.compile(r"appVersion=([^&]+)")


def report_id(url: str) -> str:
    m = UUID.search(url.split("/reporting/", 1)[-1])
    if not m:
        raise SystemExit(f"Not a Looker Studio report URL: {url}")
    return m.group(0)


def load(path: Path):
    body = path.read_text().split("\n", 1)[1].lstrip()
    return json.loads(body[4:] if body.startswith(")]}'") else body)


def definition(rep: dict):
    if rep["reportConfig"].get("page"):
        return rep["reportConfig"], "draft"
    return rep["publishedReportRevision"]["reportConfig"], "published"


def tracked(path: Path) -> bool:
    """True when path is inside a git work tree and not ignored."""
    path.mkdir(parents=True, exist_ok=True)
    inside = subprocess.run(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return False
    probe = path / "probe.json"
    ignored = subprocess.run(["git", "-C", str(path), "check-ignore", "-q", str(probe)])
    return ignored.returncode != 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--no-data", action="store_true", help="do not record chart data (Route C)")
    ap.add_argument("--screenshots", action="store_true", help="save a screenshot of every page")
    ap.add_argument("--page-wait", type=float, default=6.0, help="seconds to wait on each page")
    ap.add_argument("--profile", default=str(Path.home() / ".wire" / "looker_studio" / "profile"))
    ap.add_argument("--allow-tracked", action="store_true")
    a = ap.parse_args(argv)

    out = Path(a.out).expanduser()
    if tracked(out) and not a.allow_tracked:
        print(f"ERROR: {out} is inside a git repository and not ignored. Captures hold client data "
              "and may hold connector credentials. Add it to .gitignore, or pass --allow-tracked.",
              file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed. Run: python3 -m pip install playwright", file=sys.stderr)
        return 2

    profile = Path(a.profile).expanduser()
    profile.mkdir(parents=True, exist_ok=True)
    wait_ms = int(a.page_wait * 1000)
    failures = 0

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), channel="chrome", headless=False,
                                                   viewport={"width": 1600, "height": 1000})
        state = {"page": ctx.new_page(), "def_dir": None, "data_dir": None, "n": 0, "seen": set()}

        def on_response(resp):
            url = resp.url
            if state["def_dir"] is not None and DEFINITIONS.search(url):
                target = state["def_dir"]
            elif state["data_dir"] is not None and DATA.search(url):
                target = state["data_dir"]
            else:
                return
            post = resp.request.post_data or ""
            key = (url.split("?")[0], post)
            if key in state["seen"]:
                return
            try:
                body = resp.text()
            except Exception:
                return
            state["seen"].add(key)
            state["n"] += 1
            name = url.split("?")[0].rsplit("/", 1)[-1]
            (target / f"{state['n']:04d}_{name}.txt").write_text(
                json.dumps({"url": url, "status": resp.status, "post": post}) + "\n" + body)

        def attach(page):
            page.on("response", on_response)
            return page

        attach(state["page"])
        for extra in list(ctx.pages):
            if extra is not state["page"]:
                extra.close()

        def go(url) -> bool:
            for attempt in (1, 2):
                try:
                    state["page"].goto(url, wait_until="domcontentloaded")
                    return True
                except Exception as e:  # "Download is starting" and navigation timeouts
                    print(f"  {url}: {str(e).splitlines()[0]} (attempt {attempt})", flush=True)
                    state["page"].close()
                    state["page"] = attach(ctx.new_page())
            return False

        go(HOST + "/navigation/reporting")
        if "accounts.google.com" in state["page"].url:
            print("Sign in to Google in the Chrome window. Waiting up to 5 minutes...", flush=True)
            state["page"].wait_for_url(re.compile(r"(lookerstudio|datastudio)\.google\.com/"), timeout=300_000)
            state["page"].wait_for_timeout(3000)

        for url in a.urls:
            rid = report_id(url)
            rdir = out / rid
            for sub in ("report", "data", "screenshots"):
                (rdir / sub).mkdir(parents=True, exist_ok=True)
            state.update(def_dir=rdir / "report", data_dir=None if a.no_data else rdir / "data", n=0, seen=set())
            go(f"{HOST}/reporting/{rid}")
            deadline = time.time() + 60
            while not list((rdir / "report").glob("*getReport*")) and time.time() < deadline:
                state["page"].wait_for_timeout(1000)
            reps = sorted((rdir / "report").glob("*getReport*"))
            if not reps:
                print(f"FAILED {rid}: no getReport received. Check access to the report and sign-in.", flush=True)
                failures += 1
                continue
            rep = load(reps[0])
            if rep.get("reportConfig") is None:
                print(f"FAILED {rid}: getReport returned no definition (no access?)", flush=True)
                failures += 1
                continue
            cfg, revision = definition(rep)
            nav = json.dumps(rep["reportConfig"].get("navigationInfo", {}))
            page_ids = list(dict.fromkeys(re.findall(r'"pageId":\s*"([^"]+)"', nav)))
            state["page"].wait_for_timeout(wait_ms)
            failed_pages = []
            for i, pid in enumerate(page_ids):
                if i > 0 and not go(f"{HOST}/reporting/{rid}/page/{pid}"):
                    failed_pages.append(pid)
                    continue
                if i > 0:
                    state["page"].wait_for_timeout(wait_ms)
                if a.screenshots:
                    try:
                        state["page"].screenshot(path=str(rdir / "screenshots" / f"{i + 1:03d}_{pid}.png"),
                                                 full_page=True)
                    except Exception:
                        pass
            state["data_dir"] = None
            ds_ids = sorted(set(DS_FIELD.findall(json.dumps(cfg))))
            for dsid in ds_ids:
                d = rdir / "datasources" / dsid
                d.mkdir(parents=True, exist_ok=True)
                state.update(def_dir=d, n=0, seen=set())
                go(f"{HOST}/datasources/{dsid}")
                state["page"].wait_for_timeout(wait_ms)
                if not any(d.iterdir()):
                    d.rmdir()
            state["def_dir"] = None
            head = json.loads(reps[0].read_text().split("\n", 1)[0])
            m = APP_VERSION.search(head.get("url", ""))
            (rdir / "meta.json").write_text(json.dumps({
                "url": url,
                "captured_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "capture_script": "looker_studio_capture.py 1.0.0",
                "revision": revision,
                "pages": page_ids,
                "failed_pages": failed_pages,
                "datasources": ds_ids,
                "app_version": m.group(1) if m else None,
                "chart_data_recorded": not a.no_data,
            }, indent=1, sort_keys=True) + "\n")
            print(f"captured {rid}: {revision}, {len(page_ids)} pages ({len(failed_pages)} failed), "
                  f"{len(ds_ids)} data sources", flush=True)
        ctx.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

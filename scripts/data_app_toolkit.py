#!/usr/bin/env python3
"""Wire's wrapper around Google's Looker Data Apps toolkit (wire#387).

The toolkit (installed by https://dl.google.com/looker-data-apps/install.sh,
default ~/looker-data-apps) authors, previews, verifies and publishes a Data
App from its own apps/<slug>/app.js. Wire keeps the app's source in the
client repo and this script moves copies between the two, runs the toolkit's
own tools from the toolkit root, and wraps the publish in a plan, a
confirmation and a record. It never reads the toolkit's credentials
(data-apps-config.json) beyond listing which keys are present, never prints
a secret, and never publishes without --confirm.

    check              toolkit present, VERSION against the pin, config present, tools present
    push               copy the repo app into <toolkit>/apps/<slug>/ (refuses to overwrite edits)
    pull               copy the toolkit copy back (--tags-only: the publish tags in the header)
    diff               compare the two copies, ignoring the publish tags
    verify             run the toolkit's verify-app.py (stages 1 to 3) and summarise
    publish plan|run   wrap publish-data-app.py; run needs --confirm

Toolkit path: --toolkit, else $WIRE_DATA_APPS_TOOLKIT, else toolkit_path: in
.wire/local/data_apps.yml (git-ignored, per person), else ~/looker-data-apps.
Pin: --pin, else wire/data_apps/pinned_toolkit_version.txt beside this script's folder.

Stdlib only.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PUBLISH_TAGS = ("@looker-dashboard-id", "@looker-instance", "@created-at", "@created-by",
                "@updated-at", "@updated-by", "@toolkit-version", "@published-at", "@published-by")
VERIFY_TOOL = Path("skills") / "data-app-creator" / "tools" / "verify-app.py"
CHECK_CREDS_TOOL = Path("skills") / "data-app-creator" / "tools" / "check-credentials.py"
PUBLISH_TOOL = Path("skills") / "data-app-publisher" / "tools" / "publish-data-app.py"
PREVIEW_TOOL = Path("skills") / "data-app-previewer" / "tools" / "start-preview.py"
REQUIRED_TOOLS = (VERIFY_TOOL, CHECK_CREDS_TOOL, PUBLISH_TOOL, PREVIEW_TOOL)
SECRET_KEYS = ("client_secret", "client_id")


# ----------------------------------------------------------------------
# resolution
# ----------------------------------------------------------------------

def local_toolkit_path(repo_root: Path) -> str | None:
    """toolkit_path: from .wire/local/data_apps.yml, parsed as plain lines so
    the script needs no YAML library."""
    f = repo_root / ".wire" / "local" / "data_apps.yml"
    if not f.is_file():
        return None
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*toolkit_path\s*:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip("\"'")
    return None


def resolve_toolkit(arg: str | None, repo_root: Path) -> Path:
    cand = arg or os.environ.get("WIRE_DATA_APPS_TOOLKIT") or local_toolkit_path(repo_root) \
        or str(Path.home() / "looker-data-apps")
    return Path(os.path.expanduser(cand)).resolve()


def resolve_pin(arg: str | None) -> tuple[str | None, str]:
    p = Path(arg) if arg else Path(__file__).resolve().parent.parent / "data_apps" / "pinned_toolkit_version.txt"
    if p.is_file():
        return p.read_text(encoding="utf-8").strip(), str(p)
    return None, str(p)


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def compare_versions(installed: str | None, pin: str | None) -> str:
    if not installed:
        return "missing"
    if not pin:
        return "unpinned"
    a, b = version_tuple(installed), version_tuple(pin)
    return "older" if a < b else "equal" if a == b else "newer"


# ----------------------------------------------------------------------
# app.js header tags
# ----------------------------------------------------------------------

def header_span(text: str) -> tuple[int, int] | None:
    """Start and end offsets of the first JSDoc block, or None."""
    m = re.search(r"/\*\*.*?\*/", text, re.DOTALL)
    return (m.start(), m.end()) if m else None


def tag_lines(text: str) -> dict[str, str]:
    span = header_span(text)
    if not span:
        return {}
    tags = {}
    for line in text[span[0]:span[1]].splitlines():
        m = re.match(r"^\s*\*?\s*(@[\w-]+)\s+(.*?)\s*$", line)
        if m and m.group(1) in PUBLISH_TAGS:
            tags[m.group(1)] = m.group(2)
    return tags


def title_tag(text: str) -> str | None:
    span = header_span(text)
    if not span:
        return None
    m = re.search(r"@title\s+(.+)", text[span[0]:span[1]])
    return m.group(1).strip() if m else None


def strip_tags(text: str) -> str:
    """The file without the publish tag lines, for comparison. The publisher
    (1.2.0) writes a blank ` *` separator line before its tags; that line
    goes too, or a copy that was only published reads as an edit."""
    span = header_span(text)
    if not span:
        return text
    head = text[span[0]:span[1]]
    tag_re = re.compile(r"^\s*\*?\s*(" + "|".join(re.escape(t) for t in PUBLISH_TAGS) + r")\b")
    lines = head.splitlines(keepends=True)
    kept = []
    for i, line in enumerate(lines):
        if tag_re.match(line):
            continue
        if line.strip() == "*" and any(tag_re.match(l) for l in lines[i + 1:]):
            continue
        kept.append(line)
    return text[:span[0]] + "".join(kept) + text[span[1]:]


def merge_tags(target_text: str, tags: dict[str, str]) -> str:
    """Write the given tags into the target's header: replace a tag that is
    there, add the rest before the closing */."""
    if not tags:
        return target_text
    span = header_span(target_text)
    if not span:
        block = "/**\n" + "".join(f" * {k} {v}\n" for k, v in tags.items()) + " */\n"
        return block + target_text
    head = target_text[span[0]:span[1]]
    lines = head.splitlines(keepends=True)
    out = []
    done = set()
    for line in lines:
        m = re.match(r"^(\s*\*?\s*)(@[\w-]+)\s+.*?(\r?\n?)$", line)
        if m and m.group(2) in tags:
            out.append(f"{m.group(1)}{m.group(2)} {tags[m.group(2)]}{m.group(3) or chr(10)}")
            done.add(m.group(2))
        else:
            out.append(line)
    closing = out.pop()  # the ' */' line
    for k, v in tags.items():
        if k not in done:
            out.append(f" * {k} {v}\n")
    out.append(closing)
    return target_text[:span[0]] + "".join(out) + target_text[span[1]:]


# ----------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------

def cmd_check(args, toolkit: Path) -> int:
    pin, pin_path = resolve_pin(args.pin)
    version_file = toolkit / "VERSION"
    installed = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None
    config = toolkit / "data-apps-config.json"
    config_keys: list[str] = []
    base_host = None
    if config.is_file():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config_keys = sorted(data.keys())
                base = data.get("base_url")
                if isinstance(base, str):
                    base_host = re.sub(r"^https?://", "", base).split("/")[0]
        except json.JSONDecodeError:
            config_keys = ["<unparseable>"]
    tools = {str(t): (toolkit / t).is_file() for t in REQUIRED_TOOLS}
    report = {
        "toolkit": str(toolkit),
        "present": toolkit.is_dir(),
        "version": installed,
        "pin": pin,
        "pin_file": pin_path,
        "version_vs_pin": compare_versions(installed, pin),
        "config_present": config.is_file(),
        "config_keys": [k if k not in SECRET_KEYS else f"{k} (masked)" for k in config_keys],
        "instance_host": base_host,
        "apps_dir": (toolkit / "apps").is_dir(),
        "tools": tools,
    }
    problems = []
    if not report["present"]:
        problems.append("toolkit not found; install it: bash <(curl -fsSL https://dl.google.com/looker-data-apps/install.sh)")
    if report["present"] and not installed:
        problems.append("no VERSION file in the toolkit")
    if report["version_vs_pin"] == "older":
        problems.append(f"toolkit {installed} is older than the pin {pin}; upgrade it (skills/toolkit-updater/SKILL.md)")
    if report["present"] and not report["config_present"]:
        problems.append("no data-apps-config.json; run bash scripts/bootstrap.sh in the toolkit")
    if report["present"] and not all(tools.values()):
        problems.append("toolkit tools missing: " + ", ".join(t for t, ok in tools.items() if not ok))
    report["problems"] = problems
    if report["version_vs_pin"] == "newer":
        report["warning"] = f"toolkit {installed} is newer than the pin {pin}; record it in status"
    emit(args, report)
    return 1 if problems else 0


def app_paths(args, toolkit: Path) -> tuple[Path, Path]:
    source = Path(args.source).resolve()
    if source.is_file():
        source = source.parent
    return source, toolkit / "apps" / args.app


def cmd_push(args, toolkit: Path) -> int:
    source, target = app_paths(args, toolkit)
    src_js = source / "app.js"
    if not src_js.is_file():
        return fail(args, f"no app.js in {source}")
    src_text = src_js.read_text(encoding="utf-8")
    tgt_js = target / "app.js"
    carried: dict[str, str] = {}
    if tgt_js.is_file():
        tgt_text = tgt_js.read_text(encoding="utf-8")
        if strip_tags(tgt_text) != strip_tags(src_text) and not args.force:
            if strip_tags(tgt_text) == strip_tags(src_text):
                pass
            diff = unified(strip_tags(tgt_text), strip_tags(src_text), str(tgt_js), str(src_js))
            # The toolkit copy differs from the repo copy. If the repo copy is
            # simply newer (the usual case) the push is what the user asked
            # for; refuse only when the toolkit copy carries lines the repo
            # copy never had, which means someone edited the working copy.
            if toolkit_has_edits(strip_tags(tgt_text), strip_tags(src_text), args.last_pushed):
                emit(args, {"refused": True, "reason": "the toolkit copy was edited since the last push; "
                            "pull it, or push with --force to overwrite", "diff": diff})
                return 1
        tgt_tags = tag_lines(tgt_text)
        src_tags = tag_lines(src_text)
        carried = {k: v for k, v in tgt_tags.items() if k not in src_tags}
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for f in sorted(source.iterdir()):
        if f.name.startswith(".") or not f.is_file():
            continue
        if f.name == "app.js":
            text = merge_tags(src_text, carried) if carried else src_text
            tgt_js.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(f, target / f.name)
        written.append(f.name)
    (target / ".wire-last-push.js").write_text(strip_tags(src_text), encoding="utf-8")
    report = {"pushed": written, "target": str(target), "carried_tags": carried}
    if carried:
        report["note"] = "the toolkit copy had publish tags the repo copy lacks; they were kept. Run pull --tags-only to bring them into the repo"
    emit(args, report)
    return 0


def toolkit_has_edits(tgt_body: str, src_body: str, last_pushed: str | None) -> bool:
    """True when the toolkit copy differs from what the last push wrote (so
    someone edited it there). Without a record of the last push, any
    difference counts."""
    marker = Path(last_pushed) if last_pushed else None
    if marker and marker.is_file():
        return tgt_body != marker.read_text(encoding="utf-8")
    return tgt_body != src_body


def cmd_pull(args, toolkit: Path) -> int:
    source, target = app_paths(args, toolkit)
    tgt_js = target / "app.js"
    if not tgt_js.is_file():
        return fail(args, f"no toolkit copy at {tgt_js}")
    tgt_text = tgt_js.read_text(encoding="utf-8")
    src_js = source / "app.js"
    if args.tags_only:
        if not src_js.is_file():
            return fail(args, f"no app.js in {source}")
        tags = tag_lines(tgt_text)
        if not tags:
            emit(args, {"pulled_tags": {}, "note": "the toolkit copy carries no publish tags"})
            return 0
        src_js.write_text(merge_tags(src_js.read_text(encoding="utf-8"), tags), encoding="utf-8")
        emit(args, {"pulled_tags": tags, "source": str(src_js)})
        return 0
    source.mkdir(parents=True, exist_ok=True)
    changed = (not src_js.is_file()) or src_js.read_text(encoding="utf-8") != tgt_text
    src_js.write_text(tgt_text, encoding="utf-8")
    emit(args, {"pulled": "app.js", "source": str(src_js), "changed": changed})
    return 0


def unified(a: str, b: str, name_a: str, name_b: str) -> str:
    return "".join(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                        fromfile=name_a, tofile=name_b))


def cmd_diff(args, toolkit: Path) -> int:
    source, target = app_paths(args, toolkit)
    src_js, tgt_js = source / "app.js", target / "app.js"
    if not src_js.is_file() or not tgt_js.is_file():
        return fail(args, f"need both {src_js} and {tgt_js}")
    a, b = strip_tags(src_js.read_text(encoding="utf-8")), strip_tags(tgt_js.read_text(encoding="utf-8"))
    same = a == b
    report = {"same": same, "source_tags": tag_lines(src_js.read_text(encoding="utf-8")),
              "toolkit_tags": tag_lines(tgt_js.read_text(encoding="utf-8"))}
    if not same:
        report["diff"] = unified(a, b, str(src_js), str(tgt_js))
    emit(args, report)
    return 0 if same else 1


def run_tool(toolkit: Path, tool: Path, extra: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(tool), *extra], cwd=toolkit, capture_output=True,
                          text=True, timeout=timeout)


def cmd_verify(args, toolkit: Path) -> int:
    tool = toolkit / VERIFY_TOOL
    if not tool.is_file():
        return fail(args, f"verify tool not found: {tool}")
    rel = f"apps/{args.app}/app.js"
    if not (toolkit / rel).is_file():
        return fail(args, f"no toolkit copy at {toolkit / rel}; run push first")
    extra = [rel, "--json"] + ([] if args.browser else ["--no-browser"])
    proc = run_tool(toolkit, tool, extra, args.timeout)
    payload = parse_json_output(proc.stdout)
    if payload is None:
        emit(args, {"verify": "unverified", "exit": proc.returncode,
                    "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:]})
        return 2
    syntax = payload.get("syntax") or {}
    queries = payload.get("queries") or []
    summary = {
        "verify": "pass" if payload.get("passed") else "fail",
        "exit": proc.returncode,
        "syntax_ok": bool(syntax.get("ok", True)),
        "safety_findings": payload.get("safety") or [],
        "warnings": payload.get("warnings") or [],
        "queries_checked": len(queries),
        "queries_failed": [query_summary(q) for q in queries if isinstance(q, dict) and not query_ok(q)],
        "queries_empty": [query_summary(q) for q in queries if isinstance(q, dict) and query_ok(q)
                          and (q.get("result") or {}).get("is_empty")],
        "visual": payload.get("visual") or {},
        "widget_extraction": payload.get("widget_extraction") or {},
    }
    if args.raw:
        summary["raw"] = payload
    emit(args, summary)
    return 0 if summary["verify"] == "pass" else 1


def query_ok(q: dict) -> bool:
    """verify-app.py (1.2.0) reports each dry run as {"query": {...},
    "result": {"ok", "is_empty", "rows_count", "error"}}. Older shapes put
    ok at the top level; read both."""
    result = q.get("result")
    if isinstance(result, dict) and "ok" in result:
        return bool(result["ok"])
    return bool(q.get("ok", True))


def query_summary(q: dict) -> dict:
    query = q.get("query") if isinstance(q.get("query"), dict) else {}
    result = q.get("result") if isinstance(q.get("result"), dict) else {}
    return {
        "widget": query.get("widget") or q.get("widget"),
        "title": query.get("title") or q.get("title"),
        "fields": query.get("fields") or q.get("fields"),
        "error": result.get("error") or q.get("error"),
        "rows_count": result.get("rows_count", q.get("rows_count")),
    }


def parse_json_output(stdout: str):
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def publish_command(args, toolkit: Path) -> tuple[list[str], dict]:
    rel = f"apps/{args.app}/app.js"
    js = toolkit / rel
    if not js.is_file():
        raise SystemExit(f"ERROR: no toolkit copy at {js}; run push first")
    text = js.read_text(encoding="utf-8")
    tags = tag_lines(text)
    dashboard_id = args.dashboard_id or (tags.get("@looker-dashboard-id") or "").strip() or None
    title = args.title or title_tag(text) or args.app
    config = toolkit / "data-apps-config.json"
    folder = args.folder_id
    host = None
    if config.is_file():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            folder = folder or str(data.get("publish_folder_id") or "") or None
            base = data.get("base_url")
            if isinstance(base, str):
                host = re.sub(r"^https?://", "", base).split("/")[0]
        except json.JSONDecodeError:
            pass
    cmd = [sys.executable, str(PUBLISH_TOOL), "--def", rel, "--title", title]
    if args.folder_id:
        cmd += ["--folder-id", args.folder_id]
    if dashboard_id:
        cmd += ["--dashboard-id", dashboard_id]
    if getattr(args, "confirm_replace", False):
        cmd += ["--confirm-replace"]
    plan = {
        "app": args.app,
        "title": title,
        "instance_host": host,
        "publish_folder_id": folder,
        "mode": "re-publish" if dashboard_id else "first publish",
        "dashboard_id": dashboard_id,
        "toolkit": str(toolkit),
        "command": " ".join(cmd),
        "confirm_replace": bool(getattr(args, "confirm_replace", False)),
    }
    return cmd, plan


def cmd_publish(args, toolkit: Path) -> int:
    cmd, plan = publish_command(args, toolkit)
    if args.mode == "plan":
        emit(args, plan)
        return 0
    if not args.confirm:
        emit(args, {**plan, "refused": True,
                    "reason": "publish run needs --confirm after the user has seen the plan"})
        return 2
    if not (toolkit / PUBLISH_TOOL).is_file():
        return fail(args, f"publisher not found: {toolkit / PUBLISH_TOOL}")
    proc = subprocess.run(cmd, cwd=toolkit, capture_output=True, text=True, timeout=args.timeout)
    out = proc.stdout
    envelope = None
    for line in out.splitlines() + proc.stderr.splitlines():
        if line.startswith("ERROR_ENVELOPE_JSON:"):
            try:
                envelope = json.loads(line.split(":", 1)[1].strip())
            except json.JSONDecodeError:
                envelope = {"raw": line}
    url_m = re.search(r"https?://\S+/dashboards/(\d+)", out)
    # publish-data-app.py 1.2.0 prints "registered N widget queries"; older
    # builds printed "N query/queries registered". Read both.
    registered = re.search(r"registered (\d+) widget quer", out) or re.search(r"(\d+) query/queries registered", out)
    result = {
        **plan,
        "exit": proc.returncode,
        "success": proc.returncode == 0 and url_m is not None,
        "dashboard_id": url_m.group(1) if url_m else plan["dashboard_id"],
        "dashboard_url": url_m.group(0) if url_m else None,
        "widget_queries_registered": int(registered.group(1)) if registered else None,
        "skipped": [l.strip() for l in out.splitlines() if l.strip().startswith("skipped:")],
        "warnings": [l.strip() for l in out.splitlines() if l.strip().startswith("warning:") or "WARNING:" in l],
        "error": envelope,
        "output_tail": out[-3000:],
    }
    if proc.returncode != 0 and not envelope:
        result["stderr_tail"] = proc.stderr[-2000:]
    emit(args, result)
    return 0 if result["success"] else 1


# ----------------------------------------------------------------------
# output
# ----------------------------------------------------------------------

def emit(args, obj: dict) -> None:
    if getattr(args, "format", "text") == "json":
        print(json.dumps(obj, indent=2, sort_keys=True))
        return
    for k, v in obj.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, sort_keys=True) if not (isinstance(v, str)) else v
        if k == "diff" and isinstance(obj[k], str):
            print("diff:")
            print(obj[k])
            continue
        print(f"{k}: {v}")


def fail(args, message: str) -> int:
    emit(args, {"error": message})
    return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--toolkit", help="toolkit root (default: see above)")
    ap.add_argument("--repo-root", default=".", help="repo root that holds .wire/local/data_apps.yml (default: cwd)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("--pin", help="pinned version file (default: wire/data_apps/pinned_toolkit_version.txt)")

    for name in ("push", "pull", "diff"):
        p = sub.add_parser(name)
        p.add_argument("--app", required=True)
        p.add_argument("--source", required=True, help="the app folder in the repo (holds app.js)")
        if name == "push":
            p.add_argument("--force", action="store_true", help="overwrite a toolkit copy that was edited there")
            p.add_argument("--last-pushed", help=argparse.SUPPRESS)
        if name == "pull":
            p.add_argument("--tags-only", action="store_true", help="bring only the publish tags into the repo header")

    v = sub.add_parser("verify")
    v.add_argument("--app", required=True)
    v.add_argument("--browser", action="store_true", help="also run stage 4 (headless browser)")
    v.add_argument("--raw", action="store_true", help="include the tool's own JSON")
    v.add_argument("--timeout", type=int, default=600)

    pb = sub.add_parser("publish")
    pb.add_argument("mode", choices=["plan", "run"])
    pb.add_argument("--app", required=True)
    pb.add_argument("--title")
    pb.add_argument("--folder-id")
    pb.add_argument("--dashboard-id", help="re-publish over this dashboard (default: the @looker-dashboard-id tag)")
    pb.add_argument("--confirm", action="store_true", help="required for run")
    pb.add_argument("--confirm-replace", action="store_true",
                    help="only after a user_mismatch envelope and the user's explicit yes")
    pb.add_argument("--timeout", type=int, default=900)

    args = ap.parse_args(argv)
    toolkit = resolve_toolkit(args.toolkit, Path(args.repo_root).resolve())
    if args.cmd == "push" and not args.last_pushed:
        args.last_pushed = str(toolkit / "apps" / args.app / ".wire-last-push.js")
    handlers = {"check": cmd_check, "push": cmd_push, "pull": cmd_pull, "diff": cmd_diff,
                "verify": cmd_verify, "publish": cmd_publish}
    return handlers[args.cmd](args, toolkit)


if __name__ == "__main__":
    sys.exit(main())

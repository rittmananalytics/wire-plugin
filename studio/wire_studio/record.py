"""Read a client repository's `.wire/` record. Read only: nothing here writes.

Every reader takes plain paths and returns plain data, so the behavioural test
can run it against a fixture repository with a fixed clock.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .runnable import resolve

STALL_MINUTES = 30  # director_operating_model.md: lane state files and the release claim
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".yml", ".yaml", ".json", ".jsonl", ".csv",
                 ".tsv", ".sql", ".lkml", ".lookml", ".py", ".mml", ".dbml", ".toml", ".ini"}
MAX_FILE_BYTES = 2_000_000
DENIED_PARTS = {".git", "node_modules", "__pycache__"}
COMPLETE_MARK = re.compile(r"^\s*(status|state)\s*:\s*complete\b|^\s*complete\b", re.I | re.M)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
def split_front_matter(text):
    """(front matter dict, body). status.md is YAML between the first two
    `---` lines, then Markdown."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    head = parts[0][3:]
    body = parts[1].split("\n", 1)[1] if len(parts) > 1 and "\n" in parts[1] else ""
    try:
        data = yaml.safe_load(head) or {}
    except yaml.YAMLError as e:
        return {"_error": f"status.md front matter is not valid YAML: {e}"}, body
    return (data if isinstance(data, dict) else {}), body


def artifacts_from_body(body):
    """Older status files (3.x) keep artifact states in a fenced YAML block
    under a `## Artifacts` or `## Artifact Status` heading in the body rather
    than in the front matter."""
    m = re.search(r"^##\s+Artifacts?(?:\s+Status)?\s*$.*?^```ya?ml\s*$(.*?)^```", body, re.M | re.S)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def find_releases(repo):
    """Release folders under `.wire/releases/`, plus any pre-3.4 flat-layout
    folder (`.wire/<id>/status.md`), which is reported as legacy."""
    wire = Path(repo) / ".wire"
    out = []
    for status in sorted((wire / "releases").glob("*/status.md")):
        out.append({"name": status.parent.name, "dir": status.parent, "legacy": False})
    for status in sorted(wire.glob("*/status.md")):
        if status.parent.name not in {"releases", "engagement"}:
            out.append({"name": status.parent.name, "dir": status.parent, "legacy": True})
    return out


def read_engagement(repo):
    ctx = Path(repo) / ".wire" / "engagement" / "context.md"
    if not ctx.is_file():
        return {"present": False, "orchestration_mode": "orchestrated"}
    text = ctx.read_text(encoding="utf-8", errors="replace")
    fm, body = split_front_matter(text)
    mode = ((fm.get("orchestration") or {}).get("mode") if isinstance(fm.get("orchestration"), dict) else None)
    if not mode:
        m = re.search(r"orchestration\.mode:\s*(\w+)|^\s*mode:\s*(manual|orchestrated)\b", text, re.M)
        mode = (m.group(1) or m.group(2)) if m else "orchestrated"
    title = fm.get("engagement_name") or fm.get("client_name")
    if not title:
        h = re.search(r"^#\s+(.+)$", body, re.M)
        title = h.group(1).strip() if h else Path(repo).name
    return {"present": True, "title": str(title), "orchestration_mode": mode}


# ---------------------------------------------------------------------------
# Execution log, decisions, lanes, iterations
# ---------------------------------------------------------------------------
def parse_markdown_table(text, first_header):
    """Rows of the first Markdown table whose header starts with `first_header`,
    as dicts keyed by header. Copes with the 4-column and 9-column log forms."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        cells = _cells(line)
        if cells and cells[0].lower() == first_header.lower():
            header, rows = cells, []
            for row in lines[i + 2:]:
                if not row.strip().startswith("|"):
                    break
                vals = _cells(row)
                rows.append({h: (vals[j] if j < len(vals) else "") for j, h in enumerate(header)})
            return rows
    return []


def _cells(line):
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def spend_of(log_rows):
    """AI spend the execution log records for a release: the sum of the Cost
    and Tokens cells the Wire mod (4.1.0) or the workflow filled. Rows still
    `n/a`, or legacy rows without the columns, count as unmeasured."""
    cost = 0.0
    tokens = 0
    measured = 0
    for row in log_rows:
        c = (row.get("Cost (USD)") or "").strip()
        t = (row.get("Tokens") or "").strip()
        if not re.fullmatch(r"\$?\d+(\.\d+)?", c) or not t.isdigit():
            continue
        cost += float(c.lstrip("$"))
        tokens += int(t)
        measured += 1
    return {"cost": round(cost, 2), "tokens": tokens, "measured_rows": measured, "rows": len(log_rows)}


def read_execution_log(release_dir):
    p = Path(release_dir) / "execution_log.md"
    if not p.is_file():
        return []
    return parse_markdown_table(p.read_text(encoding="utf-8", errors="replace"), "Timestamp")


RULING_BLOCK = re.compile(r"^##\s*(R-\d+)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*(.*)$", re.M)


def read_rulings(release_dir):
    """Every ruling block in decisions.md: id, when, who, title, what it applies
    to and the ruling text."""
    p = Path(release_dir) / "decisions.md"
    if not p.is_file():
        return [], ""
    text = p.read_text(encoding="utf-8", errors="replace")
    out = []
    for block in re.split(r"(?m)^(?=## R-\d)", text):
        h = RULING_BLOCK.search(block)
        if not h:
            continue
        applies = re.search(r"^Applies to:\s*(.+)$", block, re.M)
        ruling = re.search(r"^Ruling:\s*(.+)$", block, re.M)
        out.append({"id": h.group(1), "when": h.group(2).strip(), "by": h.group(3).strip(),
                    "title": h.group(4).strip(),
                    "applies_to": applies.group(1).strip() if applies else "",
                    "ruling": ruling.group(1).strip() if ruling else ""})
    return out, text


def read_lanes(release_dir, now):
    """One entry per lane state file. A lane not marked complete with no write
    for 30 minutes is stalled (the resume contract makes re-dispatch safe)."""
    lanes = []
    for p in sorted((Path(release_dir) / "lanes").glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        modified = datetime.fromtimestamp(p.stat().st_mtime)
        age = now - modified
        complete = bool(COMPLETE_MARK.search(text))
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        lanes.append({
            "label": p.stem,
            "path": str(p.relative_to(Path(release_dir))),
            "last_write": modified.strftime("%Y-%m-%d %H:%M"),
            "minutes_since_write": int(age.total_seconds() // 60),
            "state": "complete" if complete else (
                "stalled" if age > timedelta(minutes=STALL_MINUTES) else "running"),
            "summary": lines[-1][:240] if lines else "",
            "text": text[:20000],
        })
    return lanes


def read_iterations(body, release_dir):
    rows = []
    m = re.search(r"^##\s+Iterations\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    if m:
        lines = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]
        if lines:
            rows = parse_markdown_table("\n".join(lines), _cells(lines[0])[0])
    files = sorted(p.name for p in (Path(release_dir) / "iterations").glob("*.md"))
    return {"rows": rows, "files": files}


def claim_state(status, now):
    claim = ((status.get("agents") or {}).get("coordinator_session")) or None
    if not isinstance(claim, dict):
        return {"held": False}
    last = claim.get("last_write") or claim.get("claimed_at")
    stale = False
    if last:
        try:
            stale = now - datetime.strptime(str(last), "%Y-%m-%d %H:%M") > timedelta(minutes=STALL_MINUTES)
        except ValueError:
            pass
    return {"held": True, "user": claim.get("user"), "branch": claim.get("branch"),
            "last_write": last, "stale": stale}


# ---------------------------------------------------------------------------
# Decision inbox and directives
# ---------------------------------------------------------------------------
def build_inbox(release, status, resolved):
    """Everything waiting on the director, each with the directive to paste into
    the orchestrating session. Studio never records a decision itself."""
    items = []
    for d in status.get("parked_decisions") or []:
        if not isinstance(d, dict):
            continue
        did = d.get("id", "?")
        items.append({
            "id": f"parked:{did}", "kind": d.get("kind", "ruling"), "ref": did,
            "artifact": d.get("artifact"), "question": d.get("question", ""),
            "since": str(d.get("parked_at", "")), "awaiting": d.get("awaiting"),
            "directive": f"Ruling on {did}: <your decision>. Reason: <why>.",
        })
    graph = {g["id"]: g for g in resolved["graph"]}
    for art, state in resolved["states"].items():
        if state == "parked: needs ruling (review)":
            cmd = graph[art]["command"]
            items.append({
                "id": f"review:{art}", "kind": "review", "ref": art, "artifact": art,
                "question": f"Review {art}: generated and validated, waiting for approval.",
                "since": "", "awaiting": None,
                "directive": f"/wire:{cmd}-review {release}",
            })
        elif state.startswith("parked: needs ruling (proceed without "):
            dep = state.split("proceed without ", 1)[1].rstrip("?)")
            items.append({
                "id": f"gate:{art}:{dep}", "kind": "advisory gate", "ref": art, "artifact": art,
                "question": f"{art} has an advisory dependency on {dep}, which is not done. Proceed without it?",
                "since": "", "awaiting": None,
                "directive": (f"Ruling: proceed without {dep} for {art} in {release} "
                              f"(advisory). Reason: <why>."),
            })
    return items


def run_plan_directive(release, resolved):
    graph = {g["id"]: g for g in resolved["graph"]}
    steps = []
    for art in resolved["parallel"]:
        action = resolved["states"][art].split(": ", 1)[1]
        steps.append(f"/wire:{graph[art]['command']}-{action} {release}")
    if not steps:
        return None
    return {"commands": steps,
            "directive": f"Show me the run plan for {release}: " + "; ".join(steps) + ". Then wait for go."}


# ---------------------------------------------------------------------------
# One release, assembled
# ---------------------------------------------------------------------------
def load_release(framework, repo, name, now=None):
    now = now or datetime.now()
    match = [r for r in find_releases(repo) if r["name"] == name]
    if not match:
        raise KeyError(name)
    rel = match[0]
    text = (rel["dir"] / "status.md").read_text(encoding="utf-8", errors="replace")
    status, body = split_front_matter(text)
    if not text.startswith("---"):
        status["_error"] = ("status.md has no YAML front matter, so Studio cannot read its "
                            "artifact states")
    if not status.get("artifacts"):
        body_artifacts = artifacts_from_body(body)
        if body_artifacts:
            status["artifacts"] = body_artifacts
    rulings, decisions_md = read_rulings(rel["dir"])
    out = {
        "name": name, "legacy": rel["legacy"],
        "project_type": status.get("project_type") or status.get("release_type"),
        "client_name": status.get("client_name"),
        "current_phase": status.get("current_phase"),
        "last_updated": str(status.get("last_updated", "")),
        "budget": status.get("budget"),
        "claim": claim_state(status, now),
        "rulings": rulings,
        "execution_log": read_execution_log(rel["dir"]),
        "spend": None,
        "lanes": read_lanes(rel["dir"], now),
        "iterations": read_iterations(body, rel["dir"]),
        "error": status.get("_error"),
    }
    out["spend"] = spend_of(out["execution_log"])
    try:
        resolved = resolve(framework, status, decisions_md)
        out["resolved"] = resolved
        out["inbox"] = build_inbox(name, status, resolved)
        out["run_plan"] = run_plan_directive(name, resolved)
    except (ValueError, KeyError) as e:
        out["resolved"], out["inbox"], out["run_plan"] = None, [], None
        out["error"] = out["error"] or str(e)
    return out


def release_summaries(framework, repo, now=None):
    out = []
    for r in find_releases(repo):
        try:
            rel = load_release(framework, repo, r["name"], now)
        except Exception as e:  # one broken release must not hide the others
            out.append({"name": r["name"], "error": str(e)})
            continue
        states = (rel["resolved"] or {}).get("states", {})
        out.append({
            "name": rel["name"], "project_type": rel["project_type"], "legacy": rel["legacy"],
            "complete": sum(1 for s in states.values() if s == "complete"),
            "total": sum(1 for s in states.values() if s != "not applicable"),
            "waiting": len(rel["inbox"]),
            "lanes_live": sum(1 for l in rel["lanes"] if l["state"] != "complete"),
            "error": rel["error"],
        })
    return out


def safe_file(repo, release, rel_path):
    """Resolve a path a release refers to, refusing anything outside the
    repository, inside .git or similar, not a text file, or too large."""
    repo = Path(repo).resolve()
    if not rel_path or "\x00" in rel_path or Path(rel_path).is_absolute():
        raise PermissionError("path must be relative")
    candidates = []
    rels = [r for r in find_releases(repo) if r["name"] == release]
    if rels:
        candidates.append(rels[0]["dir"] / rel_path)
    candidates.append(repo / rel_path)
    for c in candidates:
        p = c.resolve()
        try:
            p.relative_to(repo)
        except ValueError:
            raise PermissionError("path is outside the repository")
        if DENIED_PARTS & set(p.relative_to(repo).parts) or p.name.startswith(".env"):
            raise PermissionError("path is not readable from Studio")
        if p.is_file():
            if p.suffix.lower() not in TEXT_SUFFIXES:
                raise PermissionError("only text files can be previewed")
            if p.stat().st_size > MAX_FILE_BYTES:
                raise PermissionError("file is larger than 2 MB")
            return p
    raise FileNotFoundError(rel_path)

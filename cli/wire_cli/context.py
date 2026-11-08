"""The Wire mod's release text in the session (ROADMAP.md phase 4).

Ports of the Claude Code mod's builders (packaging/claude-plugin/hooks/wire/
release.ts), held to the same strings by the mod's own test expectations
(tests/context.test.ts), so the two front ends say the same thing:

- status_line       `[Wire v4.5.0] 02-data-foundation (full_platform) · 5 approved · 1 parked · claim: Consultant A · ctx:42%`
- release_context   the bounded section the agent gets once per conversation:
                    next action, claim, parked decisions, last rulings, the
                    business-rules register by domain, iterations in flight
- rulings_of, business_rules_summary, open_iterations_of, approved_count
"""

from __future__ import annotations

import re
from pathlib import Path

CONTEXT_WARN_PERCENT = 85


def rulings_of(decisions_md: str | None) -> list:
    out = []
    for line in (decisions_md or "").split("\n"):
        m = re.match(r"^##\s*(R-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(.*)$", line)
        if m:
            out.append({"id": m.group(1), "date": m.group(2).strip(), "who": m.group(3).strip(), "title": m.group(4).strip()})
    return out


def business_rules_summary(rules: list, today: str) -> dict:
    """Rule counts by domain and status, and assumed rules past confirm_by.
    `rules` is the register's list (artifacts/business_rules.yaml)."""
    out = {"by_domain": {}, "assumed_overdue": []}
    for r in rules or []:
        if not isinstance(r, dict):
            continue
        domain = str(r.get("domain") or "unassigned")
        status = str(r.get("status") or "unknown")
        out["by_domain"].setdefault(domain, {})
        out["by_domain"][domain][status] = out["by_domain"][domain].get(status, 0) + 1
        confirm = str(r.get("confirm_by") or "")[:10]
        if status == "assumed" and confirm and confirm < today[:10]:
            out["assumed_overdue"].append({"id": str(r.get("id") or ""), "confirm_by": confirm})
    return out


def open_iterations_of(body: str) -> list:
    start = (body or "").find("## Iterations")
    if start < 0:
        return []
    rows = []
    for line in body[start:].split("\n")[1:]:
        if line.startswith("## "):
            break
        t = line.strip()
        if not t.startswith("|"):
            continue
        cells = [c.strip() for c in t[1:-1].split("|")]
        if not cells or cells[0] == "Id" or re.match(r"^[-:\s]+$", cells[0] or ""):
            continue
        state = (cells[2] if len(cells) > 2 else "").lower()
        if cells[0] and state not in ("closed", "merged", "done", "complete"):
            rows.append({"id": cells[0], "title": cells[1] if len(cells) > 1 else "", "state": cells[2] if len(cells) > 2 else ""})
    return rows


def approved_count(artifacts: dict) -> int:
    return sum(1 for a in (artifacts or {}).values() if isinstance(a, dict) and a.get("review") == "approved")


def status_line(version: str, release: str | None, candidates: list, project_type: str | None, approved: int,
                parked: int, claim_user: str | None, context_percent: int | None) -> str:
    head = f"[Wire v{version}]"
    ctx = "" if context_percent is None else f" · ctx:{context_percent}%"
    if not release:
        if len(candidates) > 1:
            return f"{head} {len(candidates)} releases active: {', '.join(candidates)} (say which){ctx}"
        return f"{head} no active release{ctx}"
    return (f"{head} {release} ({project_type or 'unknown type'}) · {approved} approved · {parked} parked"
            f" · claim: {claim_user or 'none'}{ctx}")


def release_context(release: str, project_type: str | None, profile: str | None, phase: str | None,
                    next_action: str | None, parked: list, rulings: list, rules: dict, iterations: list,
                    claim: dict | None, mode: str = "orchestrated", max_lines: int = 40) -> str:
    lines = [f"Wire release context: {release}"
             + (f" ({project_type}{', profile ' + profile if profile else ''})" if project_type else "") + f", {mode} mode."]
    if phase:
        lines.append(f"Current phase: {phase}.")
    if next_action:
        lines.append(f"Next action: {next_action}")
    if claim:
        lines.append(f"Release claim: {claim.get('user')} (session {claim.get('session_id') or 'unknown'}, "
                     f"last write {claim.get('last_write') or 'unknown'}).")
    if parked:
        lines.append(f"Parked decisions ({len(parked)}), each cleared by a ruling in decisions.md:")
        for d in parked:
            aw = f", awaiting {d.get('awaiting')}" if d.get("awaiting") else ""
            lines.append(f"- {d.get('id')} ({d.get('artifact')}, {d.get('kind', 'ruling')}{aw}): {d.get('question')}")
    else:
        lines.append("Parked decisions: none.")
    last = (rulings or [])[-10:]
    if last:
        lines.append("Last rulings (decisions.md):")
        for r in last:
            lines.append(f"- {r['id']} | {r['date']} | {r['who']} | {r['title']}")
    domains = sorted((rules or {}).get("by_domain", {}))
    if domains:
        lines.append("Business rules register, by domain:")
        for d in domains:
            s = rules["by_domain"][d]
            lines.append(f"- {d}: " + ", ".join(f"{k} {s.get(k, 0)}" for k in ("agreed", "disputed", "assumed", "unknown")))
        for o in rules.get("assumed_overdue", []):
            lines.append(f"- {o['id']} is assumed and past its confirm_by ({o['confirm_by']}).")
    if iterations:
        lines.append("Iterations in flight:")
        for it in iterations:
            lines.append(f"- {it['id']} {it['title']} ({it['state']})")
    mx = max(5, max_lines)
    if len(lines) > mx:
        return "\n".join(lines[:mx - 1] + [f"({len(lines) - (mx - 1)} more lines not shown; run /wire:status {release})"])
    return "\n".join(lines)


def gather(repo: Path, release: str, status: dict, body: str, next_action: str | None, max_lines: int = 40) -> str:
    """release_context from the files of one release."""
    rel = repo / ".wire" / "releases" / release
    decisions = (rel / "decisions.md").read_text(encoding="utf-8") if (rel / "decisions.md").is_file() else ""
    rules = []
    reg = rel / "artifacts" / "business_rules.yaml"
    if reg.is_file():
        try:
            import yaml
            data = yaml.safe_load(reg.read_text(encoding="utf-8")) or {}
            rules = data.get("rules") if isinstance(data, dict) else data
        except Exception:  # noqa: BLE001 - a register that does not parse is left out
            rules = []
    from datetime import date
    claim = (status.get("agents") or {}).get("coordinator_session") if isinstance(status.get("agents"), dict) else None
    parked = [d for d in (status.get("parked_decisions") or []) if isinstance(d, dict)]
    return release_context(release, status.get("release_type") or status.get("project_type"), status.get("profile"),
                           status.get("current_phase") or status.get("phase"), next_action, parked, rulings_of(decisions),
                           business_rules_summary(rules or [], date.today().isoformat()), open_iterations_of(body or ""),
                           claim if isinstance(claim, dict) and claim.get("user") else None, max_lines=max_lines)

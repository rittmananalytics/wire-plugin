"""Releases built from tickets (Wire 4.2.0, wire#279), as Studio shows them.

A release with `delivery: tickets` in status.md keeps a ticket map
(`tickets.yaml`), one ticket record per ticket (`iterations/<ticket>.md`) and
one run log per ticket (`iterations/<ticket>.execution_log.md`). The rules
that turn those into a status table, a list of what can start and a roll-up
live in `scripts/ticket_delivery.py`, which ships beside Studio in both
layouts. Studio imports that script rather than keeping its own copy, so it
cannot give a different answer from the Wire session.

Read only, like the rest of Studio.
"""

import importlib.util
import re
from pathlib import Path

_MODULES = {}

CLOSED_STATES = {"closed"}
ENDED_STATES = {"cancelled", "escalated"}


def ticket_rules(framework):
    """The framework's `scripts/ticket_delivery.py`, imported once, or None
    when this framework predates 4.2.0."""
    path = Path(framework.root) / "scripts" / "ticket_delivery.py"
    if not path.is_file():
        return None
    key = str(path)
    if key not in _MODULES:
        spec = importlib.util.spec_from_file_location("wire_ticket_delivery", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODULES[key] = mod
    return _MODULES[key]


def is_ticket_release(status, release_dir):
    return status.get("delivery") == "tickets" and (Path(release_dir) / "tickets.yaml").is_file()


def _graph_path(framework, status):
    rtype = status.get("project_type") or status.get("release_type")
    if not rtype:
        return None
    from .framework import RELEASE_TYPE_ALIASES
    p = framework.release_types_dir / f"{RELEASE_TYPE_ALIASES.get(rtype, rtype)}.yaml"
    return p if p.is_file() else None


def _ticket_log_rows(release_dir, key, parse_table):
    p = Path(release_dir) / "iterations" / f"{key}.execution_log.md"
    if not p.is_file():
        return "", []
    text = p.read_text(encoding="utf-8", errors="replace")
    return text, parse_table(text, "Timestamp")


def read_tickets(framework, release, release_dir, status, now, parse_table):
    """Everything Studio shows for a ticket-built release, or None for a
    release built artifact by artifact. `parse_table` is record.py's table
    reader, passed in to avoid an import cycle."""
    if not is_ticket_release(status, release_dir):
        return None
    td = ticket_rules(framework)
    if td is None:
        return {"error": "This release is built from tickets, but this Wire framework has no "
                         "scripts/ticket_delivery.py (4.2.0 or later is needed)."}
    tmap = td.load_map(release_dir)
    records = td.load_records(release_dir)
    graph_path = _graph_path(framework, status)
    graph = td.load_graph(status, str(graph_path)) if graph_path else None
    cells = td.cells(tmap, records)
    rollup = td.rollup(tmap, cells)
    order = list(graph) if graph else []
    steps = []
    for sl in cells:
        for art in cells[sl]:
            if art not in steps:
                steps.append(art)
    steps.sort(key=lambda a: order.index(a) if a in order else len(order))
    slices = [{"id": sl, "cells": {a: cells[sl].get(a) for a in steps}}
              for sl in td.slice_order(tmap, cells)]
    run = td.runnable(tmap, records, graph, status.get("artifacts") or {})
    by_key = {t["ticket"]: t for t in run["tickets"]}

    release_log = Path(release_dir) / "execution_log.md"
    release_log_text = release_log.read_text(encoding="utf-8", errors="replace") if release_log.is_file() else ""
    stamp = now.strftime("%Y-%m-%d %H:%M")

    tickets, activity = [], []
    for t in tmap.get("tickets") or []:
        key = t["key"]
        rec = records.get(key, {})
        r = by_key.get(key, {"state": "cancelled" if rec.get("state") in ENDED_STATES else "unknown"})
        log_text, log_rows = _ticket_log_rows(release_dir, key, parse_table)
        pending = td.merge_log(release_log_text, log_text, key, stamp) if rec.get("merged") and log_text else []
        for row in log_rows:
            activity.append(dict(row, Ticket=key))
        tickets.append({
            "key": key, "title": t.get("title", ""), "url": t.get("url"),
            "kind": t.get("kind"), "slices": t.get("slices") or [], "steps": t.get("steps") or [],
            "record_state": rec.get("state", "planned"), "merged": bool(rec.get("merged")),
            "blocked": rec.get("blocked"), "results": rec.get("results") or {},
            "next": r.get("state"), "waits_on": r.get("waits_on", []), "unmet": r.get("unmet", []),
            "needs_ruling": r.get("needs_ruling", []),
            "log_rows": len(log_rows), "rows_awaiting_rollup": len(pending),
            "record": f"iterations/{key}.md",
        })
    activity.sort(key=lambda row: row.get("Timestamp", ""))

    live = [t for t in tickets if t["record_state"] not in ENDED_STATES]
    return {
        "tracker": tmap.get("tracker"), "tracker_project": tmap.get("tracker_project"),
        "design_source": tmap.get("design_source"), "imported": str(tmap.get("imported", "")),
        "steps": steps, "slices": slices, "release": rollup,
        "tickets": tickets, "link_check": run["link_check"], "activity": activity,
        "counts": {
            "total": len(live),
            "closed": sum(1 for t in live if t["record_state"] in CLOSED_STATES),
            "can_start": sum(1 for t in live if t["next"] == "can_start"),
            "in_progress": sum(1 for t in live if t["next"] == "in_progress"),
            "waiting": sum(1 for t in live if t["next"] == "waiting"),
            "blocked": sum(1 for t in live if t["next"] == "blocked"),
            "awaiting_rollup": sum(1 for t in live if t["rows_awaiting_rollup"]),
        },
    }


def ticket_inbox(release, tk):
    """What a ticket-built release is waiting on the director for, each with
    its directive: merged tickets to roll up, missing tracker links, tickets
    parked for a ruling."""
    items = []
    if not tk or tk.get("error"):
        return items
    pending = [t["key"] for t in tk["tickets"] if t["rows_awaiting_rollup"]]
    if pending:
        items.append({
            "id": "rollup", "kind": "roll-up", "ref": ", ".join(pending), "artifact": None,
            "question": (f"{len(pending)} merged ticket{'s' if len(pending) != 1 else ''} not yet in the "
                         f"release record: {', '.join(pending)}."),
            "since": "", "awaiting": None,
            "directive": f"/wire:status-sync {release}",
        })
    for lc in tk["link_check"]:
        if not lc["missing_in_tracker"]:
            continue
        missing = ", ".join(lc["missing_in_tracker"])
        items.append({
            "id": f"link:{lc['ticket']}", "kind": "tracker link", "ref": lc["ticket"], "artifact": None,
            "question": f"{lc['ticket']} waits for {missing} in Wire's order, but the tracker has no 'blocked by' link.",
            "since": "", "awaiting": None,
            "directive": (f"In {release}, add the missing tracker link: {lc['ticket']} is blocked by {missing}. "
                          f"Ask me before changing the tracker."),
        })
    for t in tk["tickets"]:
        for q in t["needs_ruling"]:
            dep = re.sub(r"^proceed without (.*)\?$", r"\1", q)
            items.append({
                "id": f"ticket-gate:{t['key']}:{dep}", "kind": "advisory gate", "ref": t["key"], "artifact": None,
                "question": f"{t['key']} has an advisory dependency on {dep}, which is not done. Proceed without it?",
                "since": "", "awaiting": None,
                "directive": f"Ruling: proceed without {dep} for {t['key']} in {release} (advisory). Reason: <why>.",
            })
    return items


def ticket_next(release, tk):
    """The tickets that can start now, each as the directive that works it."""
    if not tk or tk.get("error"):
        return None
    ready = [t["key"] for t in tk["tickets"] if t["next"] == "can_start"]
    if not ready:
        return None
    return {"tickets": ready, "commands": [f"/wire:work {release} {k}" for k in ready]}

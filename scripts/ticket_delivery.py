#!/usr/bin/env python3
"""ticket_delivery.py: the fixed rules of a release built from tickets (wire#279).

A release built from tickets keeps a ticket map (`tickets.yaml`) that says,
for each tracker ticket, which part of the release it covers (its slices) and
which Wire steps it covers. Each ticket has a ticket record
(`iterations/<ticket>.md`) whose front matter holds its progress, and a run
log (`iterations/<ticket>.execution_log.md`) in the execution-log format.

This script holds the parts of `specs/utils/ticket_delivery.md` that have one
right answer, so the Wire session does not work them out by hand:

  steps         the Wire steps a ticket covers, from its kind and slice kind
  propose       the proposed ticket map entry for each ticket read from the tracker
  refresh       new, changed and removed tickets since the last import
  status        the per-slice status table, and each step's state for the release
  runnable      which tickets can start, which wait and on what, and where
                Wire's order and the tracker's "blocked by" links disagree
  merge-log     the release execution-log rows a merged ticket adds
  design-source where a slice's table design comes from
  scope         whether /wire:work accepts a ticket in a ticket-built release

Judgement stays with the Wire session and the consultant: the kind of a
ticket and its slice when the design model has no link for it. Those arrive
here as inputs, marked as proposals, and the output says which need checking.

Reads and prints JSON. Writes nothing except `merge-log --write`, which
appends to the release's execution_log.md and is run by the Wire session after
the consultant confirms. Stdlib plus PyYAML.

Usage:
    python3 ticket_delivery.py status <release-dir> [--markdown]
    python3 ticket_delivery.py runnable <release-dir> [--graph <release-type.yaml>]
    python3 ticket_delivery.py merge-log <release-dir> <ticket> [--now "YYYY-MM-DD HH:MM"] [--write]
    python3 ticket_delivery.py refresh <release-dir> <tracker.json>
    python3 ticket_delivery.py propose <classified.json>
    python3 ticket_delivery.py design-source <release-dir> [--slice <slice>]
    python3 ticket_delivery.py scope <release-dir> <request.json>
"""

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
RELEASE_TYPES = HERE.parent / "release-types"
ALIASES = {"discovery": "discovery_shape_up"}

WHOLE_RELEASE = "whole_release"

# ---------------------------------------------------------------------------
# Kinds and recipes (specs/utils/ticket_delivery.md, "Ticket kinds" and
# "Slice kinds and their recipes")
# ---------------------------------------------------------------------------
TICKET_KINDS = ["requirements", "business_rules", "design", "build", "test", "review", "plain"]
SLICE_KINDS = ["release", "source", "entity", "derived", "metric", "report",
               "dashboard", "layer", "deliverable", "batch", "app", "other"]

# The steps a build ticket covers, by the kind of slice it builds. A slice
# kind that maps to no steps is plain work: no Wire command builds it.
BUILD_RECIPE = {
    "source": ["dbt", "data_quality"],
    "entity": ["data_model", "dbt", "data_quality"],
    "derived": ["data_model", "dbt", "data_quality"],
    "metric": ["semantic_layer"],
    "report": ["semantic_layer"],
    "dashboard": ["dashboards"],
    "layer": [],
    "deliverable": [],
    "batch": [],
    "app": [],
    "other": [],
    "release": [],
}

# The steps other ticket kinds cover, whatever the slice.
KIND_RECIPE = {
    "requirements": ["requirements"],
    "business_rules": ["business_rules"],
    "design": ["data_model"],
    "test": ["data_quality"],
    "plain": [],
}

# Modality object types (specs/utils/mml_import.md, "Entity type mapping")
# to slice kinds.
MML_TYPE_TO_SLICE_KIND = {
    "entity": "entity",
    "derived": "derived",
    "derivation": "derived",
    "aggregate": "derived",
    "metric": "metric",
    "data_product": "report",
    "source": "source",
}

# Steps that read the tables of upstream slices, so wait for the same step
# there. Design and test steps do not.
BUILD_STEPS = {"pipeline", "seed_data", "dbt", "semantic_layer", "dashboards"}

DONE_RESULTS = {"complete", "pass", "approved"}
ACTIVE_STATES = {"open", "awaiting_review", "awaiting_owner"}
ENDED_STATES = {"cancelled", "escalated"}

# Cell states, in the order the status table shows them.
CELL_SYMBOL = {
    "complete": "✅",
    "in_progress": "🔄",
    "blocked": "⚠️",
    "not_started": "⏸️",
}


def recipe(kind, slice_kind, design_covered=False):
    """The Wire steps a ticket covers.

    `design_covered`: another ticket in the map already covers this slice's
    data_model step (a design ticket for several tables), so a build ticket
    leaves it out.
    """
    if kind == "build":
        steps = list(BUILD_RECIPE.get(slice_kind, []))
        if design_covered and "data_model" in steps:
            steps.remove("data_model")
        return steps
    if kind == "review":
        return []  # named by the ticket itself: "<artifact>.review"; never guessed
    return list(KIND_RECIPE.get(kind, []))


def step_artifact(step):
    """`requirements.review` -> `requirements`; `dbt` -> `dbt`."""
    return step.split(".", 1)[0]


# ---------------------------------------------------------------------------
# Reading a release folder
# ---------------------------------------------------------------------------
def _front_matter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        data = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def load_map(release_dir):
    path = Path(release_dir) / "tickets.yaml"
    if not path.exists():
        raise SystemExit(f"No ticket map at {path}. Run /wire:tickets-import first.")
    data = yaml.safe_load(path.read_text()) or {}
    data.setdefault("slices", [])
    data.setdefault("tickets", [])
    return data


def load_records(release_dir):
    """Ticket progress from each ticket record's front matter."""
    out = {}
    folder = Path(release_dir) / "iterations"
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.md")):
        if path.name.endswith(".execution_log.md"):
            continue
        fm = _front_matter(path.read_text())
        key = fm.get("ticket")
        if key:
            out[str(key)] = fm
    return out


def load_status(release_dir):
    path = Path(release_dir) / "status.md"
    return _front_matter(path.read_text()) if path.exists() else {}


def load_graph(status, graph_path=None):
    """The release type's artifacts, with profile applied
    (specs/utils/runnable_set.md Step 1)."""
    if graph_path:
        data = yaml.safe_load(Path(graph_path).read_text())
    else:
        rtype = status.get("project_type") or status.get("release_type")
        if not rtype:
            return None
        rtype = ALIASES.get(rtype, rtype)
        path = RELEASE_TYPES / f"{rtype}.yaml"
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text())
    profile_field = data.get("profile_field")
    profile_id = (status.get(profile_field) if profile_field else None) or data.get("default_profile")
    profile = next((p for p in data.get("profiles") or [] if p.get("id") == profile_id), {})
    disabled = set(profile.get("disable_phases") or [])
    overrides = {}
    for o in profile.get("phase_overrides") or []:
        for a in o.get("artifacts") or []:
            overrides[a.get("id")] = a.get("depends_on") or []
    graph = {}
    for phase in data.get("phases") or []:
        for art in phase.get("artifacts") or []:
            graph[art["id"]] = {
                "depends_on": overrides.get(art["id"], art.get("depends_on") or []),
                "disabled": phase.get("id") in disabled,
            }
    return graph


# ---------------------------------------------------------------------------
# propose: the ticket map entry for each ticket read from the tracker
# ---------------------------------------------------------------------------
def propose(payload):
    """`payload`:
        design_source: wire | modality
        modality_links: {ticket: object}      the model's own ticket links
        modality_objects: {object: mml_type}  every object in the model
        release_projects: [tracker project names that map to this release]
        tickets: [{key, title, project, kind, slice_hint, slice_kind,
                   matched_object, state}]
    `kind`, `slice_hint`, `slice_kind` and `matched_object` are the Wire
    session's proposals from the ticket's title and text.
    """
    modality = payload.get("design_source") == "modality"
    links = payload.get("modality_links") or {}
    objects = payload.get("modality_objects") or {}
    in_release = set(payload.get("release_projects") or [])

    entries, questions, unmatched = [], [], {}
    for t in payload.get("tickets") or []:
        project = t.get("project")
        if in_release and project not in in_release:
            unmatched.setdefault(project, []).append(t["key"])
            continue
        kind = t.get("kind") or "plain"
        slices, slice_kinds, source, check = [], [], None, False
        linked = links.get(t["key"])
        if modality and linked:
            linked = linked if isinstance(linked, list) else [linked]
            slices = list(linked)
            slice_kinds = [MML_TYPE_TO_SLICE_KIND.get(objects.get(o, "entity"), "other") for o in linked]
            source = "modality_link"
        elif modality and t.get("matched_object") in objects:
            slices = [t["matched_object"]]
            slice_kinds = [MML_TYPE_TO_SLICE_KIND.get(objects[t["matched_object"]], "other")]
            source = "modality_match"
            check = True
        else:
            hint = t.get("slice_hint") or WHOLE_RELEASE
            slices = hint if isinstance(hint, list) else [hint]
            sk = t.get("slice_kind") or ("release" if slices == [WHOLE_RELEASE] else "other")
            slice_kinds = [sk] * len(slices)
            source = "proposed"
            # Requirements and business rules cover the whole release by
            # nature; nothing to check.
            check = not (slices == [WHOLE_RELEASE] and kind in ("requirements", "business_rules"))
        entries.append({
            "key": t["key"],
            "title": t.get("title", ""),
            "kind": kind,
            "slices": slices,
            "slice_kinds": slice_kinds,
            "slice_source": source,
            "needs_check": check,
            "blocked_by": list(t.get("blocked_by") or []),
            "steps_named": list(t.get("steps") or []),
        })

    # Steps: a build ticket leaves out data_model where a design ticket covers
    # the same slice.
    design_slices = {s for e in entries if e["kind"] == "design" for s in e["slices"]}
    for e in entries:
        if e["steps_named"]:
            steps = e["steps_named"]
        else:
            steps = []
            for sk, sl in zip(e["slice_kinds"], e["slices"]):
                for st in recipe(e["kind"], sk, design_covered=sl in design_slices):
                    if st not in steps:
                        steps.append(st)
        e["steps"] = steps
        del e["steps_named"]
        e["plain"] = not steps
        open_kinds = {"layer", "deliverable", "batch"}
        if e["plain"] and (e["kind"] == "review" or set(e["slice_kinds"]) & open_kinds):
            e["plain"] = False
            questions.append({"ticket": e["key"], "question": "name_steps",
                              "text": "Which Wire steps does this ticket cover? They cannot be read from its slice."})
        elif e["plain"]:
            questions.append({"ticket": e["key"], "question": "plain_work",
                              "text": "No Wire command builds this. Track it as plain work, outside Wire's steps?"})
        elif e["needs_check"]:
            questions.append({"ticket": e["key"], "question": "check_slice",
                              "text": f"Proposed slice {', '.join(e['slices'])}. Correct?"})

    return {
        "tickets": entries,
        "questions": questions,
        "unmatched_projects": [{"project": p, "tickets": k} for p, k in sorted(unmatched.items())],
    }


# ---------------------------------------------------------------------------
# refresh: what changed in the tracker since the last import
# ---------------------------------------------------------------------------
COMPARED = ("title", "kind", "slices", "steps")


def refresh(ticket_map, tracker_tickets):
    """`tracker_tickets`: the new proposal (`propose()` output tickets), plus
    `state: cancelled` for tickets the tracker cancelled."""
    old = {t["key"]: t for t in ticket_map.get("tickets") or []}
    new = {t["key"]: t for t in tracker_tickets}
    changes = []
    for key, t in new.items():
        if key not in old:
            if t.get("state") != "cancelled":
                changes.append({"change": "new", "ticket": key, "proposal": {f: t.get(f) for f in COMPARED}})
            continue
        if t.get("state") == "cancelled":
            changes.append({"change": "removed", "ticket": key, "proposal": "close its ticket record as cancelled"})
            continue
        diff = {f: {"was": old[key].get(f), "now": t.get(f)} for f in COMPARED
                if t.get(f) is not None and t.get(f) != old[key].get(f)}
        if diff:
            changes.append({"change": "changed", "ticket": key, "fields": diff})
    for key in old:
        if key not in new:
            changes.append({"change": "removed", "ticket": key, "proposal": "close its ticket record as cancelled"})
    order = {"new": 0, "changed": 1, "removed": 2}
    changes.sort(key=lambda c: (order[c["change"]], c["ticket"]))
    return {"changes": changes}


# ---------------------------------------------------------------------------
# status: one row per slice, one cell per step
# ---------------------------------------------------------------------------
def _live_tickets(ticket_map, records):
    for t in ticket_map.get("tickets") or []:
        rec = records.get(t["key"], {})
        if rec.get("state") in ENDED_STATES:
            continue
        yield t, rec


def cells(ticket_map, records):
    """{slice: {artifact: {state, tickets}}}.

    A cell is complete when every live ticket covering it has merged and
    recorded a done result for the step. Blocked when any covering ticket is
    blocked. In progress when any covering ticket is open, awaiting review or
    awaiting its owner. Not started otherwise.
    """
    cover = {}
    for t, rec in _live_tickets(ticket_map, records):
        for sl in t.get("slices") or []:
            for st in t.get("steps") or []:
                cover.setdefault(sl, {}).setdefault(step_artifact(st), []).append((t["key"], st, rec))
    out = {}
    for sl, arts in cover.items():
        out[sl] = {}
        for art, covering in arts.items():
            def done(st, rec):
                return bool(rec.get("merged")) and str((rec.get("results") or {}).get(st, "")).lower() in DONE_RESULTS
            if all(done(st, rec) for _, st, rec in covering):
                state = "complete"
            elif any(rec.get("blocked") for _, _, rec in covering):
                state = "blocked"
            elif any(rec.get("state") in ACTIVE_STATES for _, _, rec in covering):
                state = "in_progress"
            else:
                state = "not_started"
            out[sl][art] = {"state": state, "tickets": sorted({k for k, _, _ in covering}, key=_key_order)}
    return out


def _key_order(key):
    m = re.match(r"^(.*?)(\d+)$", key)
    return (m.group(1), int(m.group(2))) if m else (key, 0)


def rollup(ticket_map, cell_map):
    """Each step's state for the release: complete when complete in every
    slice that has it."""
    out = {}
    for sl in cell_map:
        for art, cell in cell_map[sl].items():
            r = out.setdefault(art, {"slices": 0, "complete": 0})
            r["slices"] += 1
            r["complete"] += cell["state"] == "complete"
    for r in out.values():
        r["state"] = ("complete" if r["complete"] == r["slices"]
                      else "none" if r["complete"] == 0 else "partial")
    return out


def slice_order(ticket_map, cell_map):
    declared = [s["id"] for s in ticket_map.get("slices") or []]
    rest = sorted(s for s in cell_map if s not in declared)
    return [s for s in declared if s in cell_map] + rest


def status_markdown(ticket_map, cell_map, graph_order=None):
    arts = []
    for sl in cell_map:
        for a in cell_map[sl]:
            if a not in arts:
                arts.append(a)
    if graph_order:
        arts.sort(key=lambda a: graph_order.index(a) if a in graph_order else len(graph_order))
    lines = ["| Slice | " + " | ".join(arts) + " |", "|" + "---|" * (len(arts) + 1)]
    for sl in slice_order(ticket_map, cell_map):
        row = []
        for a in arts:
            c = cell_map[sl].get(a)
            row.append(f"{CELL_SYMBOL[c['state']]} {', '.join(c['tickets'])}" if c else "")
        lines.append(f"| {sl} | " + " | ".join(row) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# runnable: what can start, per slice
# ---------------------------------------------------------------------------
def runnable(ticket_map, records, graph, release_artifacts=None, rulings=None):
    """For each ticket: done | in_progress | blocked | can_start | waiting | parked.

    `graph`: {artifact: {depends_on, disabled}} from load_graph().
    `release_artifacts`: status.md `artifacts:` block, for steps the ticket map
    does not cover (a design document produced for the whole release).
    `rulings`: [(artifact, dependency)] advisory gates a director has ruled on.
    """
    release_artifacts = release_artifacts or {}
    rulings = {tuple(r) for r in (rulings or [])}
    cm = cells(ticket_map, records)
    roll = rollup(ticket_map, cm)
    slices = {s["id"]: s for s in ticket_map.get("slices") or []}
    owners = {}
    for t, _ in _live_tickets(ticket_map, records):
        for sl in t.get("slices") or []:
            for st in t.get("steps") or []:
                owners.setdefault((sl, step_artifact(st)), set()).add(t["key"])

    def upstream(sl):
        return list((slices.get(sl) or {}).get("depends_on") or [])

    def requirement(sl, dep, entry):
        """The cells (or release state) a dependency on `dep` for slice `sl`
        resolves to. Returns (met, waiting_tickets, reason)."""
        node = (graph or {}).get(dep)
        if node and node.get("disabled"):
            return True, set(), None
        if dep in cm.get(sl, {}):
            c = cm[sl][dep]
            return c["state"] == "complete", set(c["tickets"]), f"{sl}.{dep}"
        ups = [u for u in upstream(sl) if dep in cm.get(u, {})]
        if ups:
            pending = [u for u in ups if cm[u][dep]["state"] != "complete"]
            tickets = set().union(*(cm[u][dep]["tickets"] for u in ups))
            return not pending, tickets, ", ".join(f"{u}.{dep}" for u in ups)
        if dep in cm.get(WHOLE_RELEASE, {}):
            c = cm[WHOLE_RELEASE][dep]
            return c["state"] == "complete", set(c["tickets"]), f"{WHOLE_RELEASE}.{dep}"
        if dep in roll:
            # Other slices have this step and this one does not: the ticket
            # map, as confirmed, says the step does not apply to this slice.
            return True, set(), None
        action = entry.get("action", "generate")
        outcome = str(entry.get("outcome", "complete")).lower()
        actual = str((release_artifacts.get(dep) or {}).get(action, "not_started")).lower()
        return actual == outcome, set(), f"release {dep}.{action} required {outcome}, was {actual}"

    results, links = [], []
    for t, rec in _live_tickets(ticket_map, records):
        key = t["key"]
        own = {(sl, step_artifact(st)) for sl in t.get("slices") or [] for st in t.get("steps") or []}
        if not own:
            results.append({"ticket": key, "state": "plain"})
            continue
        if all(cm[sl][a]["state"] == "complete" for sl, a in own):
            results.append({"ticket": key, "state": "done"})
            continue
        structural, waits, reasons, parked = set(), set(), [], []
        for sl, art in sorted(own):
            entries = list(((graph or {}).get(art) or {}).get("depends_on") or [])
            # The same step in each upstream slice comes first.
            for u in upstream(sl) if art in BUILD_STEPS else []:
                if art in cm.get(u, {}):
                    entries.append({"artifact": art, "action": "generate", "outcome": "complete", "_upstream": u})
            for entry in entries:
                dep = entry["artifact"]
                if entry.get("_upstream"):
                    c = cm[entry["_upstream"]][art]
                    met, tickets, why = c["state"] == "complete", set(c["tickets"]), f"{entry['_upstream']}.{art}"
                else:
                    if (sl, dep) in own:
                        continue  # the ticket runs its own steps in order
                    met, tickets, why = requirement(sl, dep, entry)
                tickets.discard(key)
                structural |= tickets
                if met:
                    continue
                if entry.get("enforcement") == "advisory":
                    if (art, dep) not in rulings:
                        parked.append(f"proceed without {dep}?")
                    continue
                waits |= tickets
                reasons.append(why)
        if rec.get("blocked"):
            state = "blocked"
        elif rec.get("state") in ACTIVE_STATES:
            state = "in_progress"
        elif reasons:
            state = "waiting"
        elif parked:
            state = "parked"
        else:
            state = "can_start"
        item = {"ticket": key, "state": state}
        if rec.get("blocked"):
            item["reason"] = rec["blocked"]
        if waits or reasons:
            item["waits_on"] = sorted(waits, key=_key_order)
            item["unmet"] = sorted(set(reasons))
        if parked:
            item["needs_ruling"] = sorted(set(parked))
        results.append(item)

        tracker = set(t.get("blocked_by") or [])
        open_structural = {k for k in structural
                           if not all(cm[sl][a]["state"] == "complete"
                                      for (sl, a), keys in owners.items() if k in keys)}
        missing = sorted(open_structural - tracker, key=_key_order)
        extra = sorted(tracker - structural, key=_key_order)
        if missing or extra:
            links.append({"ticket": key, "missing_in_tracker": missing, "not_in_wire_order": extra})
    return {"tickets": results, "link_check": links}


# ---------------------------------------------------------------------------
# merge-log: a merged ticket's run log rows, added to the release log
# ---------------------------------------------------------------------------
TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def _rows(text):
    out = []
    for line in (text or "").splitlines():
        t = line.strip()
        if not (t.startswith("|") and t.endswith("|")):
            continue
        cells_ = [c.strip() for c in t[1:-1].split("|")]
        if not cells_ or not TS.match(cells_[0]):
            continue
        out.append(cells_)
    return out


def merge_log(release_log, ticket_log, ticket, now):
    """Rows to append to the release execution_log.md.

    Each row keeps its command, result, by, session and metric cells. Its
    Timestamp is the time of the roll-up (never earlier than the release log's
    last row), and its Detail starts `ticket <key>, ran <original time>:`,
    because execution_log.md is append-only and its timestamps must not go
    backwards (specs/utils/execution_log.md rules 1 and 6). Rows are added in
    the order the ticket ran them. A row already rolled up is not added again.
    """
    existing = _rows(release_log)
    last = existing[-1][0] if existing else None
    stamp = max(now, last) if last else now
    seen = set()
    for r in existing:
        m = re.match(rf"^ticket {re.escape(ticket)}, ran (\S+ \S+): ", r[3] if len(r) > 3 else "")
        if m:
            seen.add((m.group(1), r[1], r[2]))
    ticket_rows = sorted(enumerate(_rows(ticket_log)), key=lambda p: (p[1][0], p[0]))
    out = []
    for _, r in ticket_rows:
        if (r[0], r[1], r[2]) in seen:
            continue
        seen.add((r[0], r[1], r[2]))
        detail = f"ticket {ticket}, ran {r[0]}: {r[3] if len(r) > 3 else ''}".replace("|", "—")
        if len(detail) > 120:
            detail = detail[:119] + "…"
        cells_ = [stamp, r[1], r[2], detail] + r[4:]
        while len(cells_) < 9:
            cells_.append("n/a" if len(cells_) >= 6 else "unknown")
        out.append("| " + " | ".join(cells_) + " |")
    return out


# ---------------------------------------------------------------------------
# design-source: where a slice's table design comes from
# ---------------------------------------------------------------------------
def design_source(model_source, physical_tables, slice_table=None):
    """Returns one of:
        wire_data_model             Wire's data_model document, as now
        modality_physical           the Modality physical model; data_model-generate
                                    records it and lists gaps against Wire's rules
        wire_data_model_from_modality
                                    Wire's data_model document, designed from the
                                    Modality conceptual and logical layers
    """
    if model_source != "modality":
        return "wire_data_model"
    tables = {t.lower() for t in physical_tables or []}
    if not tables:
        return "wire_data_model_from_modality"
    if slice_table is not None and slice_table.split(".")[-1].lower() not in tables:
        return "wire_data_model_from_modality"
    return "modality_physical"


PHYSICAL_TABLE = re.compile(r'^\s*(?:table|physical_table)\s+"([^"]+)"', re.M)


def physical_tables(release_dir, status):
    root = status.get("modality_path")
    if not root:
        return []
    base = Path(root)
    if not base.is_absolute():
        base = (Path(release_dir) / root).resolve()
        if not base.exists():
            base = Path(root).resolve()
    folder = base / "models" / "physical"
    if not folder.is_dir():
        folder = base / "modality" / "models" / "physical"
    tables = []
    for path in sorted(folder.glob("*.mml")) if folder.is_dir() else []:
        tables += PHYSICAL_TABLE.findall(path.read_text())
    return tables


# ---------------------------------------------------------------------------
# scope: /wire:work in a ticket-built release
# ---------------------------------------------------------------------------
# specs/work.md "When to use it, and when not", in table order.
TRIGGERS = ["new_source", "new_concept", "grain_change_with_dependants",
            "security_or_residency", "production_cutover", "spans_deliverables", "unbounded"]
# Triggers the ticket map can answer: the new object is planned when it is a
# slice of this ticket.
PLANNABLE = {"new_source", "new_concept"}


def scope(ticket_map, request):
    """`request`: {ticket, adds: [{object, trigger}], triggers: [other triggers]}.

    Ticket in the map: each added source or table is accepted when it is one
    of this ticket's slices, refused otherwise. Other triggers apply as in
    /wire:work. Ticket not in the map: the ordinary /wire:work boundary check.
    """
    tickets = {t["key"]: t for t in ticket_map.get("tickets") or []}
    t = tickets.get(request.get("ticket"))
    adds = request.get("adds") or []
    other = [x for x in TRIGGERS if x in (request.get("triggers") or [])]
    if t is None:
        triggers = [x for x in TRIGGERS if x in other or any(a["trigger"] == x for a in adds)]
        return {"in_map": False, "outcome": "escalate" if triggers else "iteration", "triggers": triggers}
    mine = set(t.get("slices") or [])
    accepted, refused = [], []
    for a in adds:
        if a["trigger"] in PLANNABLE and a["object"] in mine:
            accepted.append(a["object"])
        else:
            refused.append({"object": a["object"], "trigger": a["trigger"]})
    # partial: the ticket starts without the refused objects, if the
    # consultant agrees; each refused object is offered a ticket of its own.
    outcome = "escalate" if other else "partial" if refused else "planned"
    return {"in_map": True, "outcome": outcome, "accepted": accepted, "refused": refused, "triggers": other}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _now():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def main(argv=None):
    p = argparse.ArgumentParser(description="Fixed rules of a release built from tickets (wire#279).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("release"); s.add_argument("--markdown", action="store_true")
    s = sub.add_parser("runnable"); s.add_argument("release"); s.add_argument("--graph")
    s = sub.add_parser("merge-log"); s.add_argument("release"); s.add_argument("ticket")
    s.add_argument("--now"); s.add_argument("--write", action="store_true")
    s = sub.add_parser("refresh"); s.add_argument("release"); s.add_argument("tracker")
    s = sub.add_parser("propose"); s.add_argument("classified")
    s = sub.add_parser("design-source"); s.add_argument("release"); s.add_argument("--slice")
    s = sub.add_parser("scope"); s.add_argument("release"); s.add_argument("request")
    a = p.parse_args(argv)

    if a.cmd == "propose":
        print(json.dumps(propose(json.loads(Path(a.classified).read_text())), indent=2))
        return 0
    rel = Path(a.release)
    if not (rel / "status.md").exists() and (Path(".wire/releases") / a.release / "status.md").exists():
        rel = Path(".wire/releases") / a.release
    status = load_status(rel)

    if a.cmd == "design-source":
        print(json.dumps({"design_source": design_source(
            status.get("model_source"), physical_tables(rel, status), a.slice)}, indent=2))
        return 0
    tmap = load_map(rel)
    records = load_records(rel)
    if a.cmd == "status":
        cm = cells(tmap, records)
        if a.markdown:
            graph = load_graph(status)
            print(status_markdown(tmap, cm, list(graph) if graph else None))
        else:
            print(json.dumps({"cells": cm, "release": rollup(tmap, cm)}, indent=2, ensure_ascii=False))
    elif a.cmd == "runnable":
        graph = load_graph(status, a.graph)
        print(json.dumps(runnable(tmap, records, graph, status.get("artifacts") or {}), indent=2))
    elif a.cmd == "merge-log":
        log = rel / "execution_log.md"
        tlog = rel / "iterations" / f"{a.ticket}.execution_log.md"
        rows = merge_log(log.read_text() if log.exists() else "",
                         tlog.read_text() if tlog.exists() else "", a.ticket, a.now or _now())
        if a.write and rows:
            text = log.read_text() if log.exists() else (
                "# Execution Log\n\n| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |\n"
                "|-----------|---------|--------|--------|----|---------|----------|--------|------------|\n")
            log.write_text(text.rstrip("\n") + "\n" + "\n".join(rows) + "\n")
        print(json.dumps({"rows": rows, "written": bool(a.write and rows)}, indent=2, ensure_ascii=False))
    elif a.cmd == "refresh":
        print(json.dumps(refresh(tmap, json.loads(Path(a.tracker).read_text())), indent=2))
    elif a.cmd == "scope":
        print(json.dumps(scope(tmap, json.loads(Path(a.request).read_text())), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

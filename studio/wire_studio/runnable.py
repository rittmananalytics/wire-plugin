"""The runnable set: specs/utils/runnable_set.md Steps 1 to 5.

This is the same rule `/wire:start`, `/wire:delegate`, the release-director
skill and Autopilot read. `wire/tests/studio/validate_studio.py` runs every
case in `wire/tests/core/fixture/runnable_set/cases.json` through this module
and compares the result with `wire/tests/core/expected/runnable_set.json`, the
expected output the core test already holds, so Studio cannot show a
different answer from the one the commands act on.
"""

import re

DONE = {"generate": "complete", "validate": "pass", "review": "approved"}

RULING_HEADER = re.compile(r"^##\s*(R-\d+)\s*\|")
RULING_APPLIES = re.compile(
    r"^Applies to:\s*(\S+)\.depends_on\.(\S+)\s*\((advisory|decision)\)", re.M)
RULING_VERDICT = re.compile(r"^Ruling:\s*(\w+)", re.M)
PROCEED_VERDICTS = {"skip", "proceed", "waive"}


def parse_gate_rulings(decisions_md):
    """Rulings that name an artifact's dependency, in the structured form the
    gate reads. Blocks without the header, the Applies line and a verdict are
    skipped: guessing at a ruling's intent is what the structured form
    prevents."""
    rulings = []
    for block in re.split(r"(?m)^(?=## R-\d)", decisions_md or ""):
        h = RULING_HEADER.search(block)
        a = RULING_APPLIES.search(block)
        v = RULING_VERDICT.search(block)
        if not (h and a and v):
            continue
        rulings.append({"id": h.group(1), "artifact": a.group(1),
                        "dependency": a.group(2), "kind": a.group(3),
                        "verdict": v.group(1).lower()})
    return rulings


def _matching_ruling(rulings, artifact, dependency):
    for r in rulings:
        if (r["artifact"] == artifact and r["dependency"] == dependency
                and r["kind"] == "advisory" and r["verdict"] in PROCEED_VERDICTS):
            return r["id"]
    return None


def _resolve_profile(spec, status):
    field = spec.get("profile_field")
    if not field:
        return None
    profiles = {p["id"]: p for p in spec.get("profiles", [])}
    value = status.get(field) or spec.get("default_profile")
    if value not in profiles:
        raise ValueError(f"profile {value!r} is not declared by {spec['id']}; "
                         f"valid ids: {sorted(profiles)}")
    return profiles[value]


def flatten(spec, profile):
    disabled = set(profile.get("disable_phases", []) if profile else [])
    enabled = set(profile.get("enable_phases", []) if profile else [])
    overrides = {}
    for po in (profile.get("phase_overrides", []) if profile else []):
        for art in po.get("artifacts", []):
            overrides[art["id"]] = art.get("depends_on", [])
    artifacts, not_applicable = [], []
    for phase_index, phase in enumerate(spec.get("phases", [])):
        for art in phase.get("artifacts", []):
            entry = {
                "id": art["id"],
                "command": art.get("command", art["id"]),
                "phase": phase["id"],
                "phase_name": phase.get("name", phase["id"]),
                "phase_index": phase_index,
                "sequence": art.get("sequence", 0),
                "required": art.get("required", True),
                "depends_on": overrides.get(art["id"], art.get("depends_on", [])),
            }
            if phase["id"] in disabled:
                not_applicable.append(entry)
                continue
            if not entry["required"] and phase["id"] not in enabled:
                entry["optional_unrequested"] = True
            artifacts.append(entry)
    return artifacts, not_applicable


def _outcome_met(recorded, required):
    if recorded is None:
        return False
    if required == "PASS":
        return str(recorded).lower() == "pass"
    return recorded == required


def resolve(framework, status, decisions_md="", requested=()):
    """Returns states per artifact, the ordered runnable list, the parallel set
    within budget.lanes_max, the rulings applied, and the graph Studio draws."""
    release_type = status.get("project_type") or status.get("release_type")
    if not release_type:
        raise ValueError("status.md carries neither project_type nor release_type")
    spec = framework.release_type(release_type)
    profile = _resolve_profile(spec, status)
    artifacts, disabled_artifacts = flatten(spec, profile)
    rulings = parse_gate_rulings(decisions_md)
    art_status = status.get("artifacts", {}) or {}
    lanes_max = (status.get("budget") or {}).get("lanes_max", 4)

    states = {a["id"]: "not applicable" for a in disabled_artifacts}
    disabled_by_profile = set(states)

    for a in artifacts:
        if a.get("optional_unrequested") and a["id"] not in requested:
            states[a["id"]] = "not applicable"
            continue
        recorded = art_status.get(a["id"], {}) or {}
        if not framework.known_command(a["command"]):
            raise ValueError(
                f"artifact {a['id']!r} declares command {a['command']!r}, which "
                f"has no registered generate/validate/review command")
        steps = [s for s in ("generate", "validate", "review")
                 if framework.has_step(a["command"], s)
                 and recorded.get(s) != "not_applicable"]
        if steps and all(_outcome_met(recorded.get(s), DONE[s]) for s in steps):
            states[a["id"]] = "complete"

    ruling_used = {}
    for a in artifacts:
        if a["id"] in states:
            continue
        blocking_unmet, advisory_unmet = [], []
        for dep in a["depends_on"]:
            dep_id, dep_action = dep["artifact"], dep["action"]
            if dep_id in disabled_by_profile:
                continue
            recorded = (art_status.get(dep_id, {}) or {}).get(dep_action)
            if _outcome_met(recorded, dep["outcome"]):
                continue
            entry = (dep_id, dep_action, dep["outcome"], recorded or "not_started")
            (advisory_unmet if dep.get("enforcement") == "advisory"
             else blocking_unmet).append(entry)
        if blocking_unmet:
            f = blocking_unmet[0]
            states[a["id"]] = f"blocked: {f[0]}.{f[1]} required {f[2]}, was {f[3]}"
            continue
        unruled = []
        for dep_id, _, _, _ in advisory_unmet:
            rid = _matching_ruling(rulings, a["id"], dep_id)
            if rid:
                ruling_used.setdefault(a["id"], []).append(rid)
            else:
                unruled.append(dep_id)
        if unruled:
            states[a["id"]] = f"parked: needs ruling (proceed without {unruled[0]}?)"

    for a in artifacts:
        if a["id"] in states:
            continue
        recorded = art_status.get(a["id"], {}) or {}
        cmd = a["command"]
        if recorded.get("generate") != "complete":
            states[a["id"]] = "runnable: generate"
            continue
        if framework.has_step(cmd, "validate") and recorded.get("validate") != "not_applicable":
            if str(recorded.get("validate", "")).lower() != "pass":
                no_av = framework.no_auto_validate
                states[a["id"]] = ("runnable: validate"
                                   if cmd in no_av or a["id"] in no_av
                                   else "runnable: generate")
                continue
        if framework.has_step(cmd, "review") and recorded.get("review") != "not_applicable":
            if recorded.get("review") != "approved":
                states[a["id"]] = "parked: needs ruling (review)"
                continue
        states[a["id"]] = "complete"

    runnable = [a for a in artifacts if states[a["id"]].startswith("runnable")]
    runnable.sort(key=lambda a: (a["phase_index"], a["sequence"], a["id"]))
    deps = {a["id"]: {d["artifact"] for d in a["depends_on"]} for a in artifacts}
    parallel = []
    for a in runnable:
        if len(parallel) >= lanes_max:
            break
        if all(b["id"] not in deps[a["id"]] and a["id"] not in deps[b["id"]]
               for b in parallel):
            parallel.append(a)

    graph = []
    for a in sorted(artifacts + disabled_artifacts,
                    key=lambda x: (x["phase_index"], x["sequence"], x["id"])):
        recorded = art_status.get(a["id"], {}) or {}
        graph.append({
            "id": a["id"], "command": a["command"].replace("/", "-"),
            "phase": a["phase"], "phase_name": a["phase_name"],
            "required": a["required"], "state": states[a["id"]],
            "steps": {s: recorded.get(s, "not_started")
                      for s in ("generate", "validate", "review")
                      if framework.has_step(a["command"], s)},
            "file": recorded.get("file"),
            "depends_on": [d["artifact"] for d in a["depends_on"]],
        })

    return {
        "states": states,
        "order": [a["id"] for a in runnable],
        "parallel": [a["id"] for a in parallel],
        "rulings_applied": {k: sorted(v) for k, v in ruling_used.items()},
        "graph": graph,
        "lanes_max": lanes_max,
        "profile": profile["id"] if profile else None,
    }

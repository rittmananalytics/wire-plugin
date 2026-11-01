#!/usr/bin/env python3
"""wire_gate.py: the precondition state of one command, and a release's next
action, for the Wire mod (wire#270, releases 3 and 4).

A plain script, no AI call. It answers two questions the Claude Code mod
(hooks/register.ts) asks before it acts, from the same resolver Wire Studio
and `/wire:start` read (`studio/wire_studio/runnable.py`, the executable form
of `specs/utils/runnable_set.md`), so the mod can never disagree with them:

    gate  --repo <repo> --release <release> --command <slug>
          The state of the artifact the command belongs to. `decision` is
          `refuse` only when a blocking precondition is unmet
          (`specs/utils/precondition_gate.md` Step 2); an advisory gate, a
          command the graph does not know, a release the resolver cannot read,
          or any error is `allow`, with the reason. The mod refuses nothing it
          cannot prove.

    next  --repo <repo> --release <release>
          The first command the release can run, in graph order, as it would be
          typed (`/wire:<command>-<action> <release>`), or the review that
          waits, or null with the blocker named.

Both print one JSON object. Exit 0 whatever the answer; exit 2 only on a usage
error. The framework root (release-types/, specs/, studio/) is the folder
above this script in both layouts: `wire/` in a checkout, the plugin root in a
built plugin. `--framework` overrides it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_FRAMEWORK = HERE.parent

ACTIONS = ("generate", "validate", "review")


def _load(framework_root):
    root = Path(framework_root).resolve()
    sys.path.insert(0, str(root / "studio"))
    from wire_studio.framework import Framework  # noqa: E402
    from wire_studio.record import read_rulings, split_front_matter  # noqa: E402
    from wire_studio.runnable import resolve  # noqa: E402
    return Framework(root), split_front_matter, read_rulings, resolve


def _status_and_decisions(repo, release, split_front_matter, read_rulings):
    rel_dir = Path(repo) / ".wire" / "releases" / release
    status_path = rel_dir / "status.md"
    if not status_path.is_file():
        raise FileNotFoundError(f"no status.md for release {release!r}")
    status, _body = split_front_matter(status_path.read_text(encoding="utf-8", errors="replace"))
    if status.get("_error"):
        raise ValueError(status["_error"])
    _rulings, decisions_md = read_rulings(rel_dir)
    return status, decisions_md


def _resolved(framework, repo, release, split_front_matter, read_rulings, resolve):
    status, decisions_md = _status_and_decisions(repo, release, split_front_matter, read_rulings)
    return resolve(framework, status, decisions_md)


def _slug(command):
    return command.replace("/", "-")


def artifact_for(resolved, slug):
    """The graph artifact a command slug belongs to, and the action: an exact
    `<command>-<action>` match first, then the artifact whose command the slug
    starts with (`dbt-migration-defer-build` is `dbt_migration`'s). None when
    the slug names no artifact in this release's graph."""
    graph = {g["id"]: g for g in resolved["graph"]}
    for art, g in graph.items():
        base = _slug(g["command"])
        for action in ACTIONS:
            if slug == f"{base}-{action}":
                return art, action
    # A utility command named after its artifact (`dbt-migration-defer-build`
    # is `dbt_migration`'s). The artifact's command must cover at least the
    # slug's first two segments, so `dbt` never claims `dbt-migration-*`.
    parts = slug.split("-")
    floor = "-".join(parts[:2]) if len(parts) > 2 else slug
    longest = None
    for art, g in graph.items():
        base = _slug(g["command"])
        if slug.startswith(base + "-") and len(base) >= len(floor) and (
                longest is None or len(base) > len(_slug(graph[longest]["command"]))):
            longest = art
    if longest is not None:
        return longest, slug[len(_slug(graph[longest]["command"])) + 1:]
    return None, None


def gate(framework, repo, release, command, split_front_matter, read_rulings, resolve):
    slug = _slug(command.replace("/wire:", "").replace("wire:", ""))
    out = {"command": slug, "release": release, "artifact": None, "action": None,
           "state": None, "decision": "allow", "reason": ""}
    try:
        resolved = _resolved(framework, repo, release, split_front_matter, read_rulings, resolve)
    except Exception as e:  # noqa: BLE001 - the mod must never refuse on a reading error
        out["reason"] = f"could not resolve the release: {e}"
        return out
    art, action = artifact_for(resolved, slug)
    if art is None:
        out["reason"] = "the command belongs to no artifact in this release's graph"
        return out
    state = resolved["states"].get(art, "")
    out.update({"artifact": art, "action": action, "state": state})
    if state.startswith("blocked: "):
        out["decision"] = "refuse"
        out["reason"] = state[len("blocked: "):]
    elif state.startswith("parked: needs ruling (proceed without"):
        out["reason"] = "advisory gate: the command asks for a reason, the mod does not refuse"
    elif state == "not applicable":
        out["reason"] = "the artifact is not applicable under the active profile"
    else:
        out["reason"] = "no blocking precondition is unmet"
    return out


def next_action(framework, repo, release, split_front_matter, read_rulings, resolve):
    out = {"release": release, "next": None, "kind": None, "reason": ""}
    try:
        resolved = _resolved(framework, repo, release, split_front_matter, read_rulings, resolve)
    except Exception as e:  # noqa: BLE001
        out["reason"] = f"could not resolve the release: {e}"
        return out
    graph = {g["id"]: g for g in resolved["graph"]}
    states = resolved["states"]
    # The runnable set's own order first (specs/utils/runnable_set.md Step 5):
    # the first thing that can run is the next action.
    for art in resolved["order"]:
        action = states[art].split(": ", 1)[1]
        out.update({"next": f"/wire:{_slug(graph[art]['command'])}-{action} {release}",
                    "kind": "runnable", "reason": f"{art} is runnable"})
        return out
    # Nothing runnable: the first review that waits, then the first gate.
    for g in resolved["graph"]:
        if states.get(g["id"]) == "parked: needs ruling (review)":
            out.update({"next": f"/wire:{_slug(g['command'])}-review {release}", "kind": "review",
                        "reason": f"{g['id']} waits for its review"})
            return out
    for g in resolved["graph"]:
        state = states.get(g["id"], "")
        if state.startswith("blocked: ") or state.startswith("parked: "):
            out.update({"kind": "blocked", "reason": f"{g['id']}: {state}"})
            return out
    out.update({"kind": "complete", "reason": "every applicable artifact is complete"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gate", "next"):
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True)
        p.add_argument("--release", required=True)
        p.add_argument("--framework", default=str(DEFAULT_FRAMEWORK))
        if name == "gate":
            p.add_argument("--command", required=True, help="command slug, e.g. deployment-generate")
    args = ap.parse_args(argv)
    try:
        framework, split_front_matter, read_rulings, resolve = _load(args.framework)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"decision": "allow", "next": None, "reason": f"framework not readable: {e}"}))
        return 0
    if args.cmd == "gate":
        out = gate(framework, args.repo, args.release, args.command, split_front_matter, read_rulings, resolve)
    else:
        out = next_action(framework, args.repo, args.release, split_front_matter, read_rulings, resolve)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

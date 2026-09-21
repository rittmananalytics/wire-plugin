#!/usr/bin/env python3
"""
Evidence fingerprints and invalidation for bi_migration (wire#258).

A parity verdict is valid only for the exact things it was measured against. This
module composes that fingerprint and decides, when something changes, which kinds
of evidence the change invalidates. /wire:bi-migration-plan-generate stamps the
fingerprint on register rows; /wire:migration-drift-generate (bi_migration mode)
recomputes it and marks stale evidence; /wire:bi-equivalency-validate writes it on
every verdict. Deterministic, no AI call.

Fingerprint components (all strings; a missing component is the literal "absent"):
    source_definition    the LookML commit plus the SHA-256 of the object's .lkml file(s)
    target_definition    the SHA-256 of the emitted Omni file(s) as written to the branch
    dependencies         the SHA-256 of the object's transitive dependency closure (dependencies.jsonl slice)
    policy_context       the SHA-256 of the access filters, grants and user attributes in scope
    data_context         parity_as_of plus the warehouse consistency window
    test_contract        the SHA-256 of the tile's test contract YAML
    adapters             converter version, pair ruleset hash, comparator version, CLI versions

Evidence kinds:
    numeric_parity, access_parity, presentation_fidelity, interaction_fidelity

Invalidation rules (which component changed -> which evidence is stale):
    source_definition, dependencies, data_context, test_contract, adapters
        -> numeric_parity and interaction_fidelity
    target_definition, kind semantic (sql, aggregate_type, filters, joins, timeframes)
        -> numeric_parity, interaction_fidelity and presentation_fidelity
    target_definition, kind presentation_only (labels, formats, colours, layout)
        -> presentation_fidelity only; a presentation-only change never forces a warehouse re-run
    policy_context
        -> access_parity (and numeric_parity when the object carries an access filter that shapes rows)

Usage:
    python3 wire/scripts/bi_evidence.py fingerprint --components components.json
    python3 wire/scripts/bi_evidence.py invalidate --old old.json --new new.json
        [--target-change-kind semantic|presentation_only] [--row-filtering-policy]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

COMPONENTS = ("source_definition", "target_definition", "dependencies", "policy_context", "data_context", "test_contract", "adapters")
EVIDENCE_KINDS = ("numeric_parity", "access_parity", "presentation_fidelity", "interaction_fidelity")
VERSION = "1"


def fingerprint(components: dict) -> str:
    """SHA-256 over the canonical JSON of the seven components; missing ones are 'absent'."""
    canon = OrderedDict((c, str(components.get(c, "absent"))) for c in COMPONENTS)
    canon["version"] = VERSION
    return hashlib.sha256(json.dumps(canon, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def changed_components(old: dict, new: dict) -> list[str]:
    return [c for c in COMPONENTS if str(old.get(c, "absent")) != str(new.get(c, "absent"))]


def invalidated(changed: list[str], target_change_kind: str | None = None, row_filtering_policy: bool = False) -> OrderedDict:
    """Map changed components to the evidence kinds they invalidate, with the rule that fired."""
    stale: "OrderedDict[str, list[str]]" = OrderedDict((k, []) for k in EVIDENCE_KINDS)

    def hit(kind: str, rule: str) -> None:
        if rule not in stale[kind]:
            stale[kind].append(rule)

    for c in changed:
        if c in {"source_definition", "dependencies", "data_context", "test_contract", "adapters"}:
            hit("numeric_parity", c)
            hit("interaction_fidelity", c)
        elif c == "target_definition":
            kind = target_change_kind or "semantic"
            if kind == "presentation_only":
                hit("presentation_fidelity", "target_definition:presentation_only")
            else:
                hit("numeric_parity", "target_definition:semantic")
                hit("interaction_fidelity", "target_definition:semantic")
                hit("presentation_fidelity", "target_definition:semantic")
        elif c == "policy_context":
            hit("access_parity", "policy_context")
            if row_filtering_policy:
                hit("numeric_parity", "policy_context:row_filtering")
    return OrderedDict((k, v) for k, v in stale.items() if v)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fingerprint")
    f.add_argument("--components", required=True, type=Path)
    i = sub.add_parser("invalidate")
    i.add_argument("--old", required=True, type=Path)
    i.add_argument("--new", required=True, type=Path)
    i.add_argument("--target-change-kind", choices=["semantic", "presentation_only"], default=None)
    i.add_argument("--row-filtering-policy", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "fingerprint":
        print(fingerprint(json.loads(args.components.read_text())))
        return 0
    old, new = json.loads(args.old.read_text()), json.loads(args.new.read_text())
    ch = changed_components(old, new)
    out = OrderedDict([
        ("old_fingerprint", fingerprint(old)),
        ("new_fingerprint", fingerprint(new)),
        ("changed_components", ch),
        ("invalidated", invalidated(ch, args.target_change_kind, args.row_filtering_policy)),
    ])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

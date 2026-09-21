#!/usr/bin/env python3
"""
Tile-level parity comparator for bi_migration (wire#258): the deterministic core
of /wire:bi-equivalency-validate.

Two result sets in (the Looker tile's rows and the Omni tile's rows, both already
executed under the same pinned as-of, filters, limit and timezone), one test
contract in, one verdict out. No AI call. The same inputs always give the same
verdict, so the comparison can be reasoned about, tested with fixtures and
re-run by a lane.

Usage:
    python3 wire/scripts/bi_parity.py --contract <tile>.yaml --source looker.csv --target omni.csv
        [--source-status ok|error|truncated] [--target-status ok|error|truncated]
        [--accepted decisions_accepted.yaml] [--out verdict.json]

Test contract (YAML; the control plane's own format, not a vendor payload):

    test_id: revenue_by_region
    source_object: "looker:acme:dashboard:101/element:301"
    target_object: "omni:acme:document:abc123/tile:1"
    baseline: "run-017"
    execution:
      principal: finance_uk          # the user context both sides ran under
      timezone: Europe/London
      data_snapshot: "2026-08-31T23:59:59Z"   # parity_as_of
      limit: 5000                    # the explicit row limit set on BOTH sides
      cache_policy: bypass
    comparison:
      row_semantics: multiset        # multiset (duplicates count) | ordered
      key_fields: [region]           # target-side names
      field_map: {orders.region: orders.region}   # source name -> target name (optional)
      measures:
        revenue: {comparator: exact_decimal, precision: 2}
        order_count: {comparator: exact_integer}
        conversion_rate: {comparator: floating_tolerance, absolute_tolerance: 0.000001, relative_tolerance: 0.000001}
      dates:
        fields: [created_at[date]]   # key fields that are dates; one-bucket shifts may be timezone_conversion
        bucket: day                  # day | month
        timezone_conversion_recorded: false   # true only when the model batch recorded the convert_tz decision
      expected_rows: nonzero         # nonzero | any; two empty sides with nonzero expected is INCONCLUSIVE
      tile_sorted: false             # an unsorted tile with the same multiset in a different order is sort_only

Outcomes and the verdict they map to:
    PASS                 -> pass
    PASS with mechanism  -> pass_qualified (rounding | timezone_conversion | sort_only)
    ACCEPTED_DIFFERENCE  -> pass_declared_deviation (needs an accepted-differences entry with approver and reason)
    FAIL                 -> fail
    BLOCKED              -> no verdict (the source query failed; a source failure is never a target success)
    INCONCLUSIVE         -> no verdict (truncated by the limit, or both sides empty when rows were expected)
    NOT_RUN              -> no verdict
Only pass, pass_qualified and pass_declared_deviation satisfy the cutover gate.

Comparison semantics (type-aware, never set-based):
    - Rows are compared as a multiset keyed by key_fields; duplicate multiplicity is preserved.
    - exact_integer and exact_decimal are exact (decimal at the declared precision).
    - floating_tolerance passes within absolute OR relative tolerance and records `rounding`.
    - Nulls are distinct from zero, empty string and missing rows.
    - A result at the row limit cannot establish equivalence: INCONCLUSIVE.
    - Ordered semantics compare the sequence; multiset semantics compare the bag and note order.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import yaml

PASSING_VERDICTS = {"pass", "pass_qualified", "pass_declared_deviation"}
NULL_TOKENS = {"", "null", "NULL", "None", "\\N"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("rows", [])
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def apply_field_map(rows: list[dict], field_map: dict) -> list[dict]:
    if not field_map:
        return rows
    out = []
    for r in rows:
        out.append({field_map.get(k, k): v for k, v in r.items()})
    return out


def norm_null(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s in NULL_TOKENS else s


# ---------------------------------------------------------------------------
# Typed comparison
# ---------------------------------------------------------------------------

def to_decimal(v) -> Decimal | None:
    s = norm_null(v)
    if s is None:
        return None
    try:
        return Decimal(s.replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"not numeric: {v!r}")


def compare_measure(name: str, spec: dict, a, b) -> tuple[bool, str | None, str | None]:
    """Return (equal, mechanism, detail)."""
    da, db = to_decimal(a), to_decimal(b)
    if da is None or db is None:
        if da is None and db is None:
            return True, None, None
        return False, None, f"{name}: null on one side ({a!r} vs {b!r})"
    comparator = spec.get("comparator", "exact_decimal")
    if comparator == "exact_integer":
        if da != da.to_integral_value() or db != db.to_integral_value():
            return False, None, f"{name}: non-integer value ({a!r} vs {b!r})"
        return (da == db), None, (None if da == db else f"{name}: {a} vs {b}")
    if comparator == "exact_decimal":
        q = Decimal(1).scaleb(-int(spec.get("precision", 2)))
        qa, qb = da.quantize(q, rounding=ROUND_HALF_UP), db.quantize(q, rounding=ROUND_HALF_UP)
        return (qa == qb), None, (None if qa == qb else f"{name}: {qa} vs {qb} at precision {spec.get('precision', 2)}")
    if comparator == "floating_tolerance":
        if da == db:
            return True, None, None
        abs_tol = Decimal(str(spec.get("absolute_tolerance", 0)))
        rel_tol = Decimal(str(spec.get("relative_tolerance", 0)))
        diff = abs(da - db)
        base = max(abs(da), abs(db))
        within = diff <= abs_tol or (base != 0 and diff / base <= rel_tol)
        if within:
            return True, "rounding", f"{name}: {a} vs {b} within tolerance (abs {abs_tol}, rel {rel_tol})"
        return False, None, f"{name}: {a} vs {b} outside tolerance (abs {abs_tol}, rel {rel_tol})"
    raise ValueError(f"unknown comparator {comparator!r} for {name}")


def key_of(row: dict, key_fields: list[str]) -> tuple:
    return tuple(norm_null(row.get(k)) for k in key_fields)


def _shift_dates(rows: list[dict], date_fields: set[str], bucket: str, shift: int) -> list[dict]:
    """Copy of rows with every date key moved by `shift` buckets (day or month). Non-dates are left alone."""
    out = []
    for r in rows:
        r2 = dict(r)
        for f in date_fields:
            s = norm_null(r.get(f))
            if s is None:
                continue
            try:
                d = dt.date.fromisoformat(s[:10] if len(s) >= 10 else s[:7] + "-01")
            except ValueError:
                continue
            if bucket == "month":
                m = d.month - 1 + shift
                d2 = d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)
                r2[f] = d2.isoformat()[:7] if len(s) == 7 else d2.isoformat()
            else:
                r2[f] = (d + dt.timedelta(days=shift)).isoformat()
        out.append(r2)
    return out


def _core_compare(source: list[dict], target: list[dict], key_fields: list[str], measures: dict) -> dict:
    """Keyed multiset difference plus typed measure comparison on keys present on both sides."""
    src_keys = Counter(key_of(r, key_fields) for r in source)
    tgt_keys = Counter(key_of(r, key_fields) for r in target)
    missing, extra = src_keys - tgt_keys, tgt_keys - src_keys
    mismatches: list = []
    mechanisms: list[str] = []
    if measures:
        by_src: dict = {}
        by_tgt: dict = {}
        for r in source:
            by_src.setdefault(key_of(r, key_fields), []).append(r)
        for r in target:
            by_tgt.setdefault(key_of(r, key_fields), []).append(r)
        sort_key = lambda r: [norm_null(r.get(m)) or "" for m in sorted(measures)]  # noqa: E731
        for k in sorted(set(by_src) & set(by_tgt), key=lambda kk: [str(x) for x in kk]):
            srows, trows = by_src[k], by_tgt[k]
            if len(srows) != len(trows):
                continue
            for sr, tr in zip(sorted(srows, key=sort_key), sorted(trows, key=sort_key)):
                for m, spec in sorted(measures.items()):
                    try:
                        eq, mech, detail = compare_measure(m, spec, sr.get(m), tr.get(m))
                    except ValueError as exc:
                        eq, mech, detail = False, None, str(exc)
                    if not eq:
                        mismatches.append(OrderedDict([("key", list(k)), ("measure", m), ("source", norm_null(sr.get(m))), ("target", norm_null(tr.get(m))), ("detail", detail)]))
                    elif mech and mech not in mechanisms:
                        mechanisms.append(mech)
    failed = bool(missing or extra or mismatches) or len(source) != len(target)
    return {"failed": failed, "missing": missing, "extra": extra, "mismatches": mismatches, "mechanisms": mechanisms}


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------

def compare(contract: dict, source: list[dict], target: list[dict],
            source_status: str = "ok", target_status: str = "ok",
            accepted: list | None = None) -> OrderedDict:
    test_id = contract["test_id"]
    comp = contract.get("comparison", {})
    execution = contract.get("execution", {})
    key_fields: list[str] = comp.get("key_fields", [])
    measures: dict = comp.get("measures", {}) or {}
    dates = comp.get("dates", {}) or {}
    date_fields = set(dates.get("fields", []) or [])
    limit = execution.get("limit")
    reasons: list[str] = []
    mechanisms: list[str] = []
    differences = OrderedDict([("missing_in_target", []), ("extra_in_target", []), ("measure_mismatches", []), ("order", None)])

    def result(outcome: str, verdict: str | None, mechanism: str | None = None) -> OrderedDict:
        return OrderedDict([
            ("test_id", test_id),
            ("source_object", contract.get("source_object")),
            ("target_object", contract.get("target_object")),
            ("baseline", contract.get("baseline")),
            ("outcome", outcome),
            ("verdict", verdict),
            ("gate_satisfied", verdict in PASSING_VERDICTS),
            ("divergence_mechanism", mechanism),
            ("reasons", reasons),
            ("counts", OrderedDict([("source_rows", len(source)), ("target_rows", len(target))])),
            ("differences", differences),
            ("tolerances_used", OrderedDict((m, s) for m, s in sorted(measures.items()))),
            ("execution", OrderedDict((k, execution.get(k)) for k in ("principal", "timezone", "data_snapshot", "limit", "cache_policy"))),
            ("inputs", OrderedDict([("source_status", source_status), ("target_status", target_status)])),
            ("contract_sha256", hashlib.sha256(json.dumps(contract, sort_keys=True, default=str).encode()).hexdigest()),
        ])

    # Execution outcomes come first: nothing below is meaningful without two clean result sets.
    if source_status == "error":
        reasons.append("source query failed; a source failure is never a target success")
        return result("BLOCKED", None)
    if target_status == "error":
        reasons.append("target query failed")
        return result("FAIL", "fail")
    if limit and (source_status == "truncated" or target_status == "truncated" or len(source) >= int(limit) or len(target) >= int(limit)):
        reasons.append(f"a side reached the row limit ({limit}); a truncated result cannot establish equivalence")
        return result("INCONCLUSIVE", None)
    if not source and not target:
        if comp.get("expected_rows", "nonzero") == "nonzero":
            reasons.append("both sides empty but the contract expects rows; the fixture did not exercise data")
            return result("INCONCLUSIVE", None)
        return result("PASS", "pass")

    source = apply_field_map(source, comp.get("field_map") or {})

    # Core comparison: keyed multiset, then typed measures on matched keys.
    core = _core_compare(source, target, key_fields, measures)
    failed = core["failed"]

    # Timezone mechanism: the whole source shifted by one date bucket matches the target exactly.
    # Only when the model batch recorded a convert_tz decision; a shift is never inferred.
    if failed and date_fields and dates.get("timezone_conversion_recorded") is True and key_fields:
        for shift in (1, -1):
            shifted = _shift_dates(source, date_fields, dates.get("bucket", "day"), shift)
            trial = _core_compare(shifted, target, key_fields, measures)
            if not trial["failed"]:
                core, failed = trial, False
                mechanisms.append("timezone_conversion")
                reasons.append(f"target equals source shifted by {shift:+d} {dates.get('bucket', 'day')} on {sorted(date_fields)} under a recorded convert_tz decision")
                source = shifted
                break

    if len(source) != len(target):
        reasons.append(f"row count differs: source {len(source)}, target {len(target)}")
    if core["missing"] or core["extra"]:
        differences["missing_in_target"] = [OrderedDict([("key", list(k)), ("multiplicity", n)]) for k, n in sorted(core["missing"].items(), key=lambda kv: [str(x) for x in kv[0]])]
        differences["extra_in_target"] = [OrderedDict([("key", list(k)), ("multiplicity", n)]) for k, n in sorted(core["extra"].items(), key=lambda kv: [str(x) for x in kv[0]])]
        reasons.append(f"{sum(core['missing'].values())} row(s) missing in target, {sum(core['extra'].values())} extra in target (by key, multiplicity preserved)")
    if core["mismatches"]:
        differences["measure_mismatches"] = core["mismatches"]
        reasons.append(f"{len(core['mismatches'])} measure value(s) differ beyond tolerance")
    for mech in core["mechanisms"]:
        if mech not in mechanisms:
            mechanisms.append(mech)

    # Order.
    if not failed and key_fields:
        src_seq = [key_of(r, key_fields) for r in source]
        tgt_seq = [key_of(r, key_fields) for r in target]
        if src_seq != tgt_seq:
            if comp.get("row_semantics", "multiset") == "ordered":
                differences["order"] = "sequence differs and ordering is part of the tile's behaviour"
                reasons.append("ordered comparison: same rows, different order")
                failed = True
            elif not comp.get("tile_sorted", False):
                differences["order"] = "same multiset, different order, tile has no explicit sort"
                if "sort_only" not in mechanisms:
                    mechanisms.append("sort_only")

    if failed:
        for entry in accepted or []:
            if entry.get("test_id") == test_id and entry.get("approver") and entry.get("reason"):
                reasons.append(f"accepted difference: {entry['reason']} (approver {entry['approver']}, {entry.get('date', 'undated')})")
                return result("ACCEPTED_DIFFERENCE", "pass_declared_deviation")
        return result("FAIL", "fail")
    if mechanisms:
        return result("PASS", "pass_qualified", mechanisms[0] if len(mechanisms) == 1 else "+".join(sorted(mechanisms)))
    return result("PASS", "pass")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--source", required=True, type=Path, help="Looker result rows (CSV or JSON)")
    ap.add_argument("--target", required=True, type=Path, help="Omni result rows (CSV or JSON)")
    ap.add_argument("--source-status", default="ok", choices=["ok", "error", "truncated"])
    ap.add_argument("--target-status", default="ok", choices=["ok", "error", "truncated"])
    ap.add_argument("--accepted", type=Path, default=None, help="YAML list of accepted differences: test_id, reason, approver, date")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    accepted = yaml.safe_load(args.accepted.read_text(encoding="utf-8")) if args.accepted and args.accepted.exists() else []
    source = load_rows(args.source) if args.source.exists() else []
    target = load_rows(args.target) if args.target.exists() else []
    verdict = compare(contract, source, target, args.source_status, args.target_status, accepted or [])
    text = json.dumps(verdict, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if verdict["gate_satisfied"] else 1


if __name__ == "__main__":
    sys.exit(main())

---
description: Lane verdict JSON contract and single-writer merge rules — the shared shape every equivalency lane writes and the deterministic algorithm the coordinating session merges it with
---

# Equivalency — Lane Verdict Schema and Merge Rules

This is a shared utility contract, not a command. It is consumed by `equivalency-validate` (lane fan-out and the merge step), `equivalency-post-merge-verify`, and `dbt-migration-batch-raise` (candidate derivation reads the merged register). Its purpose is to make register ingestion mechanical: on a live engagement where every lane invented its own result shape, the coordinator's merge scripts had to adapt per lane (five shape variants in a single day). One contract removes that class of work.

## Lane verdict file

Every equivalency lane writes exactly one JSON file per run to:

```
.wire/releases/<release>/migration/verdicts/run_{N}/{lane_id}.json
```

`{N}` is the equivalency run number (the same number as `equivalency_report_{N}.md`); `{lane_id}` is the lane's declared identifier (e.g. `w05-build-pool`, `silver-schema-a`). The file is written **incrementally**: the lane appends to its `verdicts` array and rewrites the file after each object completes, so a lane killed mid-run loses at most the in-flight object and a resumed lane skips every object already present in its own file.

```json
{
  "schema_version": 1,
  "lane_id": "silver-schema-a",
  "run_point": "standard",
  "generated_at": "2026-08-07T14:02:11Z",
  "mode": "baseline",
  "baseline_t": "2026-08-01T00:00:00Z",
  "scope": "full_migration",
  "tenant_predicate_sha256": null,
  "verdicts": [
    {
      "model": "orders",
      "object_type": "model",
      "verdict": "pass",
      "divergence_mechanism": null,
      "method_class": "full_history",
      "file_version": "9abc1234",
      "evidence_ref": "migration/equivalency_report_12.md#orders"
    }
  ]
}
```

| Field | Rules |
|---|---|
| `schema_version` | Integer, currently `1`. A merge step that meets a version it does not know must stop and report, never guess. |
| `lane_id` | Non-empty string, unique per run. Doubles as the file basename. |
| `run_point` | `standard` \| `pre_raise` \| `post_merge_prod` — one per file; a lane never mixes run points. |
| `generated_at` | UTC ISO-8601 instant of the last rewrite. |
| `mode` | `live` \| `baseline`; `baseline_t` is the pinned instant in baseline mode, else `null`. |
| `scope` / `tenant_predicate_sha256` | Optional; default `full_migration` / `null`. A tenant-carve-out lane records the SHA-256 of the exact predicate it applied, so a carve-out verdict can never be mistaken for a full-estate one. |
| `verdicts[].verdict` | A taxonomy value: `pass` \| `pass_qualified` \| `pass_declared_deviation` \| `diff_vintage` \| `diff_availability` \| `diff_schema_type` \| `fail` (see `equivalency-validate`, Verdict taxonomy). A `pass_declared_deviation` row carries `divergence_mechanism: declared_deviation:<id>` (#219). |
| `verdicts[].divergence_mechanism` | Required non-null for every verdict except `pass` — the named mechanism the divergence was drilled to (or, for `pass_qualified`, the allow-listed benign mechanism). A non-`pass` verdict with a null mechanism is malformed and the merge rejects the row. |
| `verdicts[].method_class` | The declared comparison window class used (e.g. `full_history`, `windowed_event`, `aggregate_only`) — see the Verdict bar in `equivalency-validate`. |
| `verdicts[].object_type` | `model` \| `snapshot` \| `reverse_etl_sync` (`reverse-etl-equivalency-validate`) \| `metabase_card` (`metabase-equivalency-validate`, #184). The merge rules are object-type-agnostic. |
| `verdicts[].file_version` | The `last_migrated_commit` the verdict binds to. A verdict is evidence about one exact file version, never about the model name in the abstract. |
| `verdicts[].evidence_ref` | Path plus anchor to the check evidence in the run's report. |
| `verdicts[].window` | Optional. **Required when `divergence_mechanism` is `declared_window_availability`** (see `equivalency-validate` Step 1e); omitted or `null` otherwise. An object carrying the declared comparison window as structured fields, so the verdict itself states what was compared instead of a PR body re-arguing it in prose: `{"floor": "<UTC instant>", "floor_derivation": "bronze_min_loaded_at" \| "partition_metadata" \| "explicit", "cap": "<UTC instant>", "exclusions": [{"range": "<UTC date or range>", "reason": "<why>"}], "in_window_result": "pass"}`. A `declared_window_availability` verdict with no `window` object, or with `in_window_result` other than `pass`, is malformed and the merge rejects the row (an in-window divergence is never availability — it is `fail`). |

## Single-writer rule

Lanes write **only** their own verdict file. Exactly one process (the coordinating session, or the `equivalency-validate` run itself when there is no fleet) merges lane files into `migration/migration_register.csv` and `migration/migration_verdict_log.csv`. No lane ever writes either file directly. This rule exists because concurrent register writes on a live engagement corrupted each other's rows; it is a convention the lane brief must state, enforced by review of the lane brief, not by tooling.

## Merge algorithm (deterministic)

Given the register rows and the set of lane files for a run, the merge is a pure function. Tests mirror these rules exactly (`wire/tests/platform_migration/validate_verdict_log_merge.py`).

1. **Order the input.** Sort lane files by `lane_id` (lexicographic, ascending); within a file, take `verdicts` in array order. This is the append order.
2. **Append to the log, always.** Every well-formed verdict row appends one row to `migration/migration_verdict_log.csv` with `written_at` set to the lane file's `generated_at`. No dedup, no rewrites: two verdicts for the same model in one run produce two log rows.
3. **Reject malformed rows.** A row with an unknown `verdict` value, or a non-`pass` verdict with a null `divergence_mechanism`, is skipped entirely (no log row, no register touch) and reported in the merge summary as `malformed`.
4. **Update the register, conditionally.** Per model, only `run_point` values `standard` and `pre_raise` update `last_equivalence_result` / `last_equivalence_t` / `last_validated_commit`. Among a run's candidate rows for one model, the row from the lane file with the **latest `generated_at`** wins; ties break by `lane_id` (lexicographic, last wins, matching append order), and any same-model multi-lane collision is reported as `conflict` in the merge summary.
5. **`post_merge_prod` rows touch delivery, not equivalence.** A `post_merge_prod` verdict never updates the `last_equivalence_*` columns. If the verdict is `pass`, `pass_qualified`, or `pass_declared_deviation` **and** the model's `delivery_stage` is `merged`, set `delivery_stage: production_verified`. If `delivery_stage` is not `merged`, leave the register untouched and report `not_merged` — a production verdict for something not on the client's main is evidence filed for later, not a stage advance.
6. **Unknown models.** A verdict for a model with no register row still appends to the log (history is history) but touches nothing else; report `unknown_model`.

The merge summary (counts of appended, updated, malformed, conflict, not_merged, unknown_model) goes into the equivalency report for the run.

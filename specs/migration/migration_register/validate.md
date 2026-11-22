---
wire_schema: "1.0"
command: validate
artifact: migration_register
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: migration_register
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the per-model migration register — schema, uniqueness, coverage, and state consistency

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Register — Validate

## Validation Checks

Read `migration/migration_register.csv`, `audit/dbt_audit.csv`, `audit/reverse_etl_audit.csv` where it exists, and the latest equivalency report.

**Check 1 — Schema present**
The header carries all eighteen columns: `model, object_type, source_path, source_layer, last_migrated_commit, bq_target, state, snapshot_strategy, last_equivalence_result, last_equivalence_t, last_validated_commit, last_reverse_ported_commit, delivery_stage, pr_url, parent_release, parent_model, parent_verdict_ref, notes`. A twelve-column register predating v3.11.0 is a FAIL with the fix hint "run /wire:upgrade to add delivery_stage and pr_url"; a fourteen-column register predating the cross-release linkage columns (#180) is a FAIL with the fix hint "run /wire:upgrade to add parent_release, parent_model, parent_verdict_ref"; a seventeen-column register predating the reverse-port sweep column (#195) is a FAIL with the fix hint "run /wire:upgrade to add last_reverse_ported_commit".
PASS/FAIL.

**Check 2 — One row per in-scope object, unique key**
Every in-scope model from `dbt_audit.csv` has exactly one `object_type = model` row, and every snapshot from `dbt_snapshots.csv` has exactly one `object_type = snapshot` row; `model` is unique across all rows. Where `audit/reverse_etl_audit.csv` exists, every audit sync has exactly one `object_type = reverse_etl_sync` row, joined on the **normalised sync id** (`reverse-etl-twin-generate`'s Step 0 rule, applied to both sides: the audit's raw `sync_id` is not the key), and a `reverse_etl_sync` row matching no audit row on that join is an orphan unless marked `state = removed` (#191). A register with no `reverse_etl_sync` rows on a release whose reverse-ETL audit exists predates the sync seeding: FAIL with the fix hint "re-run /wire:migration-register-generate to seed the sync rows". `metabase_card` and `metabase_dashboard` rows (#184) trace to the Metabase manifests; they are not orphans. Any other row not in a source catalogue is an orphan unless marked `state = removed`.
PASS/FAIL with missing/duplicate/orphan objects.

**Check 3 — State values valid**
Every `state` is one of `pending | migrated | drifted | failed | removed | deferred`.
PASS/FAIL with offending rows.

**Check 4 — Migrated rows are complete, with a physical `bq_target`**
Every `state = migrated` row has a non-null `last_migrated_commit` and `bq_target`. A migrated model with no recorded source commit can't be drift-checked. For `object_type` `model` and `snapshot` rows, `bq_target` carries the fully qualified physical form: exactly three dot-separated segments (`project.dataset.table` / `database.schema.table`, #201). A two-segment value is the legacy dbt-relative form: FAIL with the fix hint "run /wire:upgrade to re-resolve bq_target from the target manifest"; until it is re-resolved, `equivalency-validate` classifies the row `unresolved_target` rather than guessing a physical path. `metabase_card`/`metabase_dashboard` rows carry a connection + database reference and are exempt from the segment rule.
PASS/FAIL with offending rows.

**Check 5 — Equivalence fields consistent**
`last_equivalence_result` is one of `pass | pass_qualified | diff_vintage | diff_availability | diff_schema_type | fail | null` (the verdict taxonomy; the legacy value `info` is accepted with a warning and read as `pass_qualified`); when it is non-null, `last_validated_commit` is set. `last_equivalence_t` is a UTC instant or null.
PASS/FAIL.

**Check 6 — Validated-vs-migrated coherence**
No row claims `last_equivalence_result = pass` with a `last_validated_commit` that predates `last_migrated_commit` (would mean it was validated before it was (re)migrated).
PASS/FAIL with offending rows.

**Check 7 — Snapshot strategy valid and signed off**
Every `object_type = snapshot` row has a `snapshot_strategy` of exactly `copy_and_continue` or `rebuild_from_T`; every `object_type = model` row has a blank `snapshot_strategy`. Every `rebuild_from_T` row records a data-owner sign-off in `notes` — a `rebuild_from_T` with no sign-off is a FAIL. A blank `snapshot_strategy` on a snapshot row is also a FAIL (a snapshot must never be left unassigned, which would risk defaulting to a history-discarding rebuild).
PASS: every snapshot row has a valid, signed-off-where-required strategy. FAIL: list offending rows. Note "no snapshot rows" when none exist.

**Check 8 — Delivery stage consistent**
Every `delivery_stage` is blank or one of `in_pr | merged | production_verified`. A non-blank `delivery_stage` requires `state = migrated` or `state = drifted` (delivery progress survives drift; it cannot precede migration). `in_pr` requires a non-blank `pr_url`. `production_verified` requires at least one `run_point = post_merge_prod` row with verdict `pass` or `pass_qualified` for the model in `migration/migration_verdict_log.csv` (skip this sub-check with a warning if the log is absent).
PASS/FAIL with offending rows.

**Check 9 — Verdict log well-formed (when present)**
If `migration/migration_verdict_log.csv` exists: the header carries `model, object_type, run_point, verdict, divergence_mechanism, method_class, mode, baseline_t, file_version, lane_id, report_ref, written_at`; every `run_point` is one of `standard | pre_raise | post_merge_prod`; every `verdict` is a taxonomy value; every verdict other than `pass` has a non-blank `divergence_mechanism`; `written_at` values are non-decreasing down the file (append-only order).
PASS/FAIL with offending rows. Note "no verdict log" when the file does not exist.

**Check 10 — Cross-release linkage consistent (#180)**
The three parent columns travel together and only on relocated rows: a row with `origin: relocate` in `notes` has a non-blank `parent_release` and `parent_model` (blank `parent_verdict_ref` is legal — it records an evidence gap, not an error); a row without `origin: relocate` has all three blank. Every non-blank `parent_verdict_ref` starts with the row's own `parent_release` followed by `:`.
PASS/FAIL with offending rows. Note "no relocated rows" when none exist.

**Check 11 — Sync rows carry the audit's approach (#191)**
Every `object_type = reverse_etl_sync` row records `approach: <value>` in `notes`, where `<value>` is in the closed vocabulary (`specs/utils/reverse_etl_approach.md`) and equals the joined audit row's `migration_approach`. A sync row with no `approach:` note, an unrecognised value, or a value that disagrees with the audit is a FAIL: the register must never restate the approach differently from where it was assigned.
PASS/FAIL with offending rows. Note "no sync rows" when none exist.

### Update status

```yaml
artifacts:
  migration_register:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact_id, `Migration Register` as artifact_name, and the `file` value from `artifacts.migration_register` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_register` as artifact, `validate` as action.

---
wire_schema: "1.0"
command: validate
artifact: bulk_copy_migration
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
  - artifact: bulk_copy_migration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate bulk copy migration runbook — tenant guard, two-stage gate, scoped service account
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Bulk Copy Migration — Validate

## Flags

- `--wave <id>` — validate the wave-labelled runbook (`bulk_copy_migration_runbook_{wave_id}.md`) against the tables `migration/migration_batching.csv` assigns to this wave, resolved identically to `bulk-copy-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Every check below reads "in-scope table" as this resolved set instead of every landed table for `include_in_migration: true` connectors.
- `--snapshots` — validate the snapshots-labelled runbook (`bulk_copy_migration_runbook_snapshots.md`) produced by `bulk-copy-migration-generate --snapshots`. Only the snapshot-history-copy checks apply: run **Check 9** over the resolved `copy_and_continue` snapshot set and skip the raw-table checks (Checks 1–2, 4). This is the retrofit companion for a full-migration snapshot-history copy. Standalone scope — abort if combined with `--wave`.

## Validation Checks

Read `status.md` to confirm the run's `method: runbook` and its guard path. Read the bulk copy runbook (wave-labelled under `--wave`, snapshots-labelled under `--snapshots`) and `audit/ingestion_audit.md`.

**Scope guard the checks match.** Determine the runbook's copy path from `status.md` (`artifacts.bulk_copy_migration.scope` / `copy_path`) and validate accordingly:

- **Raw-table / connector copy (carve-out):** `migration.scope == tenant_carveout` and `migration.tenant_predicate` is set. All checks below apply, including the tenant guard (Check 3). This is the existing behaviour.
- **Snapshot-history copy in a full migration (`--snapshots`):** `migration.scope` is `full_migration` or absent, the runbook copies snapshot histories only, and there is **no** tenant predicate. Check 3 (tenant guard on every extract) does **not** apply — the copy is unfiltered by design; note it "not applicable — unfiltered full-migration snapshot copy" rather than failing. Check 9's tenant-predicate sub-clause (d) likewise does not apply in this path. The raw-table checks (Checks 1, 2, 4) are skipped (no raw tables in this runbook).

A `full_migration` runbook that copies **raw/connector tables** is a FAIL — bulk-copy of raw tables is carve-out-only (raw tables re-land via `/wire:ingestion-migration-generate`).

**Check 1 — All in-scope tables in the runbook**
The count of tables in the runbook matches the count of in-scope landed tables (the wave-resolved set under `--wave`, otherwise every landed table for connectors with `include_in_migration: true`) in the ingestion audit.
PASS/FAIL with missing tables listed.

**Check 2 — Each table has a source→target destination mapping**
Every table step names the source Snowflake object and its target BigQuery dataset/table.
PASS/FAIL with gaps.

**Check 3 — Tenant guard on every extract** (carve-out path only)
Every source extract step includes `WHERE {migration.tenant_predicate}`, matching `migration.tenant_predicate` exactly. No step extracts unfiltered data.
PASS: predicate present and matching on all steps.
FAIL: any step missing the predicate or using a different predicate.
**Not applicable to a full-migration snapshot-history copy** (`--snapshots`): that path is unfiltered by design — note "not applicable — unfiltered full-migration snapshot copy" rather than running the scan.

**Check 4 — Two-stage copy with validation gate**
Each table follows the pilot-partition → validation gate → remainder structure. The gate runs equivalency check 1 (row count) and check 6 (checksum), tenant-scoped, and Stage 2 is conditional on both passing.
PASS/FAIL with tables missing the gate.

**Check 5 — Scoped service account and tenant guard documented**
The runbook names a service account scoped to the extracted tenant's target project/dataset (and dedicated staging bucket for GCS-staged), and confirms the destination is `migration.target_project` and not in `data_safety.production_projects`.
PASS/FAIL.

**Check 6 — Credential rotation / staging checklist present**
The runbook includes a credential checklist (scoped SA key, GCS bucket access, target-only BigQuery grants).
PASS/FAIL.

**Check 7 — Source decommission deferred to cutover**
The runbook explicitly notes the source stays live and unmodified during the copy; decommission is deferred to the cutover phase.
PASS: note present.
FAIL: source decommission/deletion steps found in the copy runbook (should be in cutover).

**Check 8 — Post-copy validation steps present**
The runbook hands off to `/wire:equivalency-validate` for the full tenant-scoped seven-check pass once all tables are copied.
PASS/FAIL.

**Check 9 — Snapshot history copies preserve SCD state, ordinal order, and tenant scope**
If the migration register / `dbt_snapshots.csv` lists any `copy_and_continue` snapshots, the runbook has a copy step for each that: (a) lands at the snapshot's exact `target_schema` relation; (b) preserves the payload columns plus the four SCD meta columns (`dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to`) in their ordinal order (payload first, meta columns at the tail in that order), translating types via the pair's `type_mapping.md` / "Snapshot SCD mechanisms" section; (c) reads the source from the frozen clone at baseline `T`, not the live snapshot; (d) **under carve-out only**, applies `WHERE {migration.tenant_predicate}` to the snapshot extract (in a full migration the snapshot-history copy is unfiltered — sub-clause (d) does not apply); and (e) is ordered **before** the target `dbt snapshot` adopt-and-continue run, never after. Any `rebuild_from_T` snapshot is correctly **absent** from the copy runbook (it starts fresh at `T` on a recorded sign-off, so there is no history to copy).
PASS: every `copy_and_continue` snapshot has a conforming copy step and no `rebuild_from_T` snapshot is copied. FAIL: list snapshots with a missing/incomplete copy step, a dropped or reordered meta column, an unfrozen (live) source read, a missing tenant predicate, or a `rebuild_from_T` snapshot erroneously copied. Note "no snapshots in scope" when none apply.

### Update status

```yaml
artifacts:
  bulk_copy_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    snapshots_validate: pass | fail   # set only when run with --snapshots (Check 9 only)
    wave_validate:               # set only when run with --wave, keyed by wave id
      B01: pass | fail
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact_id, `Bulk Copy Migration` as artifact_name, and the `file` value from `artifacts.bulk_copy_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bulk_copy_migration` as artifact, `validate` as action.

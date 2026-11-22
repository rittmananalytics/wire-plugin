---
wire_schema: "1.0"
command: validate
artifact: reverse_etl_audit
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
  - artifact: reverse_etl_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate reverse ETL audit completeness, warehouse dependency coverage, and migration approach assignments

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Reverse ETL Audit — Validate

## Purpose

Checks the reverse ETL audit for completeness and internal consistency. Confirms every sync has a migration approach, all warehouse dependencies are mapped, Lightning engine requirements are flagged, and the sync count matches the source data. Produces a PASS/FAIL report with specific gaps to address before review.

## Prerequisites

- `audit/reverse_etl_audit.md` exists (reverse_etl_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/reverse_etl_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, Sync Catalog, Warehouse Dependency Map, Lightning Engine Syncs, Excluded Syncs).

### Step 2: Run validation checks

**Check 1 — All syncs have a migration approach**
Every row in the sync catalog has a value in the `migration_approach` column (repoint / rewrite_model / rebuild / decommission).
PASS: All rows populated.
FAIL: List syncs missing a migration approach.

**Check 2 — All syncs have a complexity rating**
Every row has a value in the `complexity` column (Low / Medium / High).
PASS: All rows populated.
FAIL: List syncs missing complexity.

**Check 3 — Source objects resolved across all model types, coverage reported**
Source-object resolution is attempted for every model type (`rawSql`, `dbtModel`, `table`, `custom`) — not just `rawSql`. Each sync with a resolvable source has at least one entry in `warehouse_objects`; each sync that genuinely could not be resolved is marked `source_resolved: false` and listed explicitly under "Unresolved syncs". The audit reports the source-resolution coverage metric (`resolved_sync_count` / `active_sync_count`), and status.md carries `resolved_sync_count`, `unresolved_sync_count`, and `source_resolution_coverage_pct`.
PASS: Resolution attempted for all model types, coverage metric present, and every unresolved sync is listed (none silently blank).
FAIL: `table`/`custom` syncs left blank without being listed as unresolved, or the coverage metric is missing.

**Check 4 — dbt model syncs cross-referenced**
Every sync with `model_type: dbtModel` has the dbt model name listed and a note confirming whether that model exists in the dbt audit (or noting it is out of scope).
PASS: All dbt model syncs have a cross-reference note.
FAIL: List dbt model syncs without cross-reference.

**Check 5 — Lightning engine syncs flagged**
If `lightning_sync_count` in status.md is > 0, the audit includes a Lightning Engine section listing the affected syncs and the two schema requirements.
PASS: Section present and populated, or lightning_sync_count = 0.
FAIL: Lightning syncs exist but section is missing or empty.

**Check 6 — Disabled/broken syncs have a decision**
If `data_source` in status.md is `hightouch_api` or `csv`: every sync with `status: disabled` or `status: interrupted` has either `migration_approach: decommission` with a reason, or `include_in_migration: true` with a note explaining why it will be migrated despite its current status.
PASS: All non-active syncs have a clear decision.
FAIL: List undecided non-active syncs.

If `data_source: git`: sync status is unavailable from Git files. Auto-pass this check and note in the validation report:
```
Check 6 skipped — audit sourced from Git files; runtime sync status not available.
Review sync decommission decisions manually with the client before proceeding to review.
```

**Check 7 — Sync count matches source**
The count of rows in the sync catalog matches `sync_count` in status.md.
PASS: Counts match.
FAIL: Report discrepancy.

**Check 8 — Row volume estimates present**
If `data_source` is `hightouch_api` or `csv`: at least 80% of active syncs have a non-null `last_run_rows`. Syncs with no run history should have a note.
PASS: ≥80% of active syncs have row volumes.
FAIL: Report percentage and list syncs missing estimates.

If `data_source: git`: row volumes are unavailable. Auto-pass this check and note in the validation report:
```
Check 8 skipped — audit sourced from Git files; runtime row volumes not available.
Row volume estimates are needed for cutover sequencing. Obtain these from the client
(Hightouch UI → sync run history) and add to the audit before migration inventory is drafted.
```

**Check 9 — `migration_approach` is inside the closed vocabulary (v3.11.7)**
Every row's `migration_approach` is one of exactly `repoint`, `rewrite_model`, `rebuild`, `decommission` (`specs/utils/reverse_etl_approach.md`). No blanks, no synonyms, no fifth value.
PASS: every row inside the set. FAIL: list each offending sync id with the value found, and the closed set.

This is a producer-side check because the vocabulary has already drifted once on the consumer side, silently. Two commands shipped keying on `retire`, a value this audit never writes, so on a release with 98 `decommission` syncs one command would have authored 98 unnecessary twins and the other would have listed none of them for retirement. Neither errored. Enforcing the set only in the consumers means each consumer discovers the drift independently, which is how one token became four commands' worth of the same bug. It is enforced here, where the value is written.

### Step 3: Write validation report

Append a `## Validation` section to `audit/reverse_etl_audit.md`:

```markdown
## Validation

**Run date**: {{TODAY}}
**Overall result**: PASS | FAIL

| Check | Result | Detail |
|-------|--------|--------|
| 1. Migration approaches complete | PASS/FAIL | ... |
| 2. Complexity ratings complete | PASS/FAIL | ... |
| 3. rawSql warehouse objects extracted | PASS/FAIL | ... |
| 4. dbt model syncs cross-referenced | PASS/FAIL | ... |
| 5. Lightning engine syncs flagged | PASS/FAIL | ... |
| 6. Non-active syncs have decisions | PASS/FAIL | ... |
| 7. Sync count matches source | PASS/FAIL | ... |
| 8. Row volume estimates present | PASS/FAIL | ... |

### Gaps to address
[List any FAIL items with specific syncs to fix]
```

### Step 4: Update status

```yaml
artifacts:
  reverse_etl_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:reverse-etl-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:reverse-etl-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_audit` as artifact_id, `Reverse ETL Audit` as artifact_name, and the `file` value from `artifacts.reverse_etl_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_audit` as artifact, `validate` as action.

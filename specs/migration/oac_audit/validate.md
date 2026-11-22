---
wire_schema: "1.0"
command: validate
artifact: oac_audit
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
  - artifact: oac_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate OAC audit completeness, warehouse dependency coverage, connection documentation, raw SQL construct classification, and migration approach assignments

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# OAC Audit — Validate

## Purpose

Checks the OAC audit for completeness and internal consistency: every physical table has a migration approach and complexity, warehouse dependencies are mapped with a coverage metric, every physical join and physical-layer SQL construct is classified, `redesign`/`manual-review-out-of-scope` constructs are surfaced rather than silently translated, connection pools are recorded, the logical and presentation layers are catalogued with their dialect-neutral impact confirmed, structural validation (`validate_smml.py`) was run, and the model counts match the source. Produces a PASS/FAIL report with specific gaps to address before review.

## Prerequisites

- `audit/oac_audit.md` exists (oac_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/oac_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/oac_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, Physical Table Catalog, Physical Join / Raw SQL Construct Catalog, Database/Connection Pool Inventory, Logical Layer Catalog, Presentation Layer Catalog, Warehouse Dependency Map, Structural Validation, Unresolved Physical Tables, Excluded Content).

### Step 2: Run validation checks

**Check 1 — All physical tables have a migration approach**
Every row in the physical table catalog has a value in `migration_approach` (repoint / rewrite_sql / rebuild).
PASS/FAIL with tables missing an approach.

**Check 2 — All physical tables have a complexity rating**
Every row has a `complexity` value (Low / Medium / High).
PASS/FAIL with tables missing complexity.

**Check 3 — Source objects resolved across source_type, coverage reported**
Source-object resolution is attempted for every active physical table regardless of `source_type`. Each table with a resolvable source has ≥1 entry in `warehouse_objects`; each genuinely unresolvable table is marked `source_resolved: false` and listed under "Unresolved physical tables". The coverage metric (`resolved_table_count` / `active_table_count`) is present, and status.md carries `resolved_table_count`, `unresolved_table_count`, and `source_resolution_coverage_pct`.
PASS: resolution attempted for all source_types, coverage present, every unresolved table listed.
FAIL: tables left blank without being listed, or coverage metric missing.

**Check 4 — dbt model physical tables cross-referenced**
Every physical table whose resolved source is a dbt model has a note confirming whether that model exists in the dbt audit (or is out of scope).
PASS/FAIL with tables missing the cross-reference.

**Check 5 — Databases and connection pools documented**
Every distinct database and connection pool referenced by a physical table appears in the connection inventory with its `databaseType`.
PASS/FAIL.

**Check 6 — Every physical join classified, every raw SQL construct scanned**
Every entry in `physicalTable.joins` has a `use_join_expression` value and, for expression-based joins, a `construct_action`. Every `SELECT`/`STORED_PROCEDURE`-sourced physical table, every connection-pool script, and every non-identity physical mapping expression has been scanned and assigned a `construct_action` (translate / redesign / manual-review-out-of-scope).
PASS/FAIL with an unscanned or unclassified construct.

**Check 7 — redesign and manual-review-out-of-scope constructs surfaced, not silently tiered**
Every construct classified `redesign` is listed in its own bucket for human review, with no `migration_approach` inferred mechanically for the physical table beyond `rebuild`. Every `manual-review-out-of-scope` construct is listed separately with a note that it is not part of the mechanical translation.
PASS/FAIL with a `redesign`/`manual-review-out-of-scope` construct missing from its bucket, or silently folded into a `translate` count.

**Check 8 — Logical and presentation layers catalogued with migration impact confirmed**
Every logical table and subject area has a `migration_impact` value. Any logical table marked `migration_impact: see construct <id>` has a corresponding row in the raw SQL construct catalog for that construct id.
PASS/FAIL with a missing `migration_impact` or a dangling construct reference.

**Check 9 — Structural validation was run and recorded**
The audit's Structural Validation section contains the verbatim result of `validate_smml.py` against the semantic-model repo, and `smml_validation: pass | fail` is set in status.md. If `fail`, the specific errors are listed.
PASS: result recorded, matches status.md. FAIL: no structural validation section, or status.md value doesn't match the recorded result.

**Check 10 — Archived/unused content has a decision**
Every archived or unused subject area or physical table has either `include_in_migration: false` with a decommission reason, or `include_in_migration: true` with a note.
PASS/FAIL with undecided content.

**Check 11 — Model counts match source**
The counts of databases, connection pools, physical tables, physical joins, logical tables, and subject areas in the audit tables match `database_count`, `connection_pool_count`, `physical_table_count`, `physical_join_count`, `logical_table_count`, and `subject_area_count` in status.md.
PASS/FAIL with mismatched counts.

### Step 3: Write validation report

Append a `## Validation` section to `audit/oac_audit.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  oac_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:oac-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:oac-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_audit` as artifact_id, `OAC Audit` as artifact_name, and the `file` value from `artifacts.oac_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `oac_audit` as artifact, `validate` as action.

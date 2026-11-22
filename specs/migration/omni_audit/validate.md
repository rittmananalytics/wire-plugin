---
wire_schema: "1.0"
command: validate
artifact: omni_audit
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: omni_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate Omni audit completeness, warehouse dependency coverage, connection documentation, and migration approach assignments

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Audit — Validate

## Purpose

Checks the Omni audit for completeness and internal consistency: every view has a migration approach and complexity, warehouse dependencies are mapped with a coverage metric, every tile is classified as topic-backed or raw-SQL, every raw-SQL tile is scanned and given its own approach, connections are recorded, and the model/content counts match the source. Produces a PASS/FAIL report with specific gaps to address before review.

## Prerequisites

- `audit/omni_audit.md` exists (omni_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/omni_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/omni_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, Model Catalog, Content Hierarchy, Connection Inventory, Warehouse Dependency Map, Raw-SQL Tile Catalog, Unresolved Views, Unresolved Raw-SQL Tiles, Excluded Content).

### Step 2: Run validation checks

**Check 1 — All views have a migration approach**
Every row in the model catalog has a value in `migration_approach` (repoint / rewrite_sql / rebuild).
PASS/FAIL with views missing an approach.

**Check 2 — All views have a complexity rating**
Every row has a `complexity` value (Low / Medium / High).
PASS/FAIL with views missing complexity.

**Check 3 — Source objects resolved across sql_type, coverage reported**
Source-object resolution is attempted for every view regardless of `sql_type`. Each view with a resolvable source has ≥1 entry in `warehouse_objects`; each genuinely unresolvable view is marked `source_resolved: false` and listed under "Unresolved views". The coverage metric (`resolved_view_count` / `active_view_count`) is present, and status.md carries `resolved_view_count`, `unresolved_view_count`, and `source_resolution_coverage_pct`.
PASS: resolution attempted for all sql_types, coverage present, every unresolved view listed.
FAIL: views left blank without being listed, or coverage metric missing.

**Check 4 — dbt model views cross-referenced**
Every view whose resolved source is a dbt model has a note confirming whether that model exists in the dbt audit (or is out of scope).
PASS/FAIL with views missing the cross-reference.

**Check 5 — Connections documented**
Every distinct `connection_id` referenced by a view appears in the connection inventory with its engine.
PASS/FAIL.

**Check 6 — Every tile classified, raw-SQL tiles scanned**
Every tile in the content hierarchy has a `query_surface` value (`topic` or `raw_sql`). Every `raw_sql` tile has been scanned for source-dialect constructs (`::`, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, variant `:` paths) and has a `sql_summary`.
PASS/FAIL with tiles missing a query_surface value or an unscanned raw-SQL tile.

**Check 7 — Raw-SQL tiles have a migration approach, unresolved tiles listed**
Every `raw_sql` tile has a `migration_approach` (repoint / rewrite_sql / rebuild) distinct from `inherits_via_model`. Each raw-SQL tile with a resolvable source has ≥1 entry in `warehouse_objects`; each unresolvable one is marked `source_resolved: false` and listed under "Unresolved raw-SQL tiles" — never dropped.
PASS/FAIL with tiles missing an approach or an unlisted unresolved tile.

**Check 8 — Archived/unused content has a decision**
Every archived or unused workbook/tile has either `include_in_migration: false` with a decommission reason, or `include_in_migration: true` with a note.
PASS/FAIL with undecided content.

**Check 9 — Model and content counts match source**
The counts of connections, topics, views, folders, workbooks, and tiles in the audit tables match `connection_count`, `topic_count`, `view_count`, `folder_count`, `workbook_count`, and `tile_count` in status.md.
PASS/FAIL with mismatched counts.

### Step 3: Write validation report

Append a `## Validation` section to `audit/omni_audit.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  omni_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:omni-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:omni-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_audit` as artifact_id, `Omni Audit` as artifact_name, and the `file` value from `artifacts.omni_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_audit` as artifact, `validate` as action.

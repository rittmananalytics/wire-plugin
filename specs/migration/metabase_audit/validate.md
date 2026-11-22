---
wire_schema: "1.0"
command: validate
artifact: metabase_audit
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
  - artifact: metabase_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate Metabase audit completeness, warehouse dependency coverage, permission groups, and migration approach assignments

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Audit — Validate

## Purpose

Checks the Metabase audit for completeness and internal consistency: every card has a migration approach and complexity, warehouse dependencies are mapped with a coverage metric, permission groups are catalogued, database connections are recorded, and the card count matches the source. Produces a PASS/FAIL report with specific gaps to address before review.

## Prerequisites

- `audit/metabase_audit.md` exists (metabase_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/metabase_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, Card Catalog, Hierarchy, Database Connections, Permission Groups, Warehouse Dependency Map, Unresolved Cards, Excluded Cards).

### Step 2: Run validation checks

**Check 1 — All cards have a migration approach**
Every row in the card catalog has a value in `migration_approach` (repoint / rewrite_sql / rebuild / decommission).
PASS/FAIL with cards missing an approach.

**Check 2 — All cards have a complexity rating**
Every row has a `complexity` value (Low / Medium / High).
PASS/FAIL with cards missing complexity.

**Check 3 — Source objects resolved across query types, coverage reported**
Source-object resolution is attempted for both `native` and `mbql` cards. Each card with a resolvable source has ≥1 entry in `warehouse_objects`; each genuinely unresolvable card is marked `source_resolved: false` and listed under "Unresolved cards". The coverage metric (`resolved_card_count` / `active_card_count`) is present, and status.md carries `resolved_card_count`, `unresolved_card_count`, and `source_resolution_coverage_pct`.
PASS: resolution attempted for all query types, coverage present, every unresolved card listed.
FAIL: cards left blank without being listed, or coverage metric missing.

**Check 4 — dbt model cards cross-referenced**
Every card whose resolved source is a dbt model has a note confirming whether that model exists in the dbt audit (or is out of scope).
PASS/FAIL with cards missing the cross-reference.

**Check 5 — Permission groups catalogued**
The audit includes a permission group inventory listing each group and its database/collection access. `permission_group_count` in status.md is > 0 (or a note explains why the instance has none beyond defaults).
PASS/FAIL.

**Check 6 — Database connections recorded**
Every distinct `source_database_id` referenced by a card appears in the database connection inventory with its engine.
PASS/FAIL.

**Check 7 — Archived/unused cards have a decision**
Every archived or unused card has either `migration_approach: decommission` with a reason, or `include_in_migration: true` with a note.
PASS/FAIL with undecided cards. If `data_source: csv` and archived status is unavailable, auto-pass and note that decommission decisions need manual review with the client.

**Check 8 — Card count matches source**
The count of rows in the card catalog matches `card_count` in status.md.
PASS/FAIL.

**Check 9 — Reverse index complete (#184)**
Every card row carries its `dashboard_ids`, the shared-card count in status.md matches the cards appearing on more than one dashboard, and every dashboard's filter parameter mappings are catalogued. A missing reverse index makes every downstream card write unsafe (the edit-in-place vs clone decision has no input).
PASS/FAIL with the cards missing dashboard resolution.

**Check 10 — Query-type split and object graph (#184)**
Every card is classified `native` or `mbql` (`native_card_count + mbql_card_count = active_card_count`); every native card records its `template_tags` (with field ids), `snippets_used`, and `card_references` (empty lists are recorded, never omitted); the snippet inventory covers every snippet any card references.
PASS/FAIL with offending cards.

### Step 3: Write validation report

Append a `## Validation` section to `audit/metabase_audit.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  metabase_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:metabase-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:metabase-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_audit` as artifact_id, `Metabase Audit` as artifact_name, and the `file` value from `artifacts.metabase_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_audit` as artifact, `validate` as action.

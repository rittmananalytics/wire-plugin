---
wire_schema: "1.0"
command: validate
artifact: metabase_migration
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
  - artifact: metabase_migration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate Metabase migration runbook completeness — query inventory, SQL translations, permission remap, decoy validation, two-stage repoint with rollback

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Migration — Validate

## Purpose

Checks the Metabase migration runbook for completeness: the client query inventory is present, every in-scope card has migration steps, `rewrite_sql` cards have verified SQL diffs, permission groups are remapped, validation runs on a decoy collection against a frozen baseline, and the two-stage connection repoint has per-stage rollback. Produces a PASS/FAIL report.

## Prerequisites

- `migration/metabase_migration_runbook.md` exists

## Validation Checks

**Check 1 — Client query inventory present**
The runbook records that it ran against a client-supplied query inventory (approved audit catalog or client export), not inferred SQL. `query_inventory_source` in status.md is set.
PASS: inventory source recorded. FAIL: no client inventory — the command must not have proceeded.

**Check 2 — Topology recorded**
The runbook states the additive topology (target BigQuery connection added alongside Snowflake, decoy collection for validation) with rationale, and documents the build steps.
PASS/FAIL.

**Check 3 — All in-scope cards covered**
Every card with `include_in_migration: true` in the inventory has a section in the runbook.
PASS: all present. FAIL: list missing cards.

**Check 4 — rewrite_sql cards have SQL diffs**
Every `rewrite_sql` card includes a before/after SQL diff (source dialect → BigQuery).
PASS: all diffs present. FAIL: list cards missing a diff.

**Check 5 — Translated SQL verified on target**
Each `rewrite_sql` card documents the result of running the translated SQL on the target BigQuery connection (row count, result shape) against the frozen baseline.
PASS/FAIL with unverified translations.

**Check 6 — Rebuild plans documented**
Every `rebuild` card has a documented rebuild plan against the target connection.
PASS/FAIL.

**Check 7 — Permission groups remapped**
The runbook includes a permission-group remap table mapping each group's source permissions to target BigQuery connection + collection permissions, with the before/after permission graph captured for rollback.
PASS/FAIL.

**Check 8 — Validation is decoy-based against a frozen baseline**
Validation compares card results against a frozen source baseline and runs on the decoy collection / non-production connection only. No production card or dashboard is repointed to validate.
PASS: decoy-based against a baseline. FAIL: validation repoints production cards, or compares against moving production.

**Check 9 — Two-stage cutover with per-stage rollback**
The cutover is two stages — pilot repoint, then full production connection repoint from Snowflake to BigQuery — and each stage has an explicit rollback (revert the database connection details; revert the permission graph; restore card SQL from diffs).
PASS: both stages and both rollbacks documented. FAIL: single-stage cutover, or a stage missing its rollback.

**Check 10 — Source connection left live until cutover**
The runbook does not repoint or delete the production Snowflake connection during the migration phase — only at cutover. The Snowflake connection remains the rollback path through Stage 2.
PASS: connection repoint appears only in the cutover section. FAIL: production connection repointed/deleted in migration or validation steps.

**Check 11 — Card manifest gate holds (#184)**
`migration/metabase_card_manifest.csv` exists with one row per in-scope card; every applied change corresponds to a row whose `status` reached `signed_off` first; MBQL cards carry `action: repoint` with no proposed SQL; every shared card (per the audit reverse index) carries an explicit `edit_in_place`/`clone` decision.
PASS/FAIL with offending rows.

**Check 12 — Dependency order respected (#184)**
No card converted before a snippet it uses; no referencing card converted before its `{{#id}}` targets; every affected dashboard's filter parameter mappings and every field-filter template tag carry a target-database field-id remap.
PASS/FAIL with offending cards.

### Write validation report

Append a `## Validation` section to `migration/metabase_migration_runbook.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

Update status:
```yaml
artifacts:
  metabase_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:metabase-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact_id, `Metabase Migration` as artifact_name, and the `file` value from `artifacts.metabase_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_migration` as artifact, `validate` as action.

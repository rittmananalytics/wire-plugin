---
wire_schema: "1.0"
command: validate
artifact: omni_migration
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
  - artifact: omni_migration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate Omni migration runbook completeness — raw-SQL tile scope, view translations, branch validation, two-stage repoint with rollback

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Migration — Validate

## Purpose

Checks the Omni migration runbook for completeness: the raw-SQL tile count was reconfirmed live before translation, every in-scope view has migration steps, `rewrite_sql` views have verified SQL diffs, raw-SQL tile translations are documented and tested, validation runs on a model branch against a frozen baseline, and the two-stage connection cutover has per-stage rollback. Produces a PASS/FAIL report.

## Prerequisites

- `migration/omni_migration_runbook.md` exists

## Validation Checks

**Check 1 — Raw-SQL tile scope reconfirmed live**
The runbook records that the raw-SQL tile count was recounted live against the Omni instance and matched (or reconciled against) `omni_audit`'s `raw_sql_tile_count` before translation started. `raw_sql_tile_count_reconfirmed: true` is set in status.md.
PASS: reconfirmation recorded. FAIL: no reconfirmation, or a drift was found and not resolved by an audit re-run.

**Check 2 — Topology recorded**
The runbook states the additive topology (target connection added alongside source, model branch created for translation) with rationale, and documents the build steps.
PASS/FAIL.

**Check 3 — All in-scope views covered**
Every view with `include_in_migration` true (or not excluded) in the `omni_audit` catalog has a section in the runbook.
PASS: all present. FAIL: list missing views.

**Check 4 — rewrite_sql views have SQL diffs**
Every `rewrite_sql` view includes a before/after SQL diff (source dialect → target).
PASS: all diffs present. FAIL: list views missing a diff.

**Check 5 — Translated view SQL verified on the branch**
Each `rewrite_sql` view documents the result of running the translated SQL on the model branch against the target connection (row count, result shape) against the frozen baseline.
PASS/FAIL with unverified translations.

**Check 6 — Rebuild plans documented**
Every `rebuild` view has a documented rebuild plan against the target connection.
PASS/FAIL.

**Check 7 — Raw-SQL tile translations documented and tested**
Every raw-SQL tile with an approach other than `inherits_via_model` has a before/after SQL diff and a documented `omni-query` test result against the target connection, held as a pending edit for Stage 2.
PASS/FAIL with untested or undocumented tile translations.

**Check 8 — Validation is branch-based against a frozen baseline**
Validation runs on the model branch, scoped to a pilot/non-production connection scope, and compares results against a frozen source baseline. No production connection is repointed, and no production workbook/tile is edited, to validate.
PASS: branch-based against a baseline, scoped to pilot. FAIL: validation repoints the primary connection, edits production content, or compares against moving production.

**Check 9 — Two-stage cutover with per-stage rollback**
The cutover is two stages — Stage 1 branch validation on a pilot/non-production connection scope, Stage 2 branch promotion plus primary connection repoint (and raw-SQL tile edits) — and each stage has an explicit rollback (Stage 1: abandon/revert the branch; Stage 2: revert the connection details, revert the model to its pre-promotion state, restore raw-SQL tile SQL from diffs).
PASS: both stages and both rollbacks documented. FAIL: single-stage cutover, or a stage missing its rollback.

**Check 10 — Source connection left live until Stage 2**
The runbook does not repoint or delete the source connection during Step 1–6 (branch creation, translation, or Stage 1 validation) — only at Stage 2. The source connection remains the rollback path through Stage 2.
PASS: connection repoint appears only in the Stage 2 section. FAIL: source connection repointed/deleted before Stage 2.

### Write validation report

Append a `## Validation` section to `migration/omni_migration_runbook.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

Update status:
```yaml
artifacts:
  omni_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:omni-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact_id, `Omni Migration` as artifact_name, and the `file` value from `artifacts.omni_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_migration` as artifact, `validate` as action.

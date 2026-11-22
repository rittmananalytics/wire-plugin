---
wire_schema: "1.0"
command: validate
artifact: metabase_source_audit
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: report
    path: "audit/metabase_source_audit.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: metabase_source_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate the Metabase source audit: reproducible from the snapshot, every construct classified, IR valid, tables synced, secrets redacted"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Source Audit: Validate

## Purpose

> **Experimental.** The `metabase_to_looker` pair is experimental. It has run end to end once, on a Metabase Cloud trial instance: four BigQuery questions converted, deployed to Looker and matched row for row. It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Checks the Metabase source audit before the plan is built on it.

## Workflow

### Step 1: Run validation checks

**Check 1: Reproducible.** Re-run `mb_to_lookml.py audit` on the snapshot into a temporary folder; the two catalogs and `needs_human.json` must match byte for byte. PASS/FAIL.

**Check 2: Every construct classified.** Every row of `bi_model_catalog.csv` and `bi_content_catalog.csv` has a `translation_class`, and every content row that is not `mechanical` has a `reason`. PASS/FAIL.

**Check 3: IR valid.** `python3 <plugin-root>/scripts/bi_ir.py validate audit/ir` passes. PASS/FAIL.

**Check 4: Tables synced.** Every table a query-builder card reads has fields in the snapshot. A table with none was not synced in Metabase: FAIL, and name the table. PASS/FAIL.

**Check 5: Secrets redacted.** No database `details` value in `inventory.json` holds a password, key, token or service account: each such setting reads `[redacted]`. PASS/FAIL.

**Check 6: Snapshot pinned.** Every object in `inventory.json` has a SHA-256 and an `updated_at`. PASS/FAIL.

**Check 7: Counts match status.md.** PASS/FAIL.

### Step 2: Write the validation report

Append a `## Validation` section to `audit/metabase_source_audit.md` with the table and "Gaps to address".

### Step 3: Update status

```yaml
artifacts:
  metabase_source_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 4: Output next command

If PASS: `/wire:metabase-source-audit-review $ARGUMENTS`. If FAIL: fix the gaps and re-run `/wire:metabase-source-audit-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_source_audit` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_source_audit` as artifact_id, `Metabase Source Audit` as artifact_name, and the `file` value from `artifacts.metabase_source_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_source_audit` as artifact, `validate` as action.

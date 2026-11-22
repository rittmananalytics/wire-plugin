---
wire_schema: "1.0"
command: validate
artifact: tableau_audit
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
    path: "audit/tableau_audit.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: tableau_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate the Tableau audit: reproducible from the snapshot, every construct classified, every data source in one fingerprint group, IR valid, usage real or unknown"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Tableau Audit: Validate

## Purpose

> **Experimental.** The `tableau_to_looker` pair is experimental. It has run end to end once, on a Tableau Cloud trial site: one BigQuery sheet converted, deployed to Looker and matched row for row. It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Checks the Tableau audit before the plan is built on it.

## Workflow

### Step 1: Run validation checks

**Check 1: Reproducible.** Re-run `twb_to_lookml.py audit` on the snapshot into a temporary folder; the three catalogs must match byte for byte. PASS/FAIL.

**Check 2: Every construct classified.** Every row of `bi_model_catalog.csv` and every content row has a `translation_class`, and every non-`mechanical` row a `reason`. PASS/FAIL.

**Check 3: Every data source in one fingerprint group.** Every dataset row with relations appears in exactly one row of `datasource_fingerprints.csv`. PASS/FAIL.

**Check 4: IR valid.** `python3 <plugin-root>/scripts/bi_ir.py validate audit/ir` passes. PASS/FAIL.

**Check 5: Usage real or unknown.** Workbook rows carry Admin Insights or repository usage, REST all-time view counts (`views_total`, with `usage_source: rest_total_views`), or the literal `unknown` with `usage_source: unavailable`. PASS/FAIL.

**Check 6: Snapshot pinned.** Every object in `inventory.json` has a SHA-256, and an `updated_at` unless `snapshot_source: files`. PASS/FAIL.

**Check 7: Counts match status.md.** PASS/FAIL.

### Step 2: Write the validation report

Append a `## Validation` section to `audit/tableau_audit.md` with the table and "Gaps to address".

### Step 3: Update status

```yaml
artifacts:
  tableau_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 4: Output next command

If PASS: `/wire:tableau-audit-review $ARGUMENTS`. If FAIL: fix the gaps and re-run `/wire:tableau-audit-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `tableau_audit` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `tableau_audit` as artifact_id, `Tableau Audit` as artifact_name, and the `file` value from `artifacts.tableau_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `tableau_audit` as artifact, `validate` as action.

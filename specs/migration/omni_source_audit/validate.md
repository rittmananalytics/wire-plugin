---
wire_schema: "1.0"
command: validate
artifact: omni_source_audit
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
    path: "audit/omni_source_audit.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: omni_source_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate the Omni source audit: reproducible from the snapshot, every construct classified, IR valid, every tile's view in the snapshot, snapshot pinned"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Source Audit: Validate

## Purpose

> **Experimental.** The `omni_to_looker` pair is experimental. It has run end to end once, on Rittman Analytics' own Omni model on BigQuery: three dashboards converted, deployed to Looker and matched tile by tile (39 of 39). It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Checks the Omni source audit before the plan is built on it.

## Workflow

### Step 1: Run validation checks

**Check 1: Reproducible.** Re-run `omni_to_lookml.py audit` on the snapshot into a temporary folder; the two catalogs and `needs_human.json` must match byte for byte. PASS/FAIL.

**Check 2: Every construct classified.** Every row of `bi_model_catalog.csv` and `bi_content_catalog.csv` has a `translation_class`, and every content row that is not `mechanical` has a `reason`. PASS/FAIL.

**Check 3: IR valid.** `python3 <plugin-root>/scripts/bi_ir.py validate audit/ir` passes. PASS/FAIL.

**Check 4: Every tile's view in the snapshot.** Every view a dashboard tile queries is in the snapshot's `model/` folder, or the tile is listed in `needs_human.json` as on a workbook-only field. A view missing for another reason means the snapshot was cut short: FAIL, and name the view. PASS/FAIL.

**Check 5: Skipped documents explained.** Every entry under `skipped_documents` in `inventory.json` has a reason, and the report lists them. PASS/FAIL.

**Check 6: Snapshot pinned.** Every model file in `inventory.json` has a SHA-256, and every document a SHA-256 and an `updated_at`. PASS/FAIL.

**Check 7: Counts match status.md.** PASS/FAIL.

### Step 2: Write the validation report

Append a `## Validation` section to `audit/omni_source_audit.md` with the table and "Gaps to address".

### Step 3: Update status

```yaml
artifacts:
  omni_source_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 4: Output next command

If PASS: `/wire:omni-source-audit-review $ARGUMENTS`. If FAIL: fix the gaps and re-run `/wire:omni-source-audit-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_source_audit` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_source_audit` as artifact_id, `Omni Source Audit` as artifact_name, and the `file` value from `artifacts.omni_source_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_source_audit` as artifact, `validate` as action.

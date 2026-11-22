---
wire_schema: "1.0"
command: validate
artifact: lookml_model
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> validates one batch; --all validates every written batch"
produces:
  - type: report
    path: "migration/lookml_model/lookml_model.md"
    description: "Validation section appended: per-check PASS/FAIL for the batch"
preconditions:
  - artifact: lookml_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate one batch of the LookML model on the branch: lint passed, Looker's validator reports no errors, every in-scope field exists, one smoke query per explore returns rows"
argument-hint: <release-folder> [--batch <id> | --all]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# LookML Model: Validate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.


## Workflow

**Check 1: Lint passed** for the batch. PASS/FAIL.

**Check 2: Looker validator** (`validate_project` on the branch through the API or MCP): no errors in the batch's files. PASS/FAIL.

**Check 3: Every in-scope field exists**: every field with a `target` in the batch's IR is present in the validated model. PASS/FAIL.

**Check 4: Smoke query** per explore: one dimension and one measure through `run_inline_query` (or the Looker MCP `query` tool) with a limit of 10 returns rows. PASS/FAIL.

Append the results to `migration/lookml_model/lookml_model.md`, set `artifacts.lookml_model.validate: pass | fail`, and output `/wire:lookml-model-review $ARGUMENTS --batch <batch_id>` on PASS.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact_id, `LookML Model` as artifact_name, and the `file` value from `artifacts.lookml_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `lookml_model` as artifact, `validate` as action.

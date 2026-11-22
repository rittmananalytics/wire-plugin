---
wire_schema: "1.0"
command: validate
artifact: looker_content
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
      description: "--batch <id> validates one batch"
produces:
  - type: report
    path: "migration/looker_content/looker_content.md"
    description: "Validation section appended: per-check PASS/FAIL for the batch"
preconditions:
  - artifact: looker_content
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate a content batch: every referenced field exists on the branch through the Looker API, every dashboard file parses and validates, every filter listen resolves"
argument-hint: <release-folder> [--batch <id>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Content: Validate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.


## Workflow

**Check 1: Dashboards parse** as YAML and Looker's validator reports no dashboard errors on the branch. PASS/FAIL.

**Check 2: Every field exists**: every `fields`, `sorts`, filter `field` and `listen` value resolves to a field in the validated model (through the Looker API `lookml_model_explore`). PASS/FAIL.

**Check 3: Tile count**: each dashboard has the planned tiles, plus the hand-finish list. PASS/FAIL.

**Check 4: Every skipped tile has a reason**. PASS/FAIL.

Append the results to `migration/looker_content/looker_content.md`, set `artifacts.looker_content.validate: pass | fail`, and output `/wire:looker-content-review $ARGUMENTS --batch <batch_id>` on PASS.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_content` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_content` as artifact_id, `Looker Content` as artifact_name, and the `file` value from `artifacts.looker_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_content` as artifact, `validate` as action.

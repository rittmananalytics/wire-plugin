---
wire_schema: "1.0"
command: review
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
      description: "--batch <id> reviews one batch"
produces:
  - type: document
    path: "migration/lookml_model/lookml_model.md"
    description: "Review section appended with reviewer, date, decision and notes"
preconditions:
  - artifact: lookml_model
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Release director review of a translated LookML batch and its needs_human resolutions"
argument-hint: <release-folder> [--batch <id>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# LookML Model: Review

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

The release director reviews the batch: explore design, consolidated data sources, every join's relationship and primary key, and every needs_human resolution (LOD, table calculation, extract). Record the decision with reviewer and date in a `## Review` section of `migration/lookml_model/lookml_model.md`, set `artifacts.lookml_model.review`, and output `/wire:looker-content-generate $ARGUMENTS` when every model batch a content batch needs is approved.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact_id, `LookML Model` as artifact_name, and the `file` value from `artifacts.lookml_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `lookml_model` as artifact, `review` as action.

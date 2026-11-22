---
wire_schema: "1.0"
command: review
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
      description: "--batch <id> reviews one batch"
produces:
  - type: document
    path: "migration/looker_content/looker_content.md"
    description: "Review section appended with reviewer, date and decision"
preconditions:
  - artifact: looker_content
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Release director review of a migrated LookML dashboard batch"
argument-hint: <release-folder> [--batch <id>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Content: Review

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

The release director reviews the batch's dashboards side by side with the Tableau originals: layout, filters, the hand-finish list. Record the decision in a `## Review` section of `migration/looker_content/looker_content.md`, set `artifacts.looker_content.review`, and output `/wire:bi-equivalency-validate $ARGUMENTS --batch <batch_id>` when approved.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_content` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_content` as artifact_id, `Looker Content` as artifact_name, and the `file` value from `artifacts.looker_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_content` as artifact, `review` as action.

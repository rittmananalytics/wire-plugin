---
wire_schema: "1.0"
command: review
artifact: looker_target_setup
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
  - type: document
    path: "migration/looker_target_setup.md"
    description: "Review section appended with reviewer, date and decision"
preconditions:
  - artifact: looker_target_setup
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Internal RA review of the Looker target setup"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Target Setup: Review

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Internal RA review: the branch, connection and permission objects are right before LookML is written.

## Workflow

Present the setup document. Ask: is this the right connection and branch; do the groups and user attributes match the plan's permission map; is anything missing for row-level access. Record the decision (`approved` or `changes_requested`) with reviewer and date in a `## Review` section of `migration/looker_target_setup.md`, set `artifacts.looker_target_setup.review`, and output `/wire:lookml-model-generate $ARGUMENTS` when approved.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_target_setup` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_target_setup` as artifact_id, `Looker Target Setup` as artifact_name, and the `file` value from `artifacts.looker_target_setup` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_target_setup` as artifact, `review` as action.

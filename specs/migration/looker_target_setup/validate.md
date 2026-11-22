---
wire_schema: "1.0"
command: validate
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
  - type: report
    path: "migration/looker_target_setup.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: looker_target_setup
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate the Looker target: branch exists, connection reaches the warehouse, project validates clean on the branch, folders and groups exist"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Target Setup: Validate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Checks the Looker target before model batches are written.

## Workflow

**Check 1: Branch exists** in the LookML repo and is not the production branch. PASS/FAIL.

**Check 2: Connection works**: a `SELECT 1` through the Looker connection returns. PASS/FAIL.

**Check 3: Project validates** on the branch (`validate_project` through the API or MCP) with no new errors. PASS/FAIL.

**Check 4: Folders, groups, user attributes** in the setup document exist by id. PASS/FAIL.

Append a `## Validation` section to `migration/looker_target_setup.md`, set `artifacts.looker_target_setup.validate: pass | fail`, and output `/wire:looker-target-setup-review $ARGUMENTS` on PASS.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_target_setup` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_target_setup` as artifact_id, `Looker Target Setup` as artifact_name, and the `file` value from `artifacts.looker_target_setup` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_target_setup` as artifact, `validate` as action.

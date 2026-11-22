---
wire_schema: "1.0"
command: generate
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
mcp_contextual:
  - looker
produces:
  - type: document
    path: "migration/looker_target_setup.md"
    description: "What was verified and created for the Looker target: project, git branch, connection, model set, folders, groups and user attributes"
preconditions:
  - artifact: bi_migration_plan
    action: review
    outcome: approved
auto_validate: false
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Prepare the Looker target (SAFETY GATE, writes to the client's Looker repo on a branch and to the Looker instance): verify the connection, create the LookML branch, folders, groups and user attributes from the plan"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: looker_target_setup` and `artifact_file_path: migration/looker_target_setup.md` before proceeding.

---

# Looker Target Setup: Generate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Prepares the Looker side before any LookML is written: the LookML project and its git repository, a migration branch, the warehouse connection, and the folders, groups and user attributes the plan's permission map needs.

```
⚠️  DATA SAFETY REMINDER
LookML is written only to the migration branch named in bi_migration.target.branch, never
to the production branch. This command never merges. Merging is a release director ruling
at cutover. Folders, groups and user attributes are created, never deleted or renamed.
```

## Prerequisites

- `bi_migration_plan review: approved`
- `bi_migration.target`: `base_url`, `project`, and the LookML repo registered with `/wire:migration-source-register $ARGUMENTS lookml <url>` and a `client_repos` entry with role `bi_target_model`
- Looker API credentials (`LOOKERSDK_*`) or the Looker MCP

## Pair: metabase_to_looker

The workflow applies with these differences. **Step 1:** the connection must reach the databases the Metabase content reads (each database's engine and project from the audit's `inventory.json`); one LookML model serves one connection, so a Metabase instance with content on two warehouses needs two models. **Step 2:** the default branch is `wire/metabase-migration`. **Step 3:** Looker folders follow the Metabase collections in scope, and groups follow the Metabase permission groups in the plan's map.

## Pair: looker_studio_to_looker

The workflow applies with these differences. **Step 1:** the connection must reach the BigQuery projects the data sources read (`connection.project` in `report.json`); a data source on Looker Studio's Looker connector names its Looker instance, model and explore, and needs no connection of its own, only that the instance is the target. **Step 2:** the default branch is `wire/looker-studio-migration`.

## Pair: omni_to_looker

The workflow applies with these differences. **Step 1:** the connection must reach the warehouse the Omni connection reads (dialect and project in the snapshot's `inventory.json`, `model`); one Omni shared model maps to one LookML model. **Step 2:** the default branch is `wire/omni-migration`. **Step 3:** Looker folders follow the Omni folders in scope; user attributes are those the topics' access filters name.

## Workflow

### Step 1: Verify the connection

Through the Looker API or MCP, confirm the connection named in the plan exists and can reach the warehouse the Tableau data sources read (`connection.project` and `schema` from the audit). Record it.

### Step 2: Create the branch

Create `bi_migration.target.branch` (default `wire/tableau-migration`) from the production branch in the LookML repo, and write it to `status.md`. Add `views/`, `models/` and `dashboards/` folders if absent.

### Step 3: Folders, groups and user attributes

Create the Looker folders for the Tableau projects in scope, and the groups and user attributes in the plan's permission map. Record every object created with its Looker id.

### Step 4: Write the setup document and update status

Write `migration/looker_target_setup.md` (connection, branch and commit, objects created) and:

```yaml
artifacts:
  looker_target_setup:
    generate: complete
    file: migration/looker_target_setup.md
    generated_date: "{{TODAY}}"
    experimental: true
```

Then output `/wire:looker-target-setup-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_target_setup` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_target_setup` as artifact_id, `Looker Target Setup` as artifact_name, and the `file` value from `artifacts.looker_target_setup` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_target_setup` as artifact, `generate` as action.

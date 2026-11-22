---
wire_schema: "1.0"
command: generate
artifact: omni_target_setup
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
    path: "migration/omni_target_setup.md"
    description: "What was verified and created on the Omni instance: connection, model, branch, schema refresh, groups and user attributes"
preconditions:
  - artifact: bi_migration_plan
    action: review
    outcome: approved
auto_validate: false
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Prepare the Omni target (SAFETY GATE, writes to a live Omni instance): verify the connection, create the model branch, refresh the schema, create groups and user attributes from the plan"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_target_setup` and `artifact_file_path: migration/omni_target_setup.md` before proceeding.

---

## Data Safety: Read Before Proceeding

This command writes to a live Omni instance. What it writes is limited to: one model branch, groups and user attributes named in the approved plan's permission map. It never edits the production model, never merges a branch, never publishes or edits a document, and never changes the connection. If the Omni CLI profile in use has write access to production model YAML, that is expected (branch creation needs it), but nothing in this command uses it outside the branch. Every write is listed in the output document so it can be reversed by hand.

---

# Omni Target Setup: Generate

## Purpose

Makes the Omni instance ready for model and content migration, and proves the assumptions the rest of the release relies on: the Omni connection reads the same warehouse Looker reads, the model exists and its schema is current, a branch exists for all model writes, and the groups and user attributes the permission map needs exist before any content is published. It is the BI-migration counterpart of `target_setup` in a warehouse migration, with far less to create because the warehouse does not move.

## Prerequisites

- `bi_migration_plan review: approved`
- Omni CLI installed and a profile configured for the target instance (`skills/omni/SKILL.md` Step 0), with permission to create model branches, groups and user attributes
- `bi_migration.omni_model_id` set in `status.md`

## Inputs

- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (permission map, topic architecture)
- `.wire/releases/$ARGUMENTS/status.md` (`bi_migration.omni_base_url`, `omni_model_id`, `looker_base_url`)
- `.wire/releases/$ARGUMENTS/audit/looker_audit.md` (the warehouse connection Looker uses, from its model files' `connection:` value)
- The Omni instance, via the Omni CLI

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. In Step 2, compare the Omni connection with the warehouse the source tool reads: the BigQuery project or Snowflake account and the datasets in `audit/bi_model_catalog.csv` (Tableau data source connections, or the Metabase database's details) in place of Looker's `connection:`. In Step 3, list the existing view and topic names, and record the plan's view prefix; a converter name that already exists on the model is a parked decision, as for Looker views.

## Workflow

### Step 1: Confirm CLI access

```
omni config show
omni whoami whoami
```

If no profile is configured, stop and output the same message as `specs/migration/omni_audit/generate.md` Step 2, with the re-run command `/wire:omni-target-setup-generate $ARGUMENTS`. There is no offline mode for this command.

### Step 2: Verify the connection

Read the model's connection through the CLI (`omni models get <modelId>` and the connection it names). Compare the warehouse, project or account, and default database or dataset with the connection Looker's model files declare (the audit records it). They must be the same warehouse. If they are not, stop:

```
The Omni model's connection does not read the same warehouse as the Looker model.
  Looker connection: <name> -> <warehouse/project/dataset>
  Omni connection:   <name> -> <warehouse/project/dataset>
A bi_migration release assumes the warehouse does not move. Point the Omni connection
at the Looker warehouse (or use platform_migration first), then re-run.
```

Record `connection_verified: true` only when they match.

### Step 3: Record the model and its state

Record `bi_migration.omni_model_id` and whether the model is git-connected (`omni models get` reports the repository and base branch). A git-connected model merges through `omni models commit` and a PR in the client's repo; a non-git model merges through `omni models merge-branch`. The later `omni_model` review needs to know which.

If `omni_audit` was run (brownfield target), list the existing topics and views by name so `omni_model` can avoid overwriting them. A name collision between an existing Omni view and a Looker view to be migrated is a parked decision for the director (`kind: ruling`): rename the incoming view, extend the existing one, or replace it.

### Step 4: Create the model branch

```
omni models create-branch <modelId> --name "wire-<release_folder>"
```

Record the branch id and name in `bi_migration.omni_branch`. If a branch of that name already exists (a re-run), reuse it and record that. All model writes in this release go to this branch. Nothing merges without a ruling recorded at `omni-model-review`.

### Step 5: Refresh the schema

```
omni models refresh <modelId>
```

The refresh runs against the connection, not the branch, so the branch sees current tables and columns. Record the refresh time. Without it, plain column dimensions the converter emits by name will not resolve on the branch.

### Step 6: Create groups and user attributes

From the plan's permission map, for each row:

- **Group**: create the Omni group if it does not exist (`omni-admin` skill). Record created or existing.
- **User attribute**: create the attribute with the type the map specifies, and the default value. Record created or existing.
- **Access grant**: note the grant name the topic YAML will reference (`required_access_grants`, `access_filters`). Grants are declared in model YAML by `omni_model`, not created here.

Do not add users to groups. Membership is a cutover step, group by group, so nobody sees Omni content before parity is proven.

### Step 6b: Derive the dashboard theme

Derive one dashboard theme JSON from the client's brand (key colour, background, tile border radius, fonts) so every migrated document styles consistently from its first draft. The theme property vocabulary and six worked examples are in `wire/bi_pairs/looker_to_omni/omni_patterns.md`, section "Dashboard themes". Write the JSON to `.wire/releases/$ARGUMENTS/migration/omni_dashboard_theme.json` and note in the setup document that it is imported per dashboard through the editor's Import button (there is no instance-wide theme API surface; confirm against the instance before promising otherwise). Where the plan already carries a theme ruling, apply it instead of deriving one. Per-dashboard visual fidelity beyond the theme stays in the content batches' `hand_finish` list.

### Step 7: Write the setup document

**Output location**: `.wire/releases/$ARGUMENTS/migration/omni_target_setup.md`

Include: CLI profile and instance URL; connection verification (both sides, match confirmed); model id and git-connection state; branch id and name; schema refresh time and table count; groups and user attributes (created, existing); name collisions parked; the derived dashboard theme (or the plan's ruling); every write made, in order, with the reversing action.

### Step 8: Update status

```yaml
bi_migration:
  omni_branch: "<branch id>"
artifacts:
  omni_target_setup:
    generate: complete
    file: migration/omni_target_setup.md
    generated_date: "{{TODAY}}"
    connection_verified: true
    schema_refreshed: true
    branch_created: true
    groups_created: N
    user_attributes_created: N
    model_git_connected: true | false
    generated_files:
      - migration/omni_target_setup.md
```

### Step 9: Output summary and safety reminder

Print what was verified and created, and:

```
Validate did not run automatically (it queries the Omni instance). Run it now:
/wire:omni-target-setup-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_target_setup.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_target_setup` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_target_setup` as artifact_id, `Omni Target Setup` as artifact_name, and the `file` value from `artifacts.omni_target_setup` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_target_setup` as artifact, `generate` as action.

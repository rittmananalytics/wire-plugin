---
wire_schema: "1.0"
command: validate
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
  - type: report
    path: "migration/omni_target_setup.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: omni_target_setup
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Validate the Omni target against the live instance: branch exists, model validates with no blocking issue, schema is fresh, groups and user attributes exist"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Target Setup: Validate

## Purpose

Confirms against the live Omni instance that what the setup document claims is true. This validate queries Omni through the CLI, which is why generate does not run it automatically. Produces a PASS/FAIL report.

## Prerequisites

- `migration/omni_target_setup.md` exists (omni_target_setup generate: complete)
- Omni CLI profile configured

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_target_setup.md`
- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (permission map)
- `.wire/releases/$ARGUMENTS/status.md`
- The Omni instance, via the Omni CLI

## Workflow

### Step 1: Load the setup document

Read the document and `status.md`. Confirm `bi_migration.omni_branch` is set.

### Step 2: Run validation checks

**Check 1: Branch exists**
`omni models get <modelId>` lists a branch whose id equals `bi_migration.omni_branch`.
PASS/FAIL.

**Check 2: Model validates on the branch**
`omni models validate <modelId> --branch-id <branch>` returns no issue with `is_warning: false`. Warnings are listed, not failed.
PASS/FAIL with the blocking issues.

**Check 3: Schema is fresh**
The model's last schema refresh is on or after the `schema refresh time` recorded in the setup document, and every schema the Looker model's `sql_table_name` values reference appears in the refreshed schema list.
PASS/FAIL with the missing schemas.

**Check 4: Groups exist**
Every Omni group named in the permission map exists on the instance.
PASS/FAIL with the missing groups.

**Check 5: User attributes exist**
Every user attribute named in the permission map exists with the type the map specifies.
PASS/FAIL.

**Check 6: No users were added**
No group named in the permission map gained members between the setup document's time and now, unless the setup document records that membership was pre-existing. Membership is a cutover step.
PASS/FAIL.

**Check 7: Connection unchanged**
The model's connection still matches the one recorded as verified.
PASS/FAIL.

### Step 3: Write validation report

Append a `## Validation` section to `migration/omni_target_setup.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  omni_target_setup:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:omni-target-setup-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:omni-target-setup-validate $ARGUMENTS
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/migration/omni_target_setup.md` (Validation section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_target_setup` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_target_setup` as artifact_id, `Omni Target Setup` as artifact_name, and the `file` value from `artifacts.omni_target_setup` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_target_setup` as artifact, `validate` as action.

---
wire_schema: "1.0"
command: review
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
    description: "Review section appended with reviewer, date, decision and notes"
preconditions:
  - artifact: omni_target_setup
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Internal RA sign-off that the Omni target is ready for model migration"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Target Setup: Review

## Purpose

Internal RA sign-off before any model YAML is written to the Omni branch. Short by design: the validate has already checked the instance. The reviewer confirms the branch and permission objects are the ones the plan asked for and that any name collision with existing Omni content has a ruling.

## Prerequisites

- `migration/omni_target_setup.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_target_setup.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Present the setup for review

Display: instance and profile; connection verification; model id and git-connection state; branch; schema refresh; groups and user attributes created or found; parked name collisions.

### Step 2: Gather reviewer feedback

1. Is this the right model and branch? (A wrong model id here puts every later write in the wrong place.)
2. Are the groups and user attributes the ones the client will administer, with names they will recognise?
3. Do any name collisions with existing Omni content still need a ruling before the first model batch?

### Step 3: Apply feedback and record decision

Record any ruling on name collisions in `decisions.md` (format per `specs/utils/director_operating_model.md`), then:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Comments, corrections, follow-up actions]
```

### Step 4: Update status

```yaml
artifacts:
  omni_target_setup:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved:
```
/wire:omni-model-generate $ARGUMENTS --batch b01
```

If changes requested:
```
Apply the corrections, then re-run:
/wire:omni-target-setup-validate $ARGUMENTS
```

## Review Gate

Approval confirms the branch, model and permission objects are correct. Model migration writes only to the approved branch from this point.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/migration/omni_target_setup.md` (Review section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_target_setup` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_target_setup` as artifact_id, `Omni Target Setup` as artifact_name, and the `file` value from `artifacts.omni_target_setup` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_target_setup` as artifact, `review` as action.

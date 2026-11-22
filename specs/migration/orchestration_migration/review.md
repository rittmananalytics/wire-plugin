---
wire_schema: "1.0"
command: review
artifact: orchestration_migration
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: orchestration_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Safety-gated approval before activating jobs on target
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Migration — Review

## Purpose

Safety-gated review before orchestration jobs are created and activated on the target platform.

## Flags

- `--wave <id>` — review the wave-labelled runbook (`orchestration_migration_runbook_{wave_id}.md`) instead of the unscoped one. Required once more than one wave's runbook exists.

## SAFETY GATE

```
⚠️  SAFETY GATE — Orchestration Job Activation

The following actions will be authorised by approving this review:
  - N orchestration jobs will be created on the TARGET platform
  - Jobs will initially run in manual-trigger mode (not scheduled)
  - Source jobs continue to run unchanged during parallel run

Please confirm:
[ ] I have reviewed the orchestration migration runbook
[ ] Target platform connection credentials are in place
[ ] The parallel-run period is understood and agreed
[ ] Critical job fallback procedures are in place
[ ] Job scheduling will not be activated until equivalency validation passes
```

Wait for explicit confirmation of all items.

## Workflow

### Step 1: Present runbook summary

Display: job count, critical job list, connection changes required.

### Step 2: Safety gate confirmation

Present checklist. Wait for confirmation.

### Step 3: Record decision

Append review block with safety gate confirmation.

### Step 4: Update status

```yaml
artifacts:
  orchestration_migration:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    wave_review:                 # set only when run with --wave, keyed by wave id
      B01: approved | changes_requested
```

### Step 5: Output next command

If approved:
```
/wire:equivalency-validate $ARGUMENTS
```

---
wire_schema: "1.0"
command: review
artifact: ingestion_migration
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
  - artifact: ingestion_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Safety-gated approval before activating Fivetran to target
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Ingestion Migration — Review

## Purpose

Safety-gated review before Fivetran connectors are activated to the target platform. Approval authorises the migration team to begin the parallel-run phase.

## Flags

- `--wave <id>` — review the wave-labelled runbook (`ingestion_migration_runbook_{wave_id}.md`) instead of the unscoped one. Required once more than one wave's runbook exists; without it, review the single unscoped runbook as today.

## Prerequisites

- `migration/ingestion_migration_runbook.md` (or `_{wave_id}.md` under `--wave`) with `validate: pass`

## SAFETY GATE

```
⚠️  SAFETY GATE — Fivetran Connector Activation

The following actions will be authorised by approving this review:
  - N Fivetran connectors will be activated to write to the TARGET platform
  - Source connectors remain active (parallel run — no data loss risk)
  - Initial syncs will consume Fivetran MAR (rows synced count)

Please confirm:
[ ] I have reviewed the ingestion migration runbook
[ ] Target platform schemas exist and have been verified
[ ] Target platform credentials for Fivetran are in place
[ ] I understand this will consume Fivetran MAR for the initial sync
[ ] The parallel-run period is agreed (source and target running simultaneously)
```

Wait for explicit confirmation of all items.

## Workflow

### Step 1: Present runbook summary

Display: connector count by complexity, estimated initial sync duration, credential rotation items.

### Step 2: Safety gate confirmation

Present the checklist. Wait for confirmation.

### Step 3: Record decision

Append review block with safety gate confirmation.

### Step 4: Update status

```yaml
artifacts:
  ingestion_migration:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    wave_review:                 # set only when run with --wave, keyed by wave id
      B01: approved | changes_requested
```

### Step 5: Output next command

If approved:
```
/wire:dbt-migration-generate $ARGUMENTS
```

---
wire_schema: "1.0"
command: review
artifact: cutover
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: cutover
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Safety-gated sign-off before live cutover

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Cutover — Review

## Purpose

Final safety-gated sign-off authorising live production cutover. This is the highest-stakes gate in the migration workflow. Both RA and the client must explicitly confirm before execution begins.

## Prerequisites

- `migration/cutover_runbook.md` with `validate: pass`

## SAFETY GATE

```
⚠️  SAFETY GATE — PRODUCTION CUTOVER (POINT OF NO RETURN)

This review authorises execution of the production cutover runbook.

Once the maintenance window begins:
  - All production workloads will be redirected to the TARGET platform
  - Source Fivetran connectors will be paused / archived
  - Source platform will no longer be the production system
  - Rollback is possible only within the agreed time window ([time from runbook])

This action CANNOT be undone after the rollback window closes.

Please confirm (ALL items required):
[ ] All equivalency checks are passing (or accepted differences are formally agreed)
[ ] The maintenance window has been communicated to all users
[ ] Client executive sponsor has given verbal/written authorisation
[ ] RA engagement lead has signed off
[ ] The rollback procedure is understood by the on-call team
[ ] A rollback decision owner is nominated (name: _______________)
[ ] Post-cutover monitoring plan is in place
[ ] Business-critical reporting periods have been avoided (no month-end, quarter-end, etc.)
```

Wait for explicit confirmation of ALL items. A single unchecked item stops the process.

## Workflow

### Step 1: Present the runbook

Display the full cutover runbook summary: sequence, timings, rollback window.

### Step 2: Confirm acceptance

Present the safety gate checklist. Ask for the rollback decision owner name explicitly.

### Step 3: Record decision with dual sign-off

```markdown
## Review

**RA sign-off**: {{RA_LEAD}}
**Client sign-off**: {{CLIENT_SPONSOR}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Safety gate confirmation
All checklist items confirmed.
Rollback decision owner: {{ROLLBACK_OWNER}}

### Accepted differences
[List any known equivalency differences accepted by client]
```

### Step 4: Update status

```yaml
artifacts:
  cutover:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved:
```
Cutover is authorised. Execute the runbook during the agreed maintenance window.

After cutover is complete:
/wire:migration-report-generate $ARGUMENTS
```

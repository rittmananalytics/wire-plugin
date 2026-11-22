---
wire_schema: "1.0"
command: review
artifact: bulk_copy_migration
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
  - artifact: bulk_copy_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Safety-gated approval before the first tenant bulk-copy execution
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Bulk Copy Migration — Review

## Purpose

Safety-gated review before any data is copied from Snowflake to BigQuery. Approval authorises the migration team to execute the **first copy** — the Stage 1 pilot partition. This is the point at which a misconfigured copy could touch the wrong tenant's data, so it requires explicit written approval.

## Flags

- `--wave <id>` — review the wave-labelled runbook (`bulk_copy_migration_runbook_{wave_id}.md`) instead of the unscoped one. Required once more than one wave's runbook exists. Approving a wave's review authorises only that wave's Stage 1 pilot-partition copy — each wave gets its own safety-gate approval.

## Prerequisites

- `migration/bulk_copy_migration_runbook.md` (or `_{wave_id}.md` under `--wave`) with `validate: pass`
- `migration.scope == tenant_carveout`

## SAFETY GATE

```
⚠️  SAFETY GATE — First Tenant Bulk-Copy Execution

Approving this review authorises the migration team to execute the Stage 1
pilot-partition copy from Snowflake to BigQuery for ONE tenant.

  - Source (Snowflake) stays READ ONLY and live — no decommission yet
  - Every extract is filtered by migration.tenant_predicate: [tenant_predicate]
  - Writes land only in: [migration.target_project] / [dataset]
  - The copy runs under a scoped service account, not an admin credential
  - Stage 2 (remainder) runs only after the equivalency gate passes

Please confirm ALL of:
[ ] I have reviewed the bulk copy runbook
[ ] migration.tenant_predicate is correct and scopes exactly the intended tenant
[ ] The scoped service account is in place and has access ONLY to the target
    tenant's project/dataset (and dedicated staging bucket, GCS-staged path)
[ ] The destination is the designated target project — NOT a production project
[ ] Target schemas exist and have been verified
[ ] The two-stage gate is understood: pilot partition → equivalency checks 1 and 6
    → remainder, with Stage 2 blocked until the gate passes
[ ] The source remains live; decommission is deferred to cutover
```

Wait for explicit confirmation of all items. If any box is unchecked, stop:

```
Safety gate not cleared. Address the unchecked items and re-run:
/wire:bulk-copy-migration-review $ARGUMENTS
```

## Workflow

### Step 1: Present runbook summary

Display: copy mechanism (BQ Data Transfer Service / GCS-staged), tables in scope, tenant predicate, scoped service account identity, target destination, and the pilot-partition chosen for Stage 1.

### Step 2: Safety gate confirmation

Present the checklist. Wait for confirmation of every item.

### Step 3: Record decision

Append a review block to the runbook recording the decision, the reviewer, and the date, with the safety-gate confirmation:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Safety gate confirmation
All checklist items confirmed by: {{REVIEWER_NAME}}
First copy execution authorised: Stage 1 pilot partition only.
```

### Step 4: Update status

```yaml
artifacts:
  bulk_copy_migration:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    wave_review:                 # set only when run with --wave, keyed by wave id
      B01: approved | changes_requested
```

### Step 5: Output next command

If approved, run the equivalency gate after the pilot partition copy, then continue to the dbt migration:
```
/wire:equivalency-validate $ARGUMENTS
/wire:dbt-migration-generate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact_id, `Bulk Copy Migration` as artifact_name, and the `file` value from `artifacts.bulk_copy_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bulk_copy_migration` as artifact, `review` as action.

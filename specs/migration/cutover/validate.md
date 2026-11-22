---
wire_schema: "1.0"
command: validate
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate cutover runbook completeness

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Cutover — Validate

## Validation Checks

**Check 1 — Pre-cutover checklist present**
The runbook includes a pre-cutover checklist with all required items.
PASS/FAIL.

**Check 2 — Timed sequence covers all workload types**
The cutover sequence includes steps for: Fivetran connectors, dbt/orchestration jobs, and BI tool connections.
PASS/FAIL with missing steps listed.

**Check 3 — Rollback procedure present**
The runbook includes a full rollback procedure with a time limit, a decision tree (data loss → immediate; perf regression → evaluate; minor discrepancy → fix forward), and a rollback window with a scheduled source decommission step.
PASS: Rollback procedure present with time limit, decision tree, and rollback window/decommission.
FAIL: Rollback missing, or missing the time limit, decision tree, or rollback window.

**Check 4 — Communication templates present**
The runbook includes notification templates for: maintenance window announcement and go-live announcement.
PASS/FAIL.

**Check 5 — Post-cutover monitoring checklist present**
The runbook includes a post-cutover monitoring checklist.
PASS/FAIL.

**Check 6 — Accepted differences documented**
If any objects have `accepted_difference` status, the runbook documents these explicitly so stakeholders are aware.
PASS: All accepted differences noted, or none exist.
FAIL: Accepted differences in status.md not reflected in runbook.

**Check 7 — Go/no-go decision point specified**
The runbook specifies a clear go/no-go decision point (time after maintenance window start).
PASS/FAIL.

**Check 8 — Cutover rehearsal recorded**
The pre-cutover checklist confirms a full cutover rehearsal was completed on staging at production scale, with step timings fed into the sequence.
PASS: Rehearsal item present and checked.
FAIL: No rehearsal recorded.

### Update status

```yaml
artifacts:
  cutover:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `cutover` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `cutover` as artifact_id, `Cutover Runbook` as artifact_name, and the `file` value from `artifacts.cutover` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `cutover` as artifact, `validate` as action.

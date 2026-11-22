---
wire_schema: "1.0"
command: review
artifact: logical_access_uat
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
  - artifact: logical_access_uat
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Execute and sign off region-scoped logical-access UAT — the isolation-proof gate before cutover

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Logical-Access UAT — Review

## Purpose

The sign-off gate where logical-access UAT is executed (or witnessed) and the evidence pack is completed. Approval is the written attestation that the tenant carve-out's access boundaries hold: users in the tenant's project reach only that project and see no other tenant's data. This gate sits before cutover — a failed or unsigned UAT blocks it.

## Prerequisites

- `migration/logical_access_uat_plan.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to surface any Fathom recordings touching data-residency, tenant isolation, or security sign-off requirements.

### Step 2: Execute the test matrix and capture evidence

Run each test (or witness the tester run it). For every test ID, fill the evidence block in the plan: actual result, evidence reference (query output, error text, masked value, or screenshot), PASS/FAIL, tester, date.

Pay special attention to the negative tests — each must produce a hard denial, zero cross-tenant rows, or a masked value. A negative test that returns another tenant's data is a **fail** and blocks sign-off regardless of how many positive tests pass.

### Step 3: Record outcomes and complete sign-off

Update the evidence blocks, then complete the sign-off block:

```markdown
## Sign-off
- All positive tests passed: ☑ / ☐
- At least one negative test passed per IAM boundary: ☑ / ☐
- No cross-tenant data was reachable in any negative test: ☑ / ☐

**Signed off by**: {{REVIEWER_NAME}}   **Role**: {{ROLE}}   **Date**: {{TODAY}}
**Decision**: approved | changes_requested
```

Approve only when all three attestations are checked. If any negative test failed, record `changes_requested`, note the boundary that leaked, and route back to `/wire:target-setup-generate` / `/wire:target-setup-review` to fix the IAM boundary before re-testing.

### Step 4: Update status

```yaml
artifacts:
  logical_access_uat:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved:
```
/wire:cutover-generate $ARGUMENTS
```

## Review Gate

This review proves tenant isolation. Cutover must not proceed until logical-access UAT is `approved` with every negative test passing. Re-running the security DDL after sign-off invalidates the attestation and requires re-execution of the affected tests.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact_id, `Logical-Access UAT` as artifact_name, and the `file` value from `artifacts.logical_access_uat` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `logical_access_uat` as artifact, `review` as action.

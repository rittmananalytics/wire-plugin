---
wire_schema: "1.0"
command: validate
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate logical-access UAT — at least one negative test per IAM boundary, positive + negative per role

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Logical-Access UAT — Validate

## Validation Checks

Read `migration/logical_access_uat_plan.md`, `migration/target_setup_scripts/04_security.sql`, and `migration/migration_strategy.md`. Confirm `migration.scope == tenant_carveout`.

**Check 1 — Every IAM boundary has at least one negative test**
Enumerate the IAM boundaries defined in `04_security.sql` (tenant-scoped grants, RLS predicate, scoped service account, column masking, shared-role behaviour). For each boundary, confirm the plan contains **at least one negative test**.
PASS: every boundary has ≥1 negative test.
FAIL: list each boundary with no negative test. This is the gating check — a boundary tested only positively is not proven.

**Check 2 — Every role has both a positive and a negative test**
Each role named in the boundaries has at least one positive and at least one negative test.
PASS/FAIL with roles missing either type.

**Check 3 — Negative tests assert a hard outcome**
Every negative test's expected result is one of: access denied / permission error, zero rows from another tenant, or a masked value — not a soft pass.
PASS/FAIL with offending tests.

**Check 4 — All boundaries from 04_security.sql are covered**
No boundary in `04_security.sql` is absent from the test matrix. Cross-check the boundary list against the plan.
PASS/FAIL with uncovered boundaries.

**Check 5 — Evidence template present and complete**
Each test ID has an evidence block with the required fields (boundary, role, type, action, expected, actual, evidence ref, result, tester, date).
PASS/FAIL.

**Check 6 — Sign-off block present**
The plan contains the written sign-off block with the three attestations and a signature line.
PASS/FAIL.

**Check 7 — Scope and region recorded**
`migration.scope == tenant_carveout` and the target region under test are recorded in the plan and status.
PASS/FAIL.

### Update status

```yaml
artifacts:
  logical_access_uat:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact_id, `Logical-Access UAT` as artifact_name, and the `file` value from `artifacts.logical_access_uat` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `logical_access_uat` as artifact, `validate` as action.

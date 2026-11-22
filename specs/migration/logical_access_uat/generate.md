---
wire_schema: "1.0"
command: generate
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
  - artifact: target_setup
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate a region-scoped logical-access UAT plan and evidence pack for a tenant carve-out

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: logical_access_uat` and `artifact_file_path: migration/logical_access_uat_plan.md` before proceeding.

---

# Logical-Access UAT — Generate

## Purpose

Generates the UAT test plan and evidence pack that proves the tenant carve-out's access boundaries hold: users in the extracted tenant's target project reach **only** that project and see **no other tenant's data**. The plan derives its tests directly from the IAM boundaries written in the target_setup security work (`04_security.sql`) — tenant-scoped GRANTs, the row-level security predicate on the tenant key, the scoped service account, and the PII policy-tag taxonomy.

Every boundary gets **both** a positive test (the authorised role can do what it should) and at least one **negative** test (the role cannot reach another tenant's data or another project). The artifact is a runnable plan plus an evidence template to capture results, with a written sign-off block completed at review.

This command runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`).

## Parameters

- `$ARGUMENTS` — the release folder.
- `--region <code>` — the target region under test. **Default: `de`** (matches `region-tagging`).

## Prerequisites

- `migration.scope == tenant_carveout` in status.md
- `target_setup review: approved` — the security DDL (`04_security.sql`) must be approved, since its boundaries are what UAT proves

If `scope` is not `tenant_carveout`, stop: "Logical-access UAT runs in tenant carve-out scope only." If `target_setup` is not approved, stop and point to `/wire:target-setup-review`.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql` — the source of truth for IAM boundaries (tenant-scoped GRANTs, RLS predicate, scoped service account, policy-tag masking)
- `.wire/releases/$ARGUMENTS/audit/security_audit.md` — tenant_scoped vs shared role classification, tenant-key flags per table
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md` — the two-project / tenant-scoped IAM model and RLS predicate definition
- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`, target project

## Workflow

### Step 1: Enumerate the IAM boundaries

Parse `04_security.sql` (cross-referenced with the migration strategy security section) and list every access boundary it establishes. Typical boundaries:

- **Tenant-scoped role grants** — each `tenant_scoped` role is granted only on the tenant's target project/dataset; it must not reach any other project.
- **Row-level security** — the RLS predicate on the tenant key restricts shared tables to the tenant's rows.
- **Scoped service account** — the copy/runtime service account has access only to the tenant's project (and dedicated staging bucket).
- **Column masking** — PII policy tags mask sensitive columns for non-privileged roles.
- **Shared roles** — platform-wide roles behave as designed without leaking cross-tenant.

Each boundary is a testable assertion. Record it with the role(s) it governs and the resource it scopes.

### Step 2: Derive positive and negative tests per role

For every boundary × role, define:

- **Positive test** — the authorised action succeeds. E.g. "role `tenant_de_analyst` queries `<target_project>.analytics.orders` and receives rows."
- **Negative test (at least one per boundary)** — the prohibited action is denied or returns no other-tenant data. E.g. "role `tenant_de_analyst` queries another tenant's project → permission denied"; "the same role queries a shared table without the RLS context → returns only `de` rows, zero rows for any other market"; "a non-privileged role selects a PII column → value is masked."

Negative tests must assert one of: **access denied**, **zero rows from another tenant**, or **masked value** — never a soft "should be fine".

### Step 3: Write the UAT plan and evidence template

**Output location**: `.wire/releases/$ARGUMENTS/migration/logical_access_uat_plan.md`

Structure:

1. **Scope** — target region, tenant predicate, target project, and the list of IAM boundaries under test.
2. **Test matrix** — one section per boundary; within each, a table of tests:

   | Test ID | Boundary | Role | Type (positive/negative) | Action / query | Expected result |
   |---------|----------|------|--------------------------|----------------|-----------------|

3. **Evidence template** — for each test ID, a capture block to be filled during execution:

   ```markdown
   ### Evidence — {{TEST_ID}}
   - Boundary: {{BOUNDARY}}
   - Role / principal: {{ROLE}}
   - Type: positive | negative
   - Action: {{QUERY_OR_ACTION}}
   - Expected: {{EXPECTED}}
   - Actual: {{ACTUAL}}            <!-- query output, error text, or masked value -->
   - Evidence ref: {{SCREENSHOT_OR_LOG}}
   - Result: PASS | FAIL
   - Tester: {{NAME}}   Date: {{DATE}}
   ```

4. **Sign-off block** — completed at review (left blank here):

   ```markdown
   ## Sign-off
   - All positive tests passed: ☐
   - At least one negative test passed per IAM boundary: ☐
   - No cross-tenant data was reachable in any negative test: ☐

   **Signed off by**: ________________   **Role**: ____________   **Date**: __________
   **Decision**: approved | changes_requested
   ```

### Step 4: Update status

```yaml
artifacts:
  logical_access_uat:
    generate: complete
    file: migration/logical_access_uat_plan.md
    generated_date: "{{TODAY}}"
    target_region: "{{REGION}}"
    boundaries_under_test: N
    positive_tests: N
    negative_tests: N
```

### Step 5: Output next command

```
/wire:logical-access-uat-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/logical_access_uat_plan.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact_id, `Logical-Access UAT` as artifact_name, and the `file` value from `artifacts.logical_access_uat` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `logical_access_uat` as artifact, `generate` as action.

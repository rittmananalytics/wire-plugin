---
wire_schema: "1.0"
command: generate
artifact: security_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Catalog roles, permissions, users, and service accounts on the source platform

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: security_audit` and `artifact_file_path: audit/security_audit.md` before proceeding.
Follow `specs/utils/audit_baseline_check.md` with `artifact_id: security_audit` before proceeding. It reads `artifacts.security_audit.baseline_path` from `status.md` and no-ops if unset — see that spec's Step 0. If set, it must PASS (or any figure mismatch it warns on must be resolved) before Step 1 below starts.

---

# Security Audit — Generate

## Purpose

Catalogs all IAM roles, warehouse roles, users, groups, service accounts, row-level security policies, column masking policies, and network policies on the source platform. The output drives security configuration on the target platform and ensures no permission gaps during cutover.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- Sufficient privileges to query security catalog tables (ACCOUNTADMIN on Snowflake; Project IAM Viewer on BigQuery)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — source platform
- Source platform security/IAM APIs or `ACCOUNT_USAGE` / IAM metadata

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration`. Read `migration.source_platform`.

### Step 2: Query security catalog

**If source is BigQuery**:

Query IAM policy bindings:
```sql
-- Dataset-level IAM bindings
SELECT
  schema_name AS dataset,
  grantee,
  privilege_type,
  is_grantable
FROM `region-us`.INFORMATION_SCHEMA.SCHEMA_PRIVILEGES
ORDER BY schema_name, grantee;
```

Also collect:
- Project-level IAM bindings via `gcloud projects get-iam-policy` (if CLI available) or ask user to export
- Row-level security filters: `INFORMATION_SCHEMA.ROW_ACCESS_POLICIES`
- Column-level security: `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` for policy tags
- Service accounts used by Fivetran and other integrations

**If source is Snowflake**:

```sql
-- All roles
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.ROLES WHERE DELETED_ON IS NULL;

-- Role grants (role hierarchy)
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES
WHERE DELETED_ON IS NULL AND GRANTED_ON IN ('DATABASE','SCHEMA','TABLE','VIEW');

-- Users and their roles
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS WHERE DELETED_ON IS NULL;

-- Row access policies
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.ROW_ACCESS_POLICIES WHERE DELETED_ON IS NULL;

-- Dynamic data masking policies
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES WHERE DELETED_ON IS NULL;

-- Network policies
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.NETWORK_POLICIES;
```

### Step 3: Classify each security object

For each role / policy, classify:

- **Type**: `role`, `user`, `service_account`, `row_access_policy`, `column_mask`, `network_policy`
- **Migration approach**:
  - `recreate` — equivalent exists on target, can be recreated directly
  - `translate` — concept exists but syntax/mechanism differs (e.g., Snowflake role hierarchy → BigQuery IAM groups)
  - `evaluate` — no direct equivalent (e.g., BQ policy tags → Snowflake dynamic masking)
  - `exclude` — system roles, deprecated users

**Tenant carve-out (`migration.scope == tenant_carveout`)**

Read `migration.scope` and `migration.tenant_predicate` from status.md. When scope is `tenant_carveout`, additionally classify each role and grant by its tenant relationship:

- **tenant_scoped** — exists to give one tenant (or tenant group) access to its own data, or is gated on the tenant key. These map into the carve-out's tenant-scoped IAM model on the target.
- **shared** — platform-wide roles (admin, analyst, integration service accounts) that span all tenants. These are recreated on the target as-is, not narrowed to the extracted tenant.

Also flag, for every in-scope table, whether it carries the tenant key referenced by `migration.tenant_predicate` (e.g. `tenant_id`). Tables with the tenant key are candidates for a target row-level security policy on that key; tables without it are shared/reference data — note them so the strategy step can decide whether they are copied whole or excluded.

When scope is absent or `full_migration`, skip this classification entirely — the audit is unchanged.

### Step 4: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/security_audit.md`

Use the template at `TEMPLATES/migration/security_audit.md`. Include:
- Role hierarchy diagram (text-based tree)
- User and service account inventory
- Row-level security policies with SQL definitions
- Column masking policies with definitions
- Network policies
- Migration approach assignments
- Objects flagged `evaluate` with notes
- (tenant_carveout only) tenant_scoped vs shared classification for each role/grant, and the tenant-key presence flag per in-scope table

### Step 5: Update status

```yaml
artifacts:
  security_audit:
    generate: complete
    file: audit/security_audit.md
    generated_date: "{{TODAY}}"
    roles_count: N
    users_count: N
    rls_policies: N
    masking_policies: N
```

### Step 6: Output next command

```
/wire:security-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/security_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `security_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `security_audit` as artifact_id, `Security Audit` as artifact_name, and the `file` value from `artifacts.security_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `security_audit` as artifact, `generate` as action.

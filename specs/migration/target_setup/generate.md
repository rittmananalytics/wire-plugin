---
wire_schema: "1.0"
command: generate
artifact: target_setup
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
  - artifact: migration_strategy
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate target warehouse DDL scripts (SAFETY GATE — writes to target platform)

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: target_setup` and `artifact_file_path: migration/target_setup_scripts/MANIFEST.md` before proceeding.
When the target platform is BigQuery, route Step 0.3's MCP call through `specs/utils/bigquery_mcp_fallback.md` on a connection failure, instead of the manual-checklist deferral this step used to fall back to.

---

# Target Setup — Generate

## Purpose

Generates the DDL scripts required to create all databases, schemas, tables, views, roles, and policies on the target platform. The scripts are written to disk for review before any are executed. This command produces scripts only — it does not execute them.

## Prerequisites

- `migration/migration_strategy.md` with `review: approved`
- Target platform credentials available (or scripts will be generated for manual execution)

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/audit/db_object_audit.md`
- `.wire/releases/$ARGUMENTS/audit/security_audit.md`
- `.wire/releases/$ARGUMENTS/audit/batch_zero_plan.json` — the UDF layer (`layer: udf` entries) for Step 5b; optional (skip cleanly if absent or dbt-audit was not run)
- Platform pair type mapping: `wire/platform_pairs/{pair}/type_mapping.md`
- Platform pair translation guide/reference: `wire/platform_pairs/{pair}/translation_guide.md` and `translation_reference.md` (for translating UDF bodies in Step 5b)

## Workflow

### Step 0: Pre-generation permissions and connectivity check

Run these checks before generating any scripts. A runbook that will fail on first execution wastes the review gate.

**Step 0.1: Read target platform from status.md**

Read `migration.target_platform`, `migration.target_project` (BigQuery) or `migration.target_account` (Snowflake), and `migration.service_account_key_path` (BigQuery) from status.md.

**Step 0.2: Check service account key file (BigQuery only)**

If `target_platform` is `bigquery` and `service_account_key_path` is set:

```bash
ls "[service_account_key_path]" 2>/dev/null && echo "KEY_FOUND" || echo "KEY_MISSING"
```

If `KEY_MISSING`:
```
❌ Pre-flight failed: service account key file not found at [service_account_key_path]
   Update migration.service_account_key_path in status.md with the correct path and re-run.
```
Stop.

**Step 0.3: BigQuery MCP probe (BigQuery target only), with automatic `bq` CLI fallback**

Run:

```
mcp__claude_ai_BigQuery_MCP__list_dataset_ids:
  project_id: "[target_project]"
```

If the MCP server is not connected or the call fails to respond, follow `specs/utils/bigquery_mcp_fallback.md` (`operation: schema_lookup`) automatically before treating this as anything other than a normal probe result — do not skip the check or defer it to a manual checklist. Whichever path answers (MCP or the `bq` CLI fallback), interpret the result the same way:

- **Success** — the target project is reachable and the credential has at least `bigquery.datasets.list`. Record: `✓ Target project [target_project] is accessible.` (note in the manifest whether this used the MCP or the `bq` CLI fallback).
- **Permission denied / 403** — the credential lacks the required permissions. Output:
  ```
  ❌ Pre-flight failed: cannot list datasets in [target_project].
     Required permission: bigquery.datasets.create (and bigquery.tables.create).
     Grant the service account the BigQuery Data Editor role on [target_project] and re-run.
  ```
  Stop.
- **Project not found / 404** — Output:
  ```
  ❌ Pre-flight failed: project [target_project] not found or not accessible.
     Check that migration.target_project in status.md is correct and that the
     service account belongs to (or has been granted access to) that project.
  ```
  Stop.
- **Both the MCP and the `bq` CLI fallback fail** — this is the only case that still falls through to a manual checklist, since neither automated path could answer at all:
  1. Output a warning:
     ```
     ⚠️  BigQuery unreachable via both the MCP and the bq CLI fallback — skipping automated permission check.
         Add a manual pre-flight check to the generated runbook (Step 0 below).
     ```
  2. Add the following section as **Step 0: Pre-flight manual check** at the top of the generated `MANIFEST.md`:
     ```markdown
     ## Step 0: Pre-flight checklist (run before executing any scripts)

     Before running any DDL scripts, verify the following manually:

     - [ ] Service account key exists at: [service_account_key_path]
     - [ ] Service account has BigQuery Data Editor role on project: [target_project]
     - [ ] Target project [target_project] exists and is accessible
     - [ ] `gcloud auth activate-service-account --key-file=[service_account_key_path]`
     - [ ] `bq ls --project_id=[target_project]` returns without error
     ```

**Step 0.5: Snowflake target**

If `target_platform` is `snowflake`, skip steps 0.2–0.4. Snowflake connectivity is verified when the consultant first runs a query via the Snowflake MCP. Add a manual pre-flight note to the MANIFEST.md advising the consultant to confirm their Snowflake role has `CREATE SCHEMA` and `CREATE TABLE` on the target database.

### Step 1: Confirm prerequisites

1. Confirm `migration_strategy review: approved` in status.md. If not, stop with message.
2. Read source and target platforms from status.md.
3. If target setup scripts already exist in `migration/target_setup_scripts/`, ask whether to regenerate.

### Step 2: Generate schema DDL

For each database/schema in the db_object audit with `migration_approach` of `recreate_ddl` or `translate_view`:

- Generate `CREATE DATABASE IF NOT EXISTS` (Snowflake) or `CREATE SCHEMA IF NOT EXISTS` (BigQuery) statements
- Apply naming conventions consistent with target platform (snake_case for BQ datasets, etc.)
- Include `COMMENT` clauses where source had descriptions

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/01_schemas.sql`

### Step 3: Generate table DDL

For each table with `migration_approach: recreate_ddl`:

- Translate column types using the type mapping file
- Apply partitioning/clustering equivalents per the migration strategy
- Generate `CREATE TABLE IF NOT EXISTS` with full column definitions
- Include `COMMENT ON TABLE` and `COMMENT ON COLUMN` statements

For tables with incompatible types (flagged `evaluate` in the type mapping), insert a `-- TODO: manual review required` comment in the DDL.

**Automated first pass (snowflake → bigquery only)**: when the target is BigQuery and the migration strategy elects to use it, run the source DDL through the BigQuery Migration Service as a first pass, then reconcile against `type_mapping.md` before writing the final scripts. See `wire/platform_pairs/snowflake_to_bigquery/bqms_first_pass.md`. BQMS gets the bulk of the column/type translation right; the type mapping catches the lossless-conversion flags (e.g. `NUMBER` precision, `VARIANT` → `JSON` vs `STRING`) and partition/cluster carry-over. Read its translation report — every warning is a candidate `-- TODO: manual review required`. Do not skip the reconciliation: BQMS output is a draft, not the final DDL.

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/02_tables.sql`

### Step 4: Generate view DDL (stubs)

For each view with `migration_approach: translate_view`:

- Generate a stub `CREATE VIEW` with the original SQL as a comment
- Add a `-- TODO: translate using dbt-migration or manual review` marker
- The actual view translation happens during dbt migration or manual translation

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/03_views_stub.sql`

### Step 5: Generate role and permission DDL

Based on the security audit:

- `GRANT` statements for each role on each schema/table
- Row-level security policy creation
- Column masking policy creation (where directly translatable)
- Service account permissions

**Tenant carve-out (`migration.scope == tenant_carveout`)**

When scope is `tenant_carveout`, read `migration.tenant_predicate` and the tenant-scoped IAM model + RLS predicate defined in the migration strategy's Security migration section, and emit into `04_security.sql`:

- **Tenant-scoped GRANTs** — grant `tenant_scoped` roles only on the extracted tenant's target project/dataset (BigQuery) or database/schema (Snowflake); recreate `shared` roles platform-wide exactly as for a full migration.
- **RLS predicate** — for each in-scope table flagged with the tenant key, emit the row-level security policy that filters on it, reusing the platform pair's mechanism (snowflake → bigquery: `translation_reference.md` §16): BigQuery `CREATE ROW ACCESS POLICY ... ON <table> GRANT TO (<principals>) FILTER USING (<tenant_predicate>)`; Snowflake `CREATE ROW ACCESS POLICY ...` attached via `ALTER TABLE ... ADD ROW ACCESS POLICY`.
- **Reuse the existing PII policy-tag taxonomy** — do not stand up a parallel masking mechanism. Tenant-sensitive columns attach to the same Data Catalog policy-tag taxonomy already used for PII column masking (the `column_mask` objects from the security audit); add the tenant dimension to that taxonomy rather than creating a new one.

When scope is absent or `full_migration`, emit the security DDL exactly as the four bullets above — no tenant scoping is applied.

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql`

### Step 5b: Generate UDF DDL (batch-zero UDF layer)

The batch-zero pass has two lifecycles. The Jinja / dispatched macros (`layer: macro`) are pure dialect translation, handled by `/wire:dbt-migration-generate --macros`. The **UDFs** (`layer: udf` — `create_udfs` and `fn_*` → `CREATE FUNCTION`) are warehouse DDL objects with a deploy-once + verify-exists lifecycle. They belong here, alongside the other target objects, and are deployed as part of target-setup Phase 1 (before model batch 1 runs).

Read `.wire/releases/$ARGUMENTS/audit/batch_zero_plan.json`:

- If the file is absent (dbt-audit was not run, e.g. a discovery-only or non-dbt migration), **skip this step** with a one-line note: `[wire] No batch_zero_plan.json — skipping UDF DDL (no dbt UDF layer to deploy).` Do not block.
- Select entries with `layer: "udf"`. If none, note `[wire] No UDF-layer entries in batch_zero_plan.json — skipping 05_udfs.sql.` and skip.

Split the selected UDFs by `action`:

**`action: translate` UDFs — emit `CREATE FUNCTION` DDL.** Translate each UDF body from the source dialect to the target using the platform-pair `translation_guide.md` / `translation_reference.md` (same engine as model translation). Emit target `CREATE FUNCTION` (BigQuery: `CREATE FUNCTION IF NOT EXISTS`; Snowflake: `CREATE FUNCTION IF NOT EXISTS`) statements into the script, **in tier order** so a UDF is defined after any UDF it calls: all of tier 0 first, then tier 1, …, and `create_udfs` (the aggregator) last. This mirrors the pilot, which deployed `STRIP_NULL_VALUE` and the dispatched helper UDFs manually as target-setup Phase 1. Where a UDF depends on another UDF's fully-qualified name, reference the target namespace, not the source.

**`action: redesign` UDFs — do not mechanically translate.** These have no direct target equivalent (Snowpark Python, JS VARIANT handling, etc.). Do **not** emit a `CREATE FUNCTION` for them. Instead, write a clearly-commented block into `05_udfs.sql` naming each redesign UDF, its source construct, and its model reach, and add each to the **UDF redesign decisions** section of the MANIFEST (Step 6) as an explicit architecture decision — BigQuery ML, Vertex AI, a remote UDF, or an in-model rewrite. This is a decision for the `target-setup-review` safety gate, not a translation.

**`action: manual-review-out-of-scope`** entries (session/catalog/dev-tooling) are not model-build objects — list them in a trailing comment in `05_udfs.sql` and move on; they are not deployed.

Add a verify-exists footer to `05_udfs.sql` — a commented `INFORMATION_SCHEMA.ROUTINES` (BigQuery) or `SHOW USER FUNCTIONS` (Snowflake) query the operator runs post-execution to confirm every translated UDF was created.

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/05_udfs.sql`

### Step 6: Generate execution manifest

Write a manifest file listing all scripts with descriptions and recommended execution order:

`.wire/releases/$ARGUMENTS/migration/target_setup_scripts/MANIFEST.md`

Include `05_udfs.sql` in the execution order when it was written (Step 5b) — after `04_security.sql` and before model batch 1. If any `redesign` UDFs were found, add a **UDF redesign decisions** section to the MANIFEST that names each redesign UDF, its source construct, and its model reach, and states that a target approach (BigQuery ML / Vertex AI / remote UDF / in-model rewrite) must be chosen at the `target-setup-review` gate before the affected models can be translated. This is the equivalent of the `redesign` macro bucket surfacing at review — an architecture decision, not a mechanical step.

### Step 7: Update status

```yaml
artifacts:
  target_setup:
    generate: complete
    file: migration/target_setup_scripts/MANIFEST.md
    generated_date: "{{TODAY}}"
    scripts_count: N
    tables_in_ddl: N
    udfs_in_ddl: N              # layer:udf, action:translate entries written to 05_udfs.sql (0 or absent if no UDF layer)
    udfs_redesign: N            # layer:udf, action:redesign entries surfaced at the review gate
    mcp_fallback_count: N       # BigQuery target only; 0 when the MCP stayed up — see specs/utils/bigquery_mcp_fallback.md
```

### Step 8: Emit dbt profiles.yml block

Read the following fields from status.md:

| status.md field | profiles.yml key |
|-----------------|-----------------|
| `migration.target_platform` | type (bigquery / snowflake) |
| `migration.target_project` (BigQuery) or `migration.target_account` (Snowflake) | project / account |
| `migration.target_dataset` (BigQuery) or `migration.target_database` + `migration.target_schema` (Snowflake) | dataset / database + schema |
| `migration.target_location` (BigQuery, default: `EU`) | location |
| `migration.service_account_key_path` (BigQuery) or `migration.snowflake_user` + `migration.snowflake_private_key_path` (Snowflake) | keyfile / user + private_key_path |

If `target_platform` is `bigquery`, emit:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add this to ~/.dbt/profiles.yml to connect to the target BigQuery environment:

[profile_name]:
  target: bigquery
  outputs:
    bigquery:
      type: bigquery
      method: service-account
      project: [target_project]
      dataset: [target_dataset]
      location: [target_location, default EU]
      keyfile: [service_account_key_path]
      threads: 4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Where `[profile_name]` is the engagement_name from status.md with `_target` appended (e.g. `acme_target`).

If `target_platform` is `snowflake`, emit the equivalent Snowflake block using `method: private-key` or `method: password` depending on which credentials are present in status.md.

If any required field is missing from status.md, emit a placeholder (`[FILL IN: ...]`) rather than omitting the block. This ensures the consultant has a complete template to fill in rather than having to construct the format from scratch.

Do not write this block to the file system — output it to the console only.

### Step 9: Output summary and safety reminder

```
Target setup scripts generated. These scripts have NOT been executed.

Scripts written to: .wire/releases/$ARGUMENTS/migration/target_setup_scripts/

Review the scripts carefully before the review step. The review gate requires
explicit approval before any script is executed against the target platform.

/wire:target-setup-validate $ARGUMENTS
```

If any `redesign` UDFs were surfaced in Step 5b, add an explicit line so they are not missed at the gate:

```
⚠  N UDF(s) have no direct [target_platform] equivalent and need an architecture
   decision at target-setup-review (see "UDF redesign decisions" in MANIFEST.md):
   [list each redesign UDF]
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/01_schemas.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/02_tables.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/03_views_stub.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/05_udfs.sql` — when a `layer: udf` batch-zero layer exists (Step 5b)
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/MANIFEST.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `target_setup` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `target_setup` as artifact_id, `Target Setup` as artifact_name, and the `file` value from `artifacts.target_setup` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `target_setup` as artifact, `generate` as action.

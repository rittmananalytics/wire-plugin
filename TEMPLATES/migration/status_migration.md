---
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
project_type: "platform_migration"
client_name: "{{CLIENT_NAME}}"
engagement_name: "{{ENGAGEMENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "audit"

migration:
  source_platform: "{{SOURCE_PLATFORM}}"   # bigquery | snowflake
  target_platform: "{{TARGET_PLATFORM}}"   # bigquery | snowflake
  scope: full_migration                    # full_migration (default) | tenant_carveout
                                           # full_migration = migrate the whole platform (standard six-phase sequence)
                                           # tenant_carveout = extract a single tenant's data into the target
  tenant_predicate: null                   # tenant_carveout only: the WHERE clause / tenant key that scopes the
                                           # extracted tenant, e.g. "tenant_id = 4815". Consumed by the carve-out
                                           # steps (region-tagging, bulk-copy-migration, logical-access-uat).
                                           # Leave null for full_migration.
  dbt_project_path: "{{DBT_PROJECT_PATH}}" # default: ./dbt
  orchestration_tool: "{{ORCHESTRATION_TOOL}}" # dagster | dbt_cloud | airflow | none
  ingestion_tool: "{{INGESTION_TOOL}}"     # fivetran | rudderstack | coupler-io | segment | airbyte | other
  reporting_tool: none                     # looker | metabase | none — the client's reporting/BI layer.
                                           # metabase enables the metabase_audit / metabase_migration commands;
                                           # looker is the Wire default. Not gated by migration.scope.
  connectivity: "{{CONNECTIVITY}}"         # public_endpoint | private_network_mcp_tunnel
  target_project: null      # BigQuery: GCP project ID for the target environment
  target_dataset: null      # BigQuery: default dataset / schema on the target
  target_location: "EU"     # BigQuery: data location (default: EU)
  target_account: null      # Snowflake: account identifier (e.g. xy12345.us-east-1)
  target_database: null     # Snowflake: target database name
  target_schema: null       # Snowflake: default schema on target database
  service_account_key_path: null  # BigQuery: local path to service account JSON key file
  transformation_log_table: null  # Optional BigQuery audit table for dbt-migration per-model transformation log
                                   # e.g. "<target-project>.wire_audit.dbt_transformation_log" — unset = logging skipped
  materialization_overrides_path: null  # Optional engagement-relative path to a materialisation overrides file
                                   # (schema: default: preserve + overrides[] with select/exclude/force_materialized).
                                   # unset = faithful preservation of every model's source materialisation.
  equivalency_baseline: null       # Release-level; set per freeze. null = equivalency runs in live mode.
                                   # When pinned (see migration_strategy "frozen equivalency baseline"):
                                   #   t: "<UTC instant>"                  # both sides pinned to this instant
                                   #   source_clone: "<db>.wire_baseline"  # Snowflake zero-copy clone AT(TIMESTAMP => t)
                                   #   target_watermark: "_fivetran_synced"# BigQuery Bronze watermark column (rows <= t)
                                   #   source_commit: "<sha>"              # source dbt snapshot SHA used
                                   #   type_translation_allowlist: []      # expected type changes (VARIANT->JSON/STRING,
                                   #                                       #   TIMESTAMP_NTZ->DATETIME, NUMBER-scale rounding)
                                   # equivalency-validate --baseline reads this per --batch.
  status: not_started                      # not_started | in_progress | complete
  completed_date: null

data_safety:
  source_readonly: true     # ALWAYS true — source platform is never written to during migration
  target_project: null      # Designated target project/account — all writes go here only
  production_projects: []   # Client production project IDs to treat as off-limits for writes
                            # e.g. ["acme-prod", "acme-analytics-prod"]

  equivalency_validation:
    checks_total: null
    checks_passing: null
    checks_failing: null
    last_run_date: null
    loop_history: []
    status: null    # null | failing | passing | complete

jira:
  project_key: null
  structure: subtasks       # subtasks (default — one Task + 3 Sub-tasks per artifact) | single_issue (one Task per artifact, status transitions)
  epic_key: null
  artifacts:
    ingestion_audit:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    db_object_audit:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    security_audit:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    dbt_audit:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    orchestration_audit:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    migration_inventory:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    migration_strategy:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    target_setup:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    ingestion_migration:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    dbt_migration:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    orchestration_migration:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    cutover:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    migration_report:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null

docstore:
  provider: null
  confluence:
    cloud_id: null
    space_key: null
    parent_page_id: null
    artifacts:
      ingestion_audit:
        page_id: null
        page_url: null
        last_synced: null
      db_object_audit:
        page_id: null
        page_url: null
        last_synced: null
      security_audit:
        page_id: null
        page_url: null
        last_synced: null
      dbt_audit:
        page_id: null
        page_url: null
        last_synced: null
      orchestration_audit:
        page_id: null
        page_url: null
        last_synced: null
      migration_inventory:
        page_id: null
        page_url: null
        last_synced: null
      migration_strategy:
        page_id: null
        page_url: null
        last_synced: null
      migration_report:
        page_id: null
        page_url: null
        last_synced: null
  notion:
    parent_page_id: null
    artifacts:
      ingestion_audit:
        page_id: null
        page_url: null
        last_synced: null
      db_object_audit:
        page_id: null
        page_url: null
        last_synced: null
      migration_inventory:
        page_id: null
        page_url: null
        last_synced: null
      migration_report:
        page_id: null
        page_url: null
        last_synced: null

artifacts:
  ingestion_audit:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    connector_count: null
    data_source: null   # fivetran_mcp | csv
    generated_files: []
    revision_history: []

  db_object_audit:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    total_objects: null
    tables: null
    views: null
    other: null
    generated_files: []
    revision_history: []

  security_audit:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    roles_count: null
    users_count: null
    rls_policies: null
    masking_policies: null
    generated_files: []
    revision_history: []

  dbt_audit:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    model_count: null
    simple_count: null
    moderate_count: null
    complex_count: null
    batch_count: null
    macro_count: null
    source_count: null
    test_count: null
    generated_files: []
    revision_history: []

  orchestration_audit:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    job_count: null
    scheduled_job_count: null
    orchestration_tool: null
    generated_files: []
    revision_history: []

  migration_inventory:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    total_objects: null
    estimated_hours: null
    generated_files: []
    revision_history: []

  lineage_view:
    generate: not_started
    file: null
    generated_date: null
    node_count: null
    edge_count: null
    generated_files: []

  migration_strategy:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

  target_setup:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    scripts_count: null
    tables_in_ddl: null
    generated_files: []
    revision_history: []

  ingestion_migration:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    connectors_in_runbook: null
    generated_files: []
    revision_history: []

  dbt_migration:
    generate: not_started
    validate: not_started
    review: not_started
    generated_date: null
    current_batch: 1
    batches_complete: []
    models_translated: null
    generated_files: []
    revision_history: []

  orchestration_migration:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    jobs_in_runbook: null
    generated_files: []
    revision_history: []

  cutover:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

  migration_report:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

  migration_register:
    generate: not_started
    validate: not_started
    file: null   # migration/migration_register.csv — per-model state store
    generated_date: null
    models_total: null
    migrated: null
    drifted: null
    pending: null
    failed: null
    revision_history: []

  migration_drift:
    generate: not_started
    validate: not_started
    file: null   # migration/migration_drift_report.md
    last_run_date: null
    drift_head: null
    modified: null
    removed: null
    new: null
    syncs_flagged: null
    masking_changes: null
    revision_history: []

notes:
  - "Release created: {{CREATED_DATE}}"

blockers: []
---

# Migration Status: {{PROJECT_NAME}}

**Client**: {{CLIENT_NAME}}
**Release ID**: {{PROJECT_ID}}
**Type**: Platform Migration
**Source**: {{SOURCE_PLATFORM}} → **Target**: {{TARGET_PLATFORM}}
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

## Migration Configuration

| Setting | Value |
|---------|-------|
| Source platform | {{SOURCE_PLATFORM}} |
| Target platform | {{TARGET_PLATFORM}} |
| dbt project path | {{DBT_PROJECT_PATH}} |
| Orchestration tool | {{ORCHESTRATION_TOOL}} |
| Connectivity | {{CONNECTIVITY}} |

## Current Phase: Audit

## Next Action

Run all 5 source platform audits in parallel:
```
/wire:migration-audit-all {{PROJECT_NAME}}
```

Or run individually:
```
/wire:ingestion-audit-generate {{PROJECT_NAME}}
```

## Artifact Status Summary

| Phase | Artifact | Generate | Validate | Review | Ready |
|-------|----------|----------|----------|--------|-------|
| **Audit** | ingestion_audit | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | db_object_audit | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | security_audit | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | dbt_audit | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | orchestration_audit | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Inventory** | migration_inventory | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | lineage_view | ⏸️ | — | — | ❌ |
| **Strategy** | migration_strategy | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Setup** | target_setup | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Ingestion** | ingestion_migration | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **dbt** | dbt_migration | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Orchestration** | orchestration_migration | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Equivalency** | equivalency_validation | — | — | — | ❌ |
| **Cutover** | cutover | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Report** | migration_report | ⏸️ | ⏸️ | ⏸️ | ❌ |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Failed/Not Started | ⏸️ Not Started | ⚠️ Blocked | — (repeatable loop)

## Equivalency Validation Loop

| Run | Date | Passing | Failing | Report |
|-----|------|---------|---------|--------|
| — | — | — | — | — |

## Notes

[Add project-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|

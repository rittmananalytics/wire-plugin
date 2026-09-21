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
  parent_target_project: null              # tenant_carveout only: the parent migration's target project, used as
                                           # the comparison source for relocate-origin models (equivalency-validate,
                                           # Relocate-mode comparison) and as defer-build's fallback defer state.
                                           # Leave null for full_migration or a carve-out with no landed parent.
  parent_release: null                     # tenant_carveout only: the parent migration's release folder name
                                           # (e.g. "05-lift-and-shift"). dbt-carveout-relocate reads the parent's
                                           # migration_register.csv from it to write the parent_release /
                                           # parent_model / parent_verdict_ref linkage columns, and refuses to
                                           # relocate a model whose parent verdict is fail. Leave null when the
                                           # parent register is not reachable from this checkout.
  cross_release_triggers: []               # tenant_carveout only: machine-readable parent→carve-out dependencies,
                                           # checked by migration-drift-generate (Step 5c). One entry per trigger:
                                           #   - event: "parent_bronze_backfill_complete"   # short id, unique in list
                                           #     parent_release: "05-lift-and-shift"
                                           #     condition: "<what to check, e.g. parent register rows X..Y reach
                                           #                 state=migrated / delivery_stage=production_verified>"
                                           #     action: "re-verify <models> | re-run /wire:equivalency-validate --models <...>"
                                           #     status: open                               # open | fired | closed
                                           # A caveat that "closes when the parent completes X" belongs here,
                                           # not in a PR comment nobody re-reads.
  declared_windows: []                     # Optional per-object availability windows (equivalency-validate Step 1e).
                                           # Auto-derivation from target Bronze MIN(loaded_at) needs no entry here;
                                           # add one to declare a window explicitly or to add exclusions:
                                           #   - object: "orders"            # object name or table pattern
                                           #     floor: "2023-06-01T00:00:00Z"
                                           #     cap: null                   # null = the run's pinned as-of
                                           #     exclusions:
                                           #       - range: "2023-06-01"
                                           #         reason: "connector initial-load day — bulk backfill row shapes"
  known_differences_path: null             # Optional path to the engagement's connector-emission known-differences
                                           # registry (default: migration/known_differences.yaml when present).
                                           # Loaded by equivalency-validate; a divergence matching an entry
                                           # classifies pass_qualified with the entry cited. See
                                           # TEMPLATES/migration/known_differences.yaml.
  bring_in:                                # bulk-copy-migration-generate --mode bring-in (source-platform-only history)
    copy_gate:                             # per-table gate between the chunked-copy and export paths
      max_rows: 10000000                   #   tables at or under both limits are COPYABLE via chunked copy
      max_gb: 3                            #   over either limit → EXPORT (client-run execute-pack)
  dbt_project_path: "{{DBT_PROJECT_PATH}}" # default: ./dbt
  orchestration_tool: "{{ORCHESTRATION_TOOL}}" # dagster | dbt_cloud | airflow | none
  ingestion_tool: "{{INGESTION_TOOL}}"     # fivetran | rudderstack | coupler-io | segment | airbyte | other
  reporting_tool: none                     # looker | metabase | omni | oac | none — the client's reporting/BI layer.
                                           # metabase enables the metabase_audit / metabase_migration commands;
                                           # omni enables the omni_audit / omni_migration commands (same role,
                                           # adapted to Omni's connection -> model -> topic -> workbook/tile hierarchy);
                                           # oac enables the oac_audit / oac_migration commands (same role, adapted
                                           # to OAC's SMML physical/logical/presentation layer object model);
                                           # looker is the Wire default. Not gated by migration.scope.
  reverse_etl_tool: none                   # hightouch | none | other — the client's reverse ETL layer, if any.
                                           # hightouch enables the sixth audit (reverse_etl_audit) and
                                           # reverse_etl_migration commands; other covers Census/Polytomic,
                                           # which follow the same output shape but aren't implemented yet.
                                           # none is the default — the sixth audit simply doesn't run.
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
  pii_tag_map_path: null           # Optional path to the PII tag map JSON — flat
                                   # {source_masking_policy_name: target_policy_tag_resource_path}.
                                   # unset = dbt-migration looks for .wire/releases/<release>/migration/tag_map.json,
                                   # then falls back to manual policy_tags authoring per column.
  equivalency_baseline: null       # Release-level; set per freeze. null = equivalency runs in live mode.
                                   # When pinned (see migration_strategy "frozen equivalency baseline"):
                                   #   t: "<UTC instant>"                  # both sides pinned to this instant
                                   #   source_clone: "<db>.wire_baseline"  # Snowflake zero-copy clone AT(TIMESTAMP => t)
                                   #   target_watermark: "_fivetran_synced"# BigQuery Bronze watermark column (rows <= t)
                                   #   source_commit: "<sha>"              # source dbt snapshot SHA used
                                   #   type_translation_allowlist: []      # expected type changes (VARIANT->JSON/STRING,
                                   #                                       #   TIMESTAMP_NTZ->DATETIME, NUMBER-scale rounding)
                                   # equivalency-validate --baseline reads this per --batch.
  gate_policy: equivalence_before_pr       # equivalence_before_pr (default) | ship_then_verify.
                                           # Governs when a translated model may enter a client PR
                                           # (dbt-migration-batch-raise eligibility rules).
                                           # ship_then_verify requires a recorded client ruling (note the
                                           # date and forum in notes below) and makes the pre-raise smoke
                                           # comparison and post-merge verification run points mandatory.
  gate_policy_ruling: null                 # ship_then_verify only: who ruled, where, when
  client_repos: []                         # Repos this migration ships into, one entry per repo:
                                           #   - role: transformation | orchestration | reverse_etl
                                           #     url: "git@github.com:org/repo.git"
                                           #     base_branch: main
                                           # Consumed by dbt-migration-batch-raise and utils-ci-parity.
                                           # Empty = batch-raise asks once and persists the answer here.
  cost_controls:                           # Warehouse spend guardrails for sandbox builds and comparison
    unit: gb_scanned                       #   gb_scanned (BigQuery) | credits (Snowflake)
    per_run_budget: null                   #   max estimated cost per build/comparison run; null = warn only
    daily_budget: null                     #   max cumulative cost per day across all lanes; null = warn only
    scratch_dataset: wire_sandbox          #   sandbox dataset/schema dbt-migration-defer-build writes to
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

client_comms:                 # utils-client-watch / utils-ask-list-generate config. Nothing here is hardcoded
                              # in the commands — an unset slack_channel_id disables the watch tick cleanly.
  slack_channel_id: null      # required for utils-client-watch; no default
  ask_list_max: 5             # hard cap on open asks per list (client-ruled ceiling; default 5)
  answers_ledger: "decisions.md"   # release-relative path to the dated client-answers ledger
  post_merge_action: "/wire:equivalency-post-merge-verify"   # fired by the watch when an own PR merges

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
    baseline_path: null   # Optional: path to a prior audit/artifact this run builds on or compares
                          # against (e.g. a previous release's audit/security_audit.md). null = no
                          # baseline — security-audit-generate skips the baseline check entirely.
                          # When set, checked by specs/utils/audit_baseline_check.md before generation:
                          # fails loudly if the path is missing/empty, and warns if any role/PII/user
                          # count cited in this release's brief/SOW/status.md notes doesn't match what
                          # the baseline actually contains.
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

  migration_batching:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    data_file: null   # migration/migration_batching.csv
    generated_date: null
    batch_count: null
    objects_classified: null
    seed_used: null
    generated_files: []
    revision_history: []

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

precondition_overrides: []   # Appended by utils/precondition_gate.md whenever a consultant
                              # runs a gated command with an unmet precondition. Each entry:
                              # {artifact, action, unmet_precondition, overridden_by, reason, date}

# Release budget — what an agent may spend on this release
# (specs/utils/director_operating_model.md, "Budget"). Absent/null means the
# defaults: lanes_max 4, no warehouse restriction, stop at decisions. The release
# director sets it in prose ("two lanes, nothing against a warehouse, stop at
# decisions") and the orchestrating session writes the block. /wire:upgrade never
# writes one: an absent block means no budget was set, not a budget of defaults.
budget: null
#   lanes_max: 2                 # concurrent lanes; default 4
#   model_tier: default          # default | economy
#   warehouse_spend: none        # none | estimate_required | cap:<amount>
#   stop_at: decisions           # decisions | phase_end | never
#   set_by: "..."
#   set_at: "YYYY-MM-DD"

# Decisions waiting on the release director. Replaces the single agents.paused_at
# value below: a release can be waiting on more than one thing at once. Each
# entry carries id, artifact, kind (review | ruling | registry_proposal | budget |
# safety_gate), question, parked_at, and optionally awaiting. The first line of
# every orchestrated session is the count of these and their questions.
parked_decisions: []

agents:
  mode: null              # null | local | managed | orchestrated
  # The release claim. Written by whatever is going to dispatch (the orchestrating
  # session, or /wire:delegate), never by /wire:new or /wire:upgrade. A second
  # session that reads a live claim offers join / take-over / move instead of
  # dispatching. See specs/utils/director_operating_model.md, "The release claim".
  coordinator_session: null
  #   user: "Jane Smith"
  #   session_id: "<claude session id>"
  #   branch: "feat/03-store-dashboards"
  #   claimed_at: "YYYY-MM-DD HH:MM"
  #   last_write: "YYYY-MM-DD HH:MM"    # the 30-minute stall rule reads this
  last_orchestrated: null
  paused_at: null         # superseded by parked_decisions; kept so older readers still resolve
  active_sessions: []
  completed_sessions: []
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

## Precondition Overrides

| Date | Artifact | Action | Unmet Precondition | Overridden By | Reason |
|------|----------|--------|---------------------|----------------|--------|
| — | — | — | — | — | — |

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|

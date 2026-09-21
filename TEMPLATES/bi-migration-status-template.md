---
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
project_type: "bi_migration"
client_name: "{{CLIENT_NAME}}"
engagement_name: "{{ENGAGEMENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "audit"

# Profile: which tool pair this release migrates. Read by precondition_gate.md Step 0
# and by runnable_set.md. looker_to_omni is the only pair in 4.0.0.
bi_pair: looker_to_omni

bi_migration:
  source_tool: looker                      # looker (the only source in 4.0.0)
  target_tool: omni                        # omni (the only target in 4.0.0)
  lookml_repo_path: "{{LOOKML_REPO_PATH}}"   # local checkout of the LookML project (default ./lookml)
  looker_base_url: "{{LOOKER_BASE_URL}}"     # Looker API host, e.g. https://client.cloud.looker.com
  omni_base_url: "{{OMNI_BASE_URL}}"         # Omni instance, e.g. https://client.omniapp.co
  omni_model_id: "{{OMNI_MODEL_ID}}"         # the shared model the migration writes to, on a branch
  omni_profile: null                       # named `omni config` profile; null = OMNI_BASE_URL + OMNI_API_TOKEN
  omni_branch: null                        # set by omni-target-setup-generate when the model branch is created
  parallel_run_days: {{PARALLEL_RUN_DAYS}}   # both tools live side by side for this long after content lands
  cutover_date: null                       # set at cutover-review approval
  parity_scope: prioritised                # prioritised (tiles of the plan's prioritised dashboards) | all
  parity_as_of: null                       # pinned as-of for bi-equivalency-validate; null = set on first run
  stale_after_days: 180                    # content with views_90d = 0 and last_viewed older than this is a drop candidate
  warehouse: null                          # bigquery | snowflake | databricks; both tools read this warehouse
  client_repos: []                         # Downstream repos this migration writes into, one entry per repo:
                                           #   - role: bi_target_model            # the git-connected Omni model repo (Omni writes YAML back via `omni models commit`)
                                           #     url: "git@github.com:org/omni-model.git"
                                           #     base_branch: main
                                           # Read by omni-model-reverse-port and utils-client-watch. Empty = the Omni model is not git-connected;
                                           # reverse-port then reads the model with `omni models yaml-get` instead.

# Upstream and downstream repos registered with /wire:migration-source-register and pulled with
# /wire:migration-source-refresh. Every audit, model and drift command reads the local snapshot, never the live repo.
migration_sources:
  lookml: null                             # the client's LookML project (source type `lookml`):
                                           #   git_repo: "https://github.com/org/looker"
                                           #   branch: main
                                           #   subfolder: ""
                                           #   local_snapshot_path: ".wire/releases/<release>/migration/source_snapshot/lookml/"
                                           #   last_refreshed: null
                                           #   last_commit: null                # recorded by refresh; the audit stamps it on every catalog row
  omni_model: null                         # the git-connected Omni model repo (source type `omni_model`), when there is one:
                                           #   same fields; read by omni-model-reverse-port to see what client modellers changed in Omni

artifacts:
  business_rules:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    domains_covered: []
    generated_date: null

  looker_audit:
    generate: not_started
    validate: not_started
    review: not_started
    file: null                 # audit/looker_audit.md
    generated_date: null
    lookml_commit: null        # migration_sources.lookml.last_commit at audit time; every model catalog row carries it
    view_count: null
    explore_count: null
    field_count: null
    dashboard_count: null
    look_count: null
    tile_count: null
    mechanical_count: null
    assisted_count: null
    redesign_count: null
    drop_count: null
    generated_files: []
    revision_history: []

  omni_audit:                  # optional: only when the client already has Omni content (brownfield target)
    generate: not_started
    validate: not_started
    review: not_started
    file: null                 # audit/omni_audit.md
    generated_date: null
    connection_count: null
    topic_count: null
    view_count: null
    folder_count: null
    workbook_count: null
    tile_count: null
    raw_sql_tile_count: null
    resolved_view_count: null
    unresolved_view_count: null
    source_resolution_coverage_pct: null
    generated_files: []
    revision_history: []

  bi_migration_plan:
    generate: not_started
    validate: not_started
    review: not_started
    file: null                 # migration/bi_migration_plan.md
    data_file: null            # migration/bi_migration_batches.csv
    generated_date: null
    batch_count: null
    objects_in_scope: null
    objects_dropped: null
    register_rows: null
    baseline_id: null          # migration/baseline.yaml; a new id on every re-baseline
    generated_files: []
    revision_history: []

  migration_drift:             # optional scheduled gate: LookML changed under a translated view, or a dashboard edited in Looker after its batch
    generate: not_started
    validate: not_started
    file: null                 # migration/migration_drift_report.md
    generated_date: null
    last_run_date: null
    drift_head: null           # LookML commit the last run compared against
    views_drifted: null
    views_reclassified: null   # drifted views whose translation class changed (a mechanical view that gained Liquid)
    topics_impacted: null
    dashboards_impacted: null
    content_drifted: null      # dashboards or Looks edited in Looker after their content batch
    generated_files: []
    revision_history: []

  omni_target_setup:
    generate: not_started
    validate: not_started
    review: not_started
    file: null                 # migration/omni_target_setup.md
    generated_date: null
    connection_verified: null
    schema_refreshed: null
    branch_created: null
    groups_created: null
    generated_files: []
    revision_history: []

  omni_model:
    generate: not_started
    lint: not_started
    validate: not_started
    review: not_started
    file: null                 # migration/omni_model/omni_model.md
    generated_date: null
    lint_date: null
    lint_batch: null           # last batch linted
    batches_total: null
    batches_complete: null
    batches_validated: []      # batch ids whose validate passed; content batches gate on their model batch here
    views_emitted: null
    topics_emitted: null
    needs_human_open: null
    smoke_queries_run: null
    last_reverse_port: null    # omni-model-reverse-port: last run date
    reverse_port_conflicts: null   # files changed on both sides, reported and never clobbered
    generated_files: []
    revision_history: []

  omni_content:
    generate: not_started
    validate: not_started
    review: not_started
    file: null                 # migration/omni_content/omni_content.md
    generated_date: null
    plan_validated: null       # the pre-write validate pass for the last batch
    batches_total: null
    batches_complete: null
    batches_validated: []
    dashboards_planned: null
    dashboards_created: null
    tiles_skipped: null
    hand_finish_open: null     # text tiles, styling and other items listed for hand finishing
    generated_files: []
    revision_history: []

  bi_equivalency:
    validate: not_started      # pass only when every in-scope tile is pass, pass_qualified or pass_declared_deviation and none is unresolved; the cutover gate reads this
    last_run_date: null
    run_count: 0
    tiles_checked: null
    passing: null
    pass_qualified: null
    failing: null
    unresolved: null           # BLOCKED + INCONCLUSIVE + NOT_RUN tiles, plus uncompared dashboards
    blocked: null
    inconclusive: null
    accepted_differences: null # pass_declared_deviation, each with a named approver in decisions.md
    contracts: null            # test contracts under migration/parity/contracts/
    stale_evidence: null       # evidence rows with numeric_parity in stale_kinds; must be 0 for the gate
    dashboards_passing: null

  cutover:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

  training:
    generate: not_started
    validate: not_started
    review: not_started
    session_plans: []
    generated_date: null
    generated_files: []
    revision_history: []

  documentation:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

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

# BI Migration Status: {{PROJECT_NAME}}

**Client**: {{CLIENT_NAME}}
**Project ID**: {{PROJECT_ID}}
**Type**: bi_migration (looker_to_omni)
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

## Current Phase: Audit

## Next Action

Run the Looker estate audit:
```
/wire:looker-audit-generate {{PROJECT_NAME}}
```

## Artifact Status Summary

| Phase | Artifact | Generate | Validate | Review | Ready |
|-------|----------|----------|----------|--------|-------|
| **Business Rules** (optional) | business_rules | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Audit** | looker_audit | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | omni_audit (optional, brownfield target) | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Plan** | bi_migration_plan | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Target** | omni_target_setup | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Model** | omni_model (per batch, plus lint) | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Content** | omni_content (per batch) | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Parity** | bi_equivalency (loop) | - | ⏸️ | - | ❌ |
| **Cutover** | cutover | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Enablement** (optional) | training | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | documentation | ⏸️ | ⏸️ | ⏸️ | ❌ |

## Session History

| Date | Consultant | Focus | Outcome | Next |
|------|-----------|-------|---------|------|

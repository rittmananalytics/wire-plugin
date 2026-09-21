---
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
project_type: "{{PROJECT_TYPE}}"
client_name: "{{CLIENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "requirements"

# Build profile — dashboard_first releases only. The release type declares
# profile_field: build_profile with seeded and live_data; /wire:new Step 6b asks
# which, and writes it here. Left out entirely for release types with no
# profiles: block. Until 4.0.0 nothing asked and default_profile applied
# silently, so live_data was only reachable by hand-editing this file.
# build_profile: seeded       # seeded | live_data

jira:
  project_key: null
  structure: subtasks       # subtasks (default — one Task + 3 Sub-tasks per artifact) | single_issue (one Task per artifact, status transitions)
  epic_key: null
  artifacts:
    business_rules:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    requirements:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    workshops:
      task_key: null
      generate_key: null
      review_key: null
    conceptual_model:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    pipeline_design:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    data_model:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    seed_data:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    mockups:
      task_key: null
      generate_key: null
      review_key: null
    viz_catalog:
      task_key: null
      generate_key: null
    pipeline:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    orchestration:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    dbt:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    semantic_layer:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    dashboards:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    dbtcharts:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    agents_schema:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    data_refactor:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    data_quality:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    uat:
      task_key: null
      generate_key: null
      review_key: null
    deployment:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    training:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    documentation:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null

docstore:
  provider: null  # confluence | notion | both | null
  confluence:
    cloud_id: null
    space_key: null
    parent_page_id: null
    artifacts:
      requirements:
        page_id: null
        page_url: null
        last_synced: null
      workshops:
        page_id: null
        page_url: null
        last_synced: null
      conceptual_model:
        page_id: null
        page_url: null
        last_synced: null
      pipeline_design:
        page_id: null
        page_url: null
        last_synced: null
      data_model:
        page_id: null
        page_url: null
        last_synced: null
      seed_data:
        page_id: null
        page_url: null
        last_synced: null
      mockups:
        page_id: null
        page_url: null
        last_synced: null
      viz_catalog:
        page_id: null
        page_url: null
        last_synced: null
      pipeline:
        page_id: null
        page_url: null
        last_synced: null
      orchestration:
        page_id: null
        page_url: null
        last_synced: null
      dbt:
        page_id: null
        page_url: null
        last_synced: null
      dbt_staging:
        page_id: null
        page_url: null
        last_synced: null
      dbt_integration:
        page_id: null
        page_url: null
        last_synced: null
      dbt_warehouse:
        page_id: null
        page_url: null
        last_synced: null
      semantic_layer:
        page_id: null
        page_url: null
        last_synced: null
      dashboards:
        page_id: null
        page_url: null
        last_synced: null
      dbtcharts:
        page_id: null
        page_url: null
        last_synced: null
      agents_schema:
        page_id: null
        page_url: null
        last_synced: null
      data_refactor:
        page_id: null
        page_url: null
        last_synced: null
      data_quality:
        page_id: null
        page_url: null
        last_synced: null
      uat:
        page_id: null
        page_url: null
        last_synced: null
      deployment:
        page_id: null
        page_url: null
        last_synced: null
      training:
        page_id: null
        page_url: null
        last_synced: null
      documentation:
        page_id: null
        page_url: null
        last_synced: null
  notion:
    parent_page_id: null
    artifacts:
      requirements:
        page_id: null
        page_url: null
        last_synced: null
      workshops:
        page_id: null
        page_url: null
        last_synced: null
      conceptual_model:
        page_id: null
        page_url: null
        last_synced: null
      pipeline_design:
        page_id: null
        page_url: null
        last_synced: null
      data_model:
        page_id: null
        page_url: null
        last_synced: null
      seed_data:
        page_id: null
        page_url: null
        last_synced: null
      mockups:
        page_id: null
        page_url: null
        last_synced: null
      viz_catalog:
        page_id: null
        page_url: null
        last_synced: null
      pipeline:
        page_id: null
        page_url: null
        last_synced: null
      orchestration:
        page_id: null
        page_url: null
        last_synced: null
      dbt:
        page_id: null
        page_url: null
        last_synced: null
      dbt_staging:
        page_id: null
        page_url: null
        last_synced: null
      dbt_integration:
        page_id: null
        page_url: null
        last_synced: null
      dbt_warehouse:
        page_id: null
        page_url: null
        last_synced: null
      semantic_layer:
        page_id: null
        page_url: null
        last_synced: null
      dashboards:
        page_id: null
        page_url: null
        last_synced: null
      dbtcharts:
        page_id: null
        page_url: null
        last_synced: null
      agents_schema:
        page_id: null
        page_url: null
        last_synced: null
      data_refactor:
        page_id: null
        page_url: null
        last_synced: null
      data_quality:
        page_id: null
        page_url: null
        last_synced: null
      uat:
        page_id: null
        page_url: null
        last_synced: null
      deployment:
        page_id: null
        page_url: null
        last_synced: null
      training:
        page_id: null
        page_url: null
        last_synced: null
      documentation:
        page_id: null
        page_url: null
        last_synced: null

# Where the data model comes from. `derived` builds it from the approved
# requirements. Any other value names an external model that already holds
# entities, keys and cardinality, which logical_model reads rather than restates.
model_source: derived
# Set by /wire:utils-modality-link when model_source is modality. The directory
# holding modality_project.yaml, relative to the repo root, or absolute for a
# client-owned repository.
modality_path: null

# Advisory preconditions the consultant chose to proceed without, recorded by
# specs/utils/precondition_gate.md Step 2b. Each entry: artifact, unmet
# precondition, reason, date. A skip that is logged is visible; an omitted gate
# is not.
advisory_skips: []

artifacts:
  # Optional first phase. Discover, define and agree what the numbers mean before
  # design bakes a definition in. Warning-level gate, not blocking.
  business_rules:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    domains_covered: []
    generated_date: null
  requirements:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  workshops:
    generate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  conceptual_model:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  pipeline_design:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  # Optional. Worth running when identity resolution, cardinality or attribution
  # is contested, so those decisions get reviewed before they arrive as dbt models.
  logical_model:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
  data_model:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  seed_data:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
    seed_file_count: null
  mockups:
    generate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  viz_catalog:
    generate: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  pipeline:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  orchestration:
    generate: not_started
    validate: not_started
    review: not_started
    orchestration_tool: null
    generated_date: null
    generated_files: []
    revision_history: []
  dbt:
    generate: not_started
    validate: not_started
    review: not_started
    models_count: null
    tests_count: null
    generated_date: null
    generated_files: []
    revision_history: []
  semantic_layer:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  dashboards:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  dbtcharts:
    generate: not_started
    validate: not_started
    review: not_started
    charts_dir: null
    boards: []
    generated_date: null
    generated_files: []
    revision_history: []
  agents_schema:
    generate: not_started
    validate: not_started
    review: not_started
    version: null
    destination: null
    providers: []
    skills: []
    workflow: null
    published: null
    generated_date: null
    generated_files: []
    revision_history: []
  data_refactor:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
    tables_refactored: null
    staging_models_updated: null
  data_quality:
    generate: not_started
    validate: not_started
    review: not_started
    tests_count: null
    generated_date: null
    generated_files: []
    revision_history: []
  uat:
    generate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  deployment:
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

notes:
  - "Project created: {{CREATED_DATE}}"

blockers: []

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
---

# Project Status: {{PROJECT_NAME}}

**Client**: {{CLIENT_NAME}}
**Project ID**: {{PROJECT_ID}}
**Type**: {{PROJECT_TYPE}}
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

## Current Phase: Requirements

## Next Action

Add source materials (SOW, requirements docs) to `.wire/{{PROJECT_ID}}_{{PROJECT_NAME}}/artifacts/`

Then run:
```
/wire:requirements-generate {{PROJECT_ID}}_{{PROJECT_NAME}}
```

## Artifact Status Summary

| Phase | Artifact | Generate | Validate | Review | Ready |
|-------|----------|----------|----------|---------|-------|
| **Requirements** | requirements | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | workshops | ⏸️ | - | ⏸️ | ❌ |
| **Design** | conceptual_model | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | pipeline_design | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | data_model | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | mockups | ⏸️ | - | ⏸️ | ❌ |
| | viz_catalog *(dashboard_first only)* | ⏸️ | - | - | ❌ |
| **Development** | pipeline | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | orchestration | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | dbt | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | seed_data *(dashboard_first only)* | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | semantic_layer | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | dashboards | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | data_refactor *(dashboard_first only)* | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Testing** | data_quality | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | uat | ⏸️ | - | ⏸️ | ❌ |
| **Deployment** | deployment | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Enablement** | training | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | documentation | ⏸️ | ⏸️ | ⏸️ | ❌ |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Failed | ⏸️ Not Started | ⚠️ Blocked | N/A (not applicable)

## Iterations

Ticket-sized work done inside this release through `/wire:work` (`specs/work.md`). One row per iteration, updated in place; the detail is in `iterations/<ticket>.md`.

| Ticket | Title | Branch | PR | State | Opened | Closed |
|--------|-------|--------|----|-------|--------|--------|

## Notes

[Add project-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|

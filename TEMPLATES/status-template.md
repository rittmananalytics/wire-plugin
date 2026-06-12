---
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
project_type: "{{PROJECT_TYPE}}"
client_name: "{{CLIENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "requirements"

jira:
  project_key: null
  structure: subtasks       # subtasks (default — one Task + 3 Sub-tasks per artifact) | single_issue (one Task per artifact, status transitions)
  epic_key: null
  artifacts:
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
    mockups:
      task_key: null
      generate_key: null
      review_key: null
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
      mockups:
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
      semantic_layer:
        page_id: null
        page_url: null
        last_synced: null
      dashboards:
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
      mockups:
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
      semantic_layer:
        page_id: null
        page_url: null
        last_synced: null
      dashboards:
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

artifacts:
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
  data_model:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  mockups:
    generate: not_started
    review: not_started
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
  mode: null              # null | local | managed
  coordinator_session: null
  last_orchestrated: null
  paused_at: null
  active_sessions: []
  completed_sessions: []

notes:
  - "Project created: {{CREATED_DATE}}"

blockers: []
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
| **Development** | pipeline | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | orchestration | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | dbt | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | semantic_layer | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | dashboards | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Testing** | data_quality | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | uat | ⏸️ | - | ⏸️ | ❌ |
| **Deployment** | deployment | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Enablement** | training | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | documentation | ⏸️ | ⏸️ | ⏸️ | ❌ |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Failed | ⏸️ Not Started | ⚠️ Blocked | N/A (not applicable)

## Notes

[Add project-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|

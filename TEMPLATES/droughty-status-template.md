---
release_id: "{{RELEASE_ID}}"
release_name: "{{RELEASE_NAME}}"
release_type: "droughty"
client_name: "{{CLIENT_NAME}}"
engagement_name: "{{ENGAGEMENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "setup"

droughty:
  context: "{{DROUGHTY_CONTEXT}}"   # discovery | post_dbt | full
  warehouse: null                    # bigquery | snowflake — set by droughty-setup

  setup:
    status: not_started              # not_started | complete
    pinned_version: null
    profile_name: null
    schemas: []
    lookml_output_path: null
    dbt_project_path: null
    completed_date: null

  introspect:
    status: not_started
    tables_found: null
    columns_found: null
    schemas_scanned: []
    pk_coverage_pct: null
    artifact: null
    completed_date: null

  dbml:
    status: not_started
    tables_in_diagram: null
    relationships_inferred: null
    artifact: null
    completed_date: null

  docs:
    status: not_started
    columns_documented: null
    low_confidence_count: null
    artifact: null
    completed_date: null

  qa:
    status: not_started
    checks_run: null
    issues_flagged: null
    critical_issues: null
    artifact: null
    completed_date: null

  stage:
    status: not_started              # bigquery only — not_applicable for snowflake
    models_generated: null
    source_dataset: null
    output_path: null
    completed_date: null

  dbt_tests:
    status: not_started
    tests_generated: null
    tables_covered: null
    merge_strategy: null
    completed_date: null

  lookml:
    status: not_started
    views_generated: null
    dimensions_generated: null
    measures_generated: null
    output_path: null
    completed_date: null

jira:
  project_key: null
  structure: subtasks
  epic_key: null
  artifacts:
    droughty_setup:
      task_key: null
    droughty_introspect:
      task_key: null
    droughty_dbml:
      task_key: null
    droughty_docs:
      task_key: null
    droughty_qa:
      task_key: null
    droughty_stage:
      task_key: null
    droughty_dbt_tests:
      task_key: null
    droughty_lookml:
      task_key: null

linear:
  team_id: null
  project_id: null
  mode: null
  artifacts:
    droughty_setup:
      issue_id: null
    droughty_introspect:
      issue_id: null
    droughty_dbml:
      issue_id: null
    droughty_docs:
      issue_id: null
    droughty_qa:
      issue_id: null
    droughty_stage:
      issue_id: null
    droughty_dbt_tests:
      issue_id: null
    droughty_lookml:
      issue_id: null
---

# Droughty Release Status — {{RELEASE_NAME}}

**Client**: {{CLIENT_NAME}}
**Release type**: Droughty schema introspection
**Context**: {{DROUGHTY_CONTEXT}}
**Created**: {{CREATED_DATE}}

---

## Phase: Setup

| Step | Status |
|------|--------|
| `droughty-setup` | not started |

---

## Phase: Schema Discovery

| Step | Status | Output |
|------|--------|--------|
| `droughty-introspect` | not started | — |
| `droughty-dbml` | not started | — |

---

## Phase: Documentation & Quality

| Step | Status | Output |
|------|--------|--------|
| `droughty-docs` | not started | — |
| `droughty-qa` | not started | — |

---

## Phase: Code Generation (post-dbt deploy)

| Step | Status | Output |
|------|--------|--------|
| `droughty-dbt-tests` | not started | — |
| `droughty-stage` | not started | — |
| `droughty-lookml` | not started | — |

---

## Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Schema inventory | `.wire/releases/{{RELEASE_NAME}}/artifacts/droughty/schema_inventory.md` | not started |
| DBML diagram | `.wire/releases/{{RELEASE_NAME}}/artifacts/droughty/*.dbml` | not started |
| Field descriptions | `.wire/releases/{{RELEASE_NAME}}/artifacts/droughty/field_descriptions/` | not started |
| QA report | `.wire/releases/{{RELEASE_NAME}}/artifacts/droughty/qa_report.md` | not started |
| Staging models | `[dbt_path]/models/staging/` | not started |
| Schema tests | `[dbt_path]/models/schema.yml` | not started |
| LookML base views | `[lookml_path]/views/generated/` | not started |

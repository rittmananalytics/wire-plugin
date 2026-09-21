---
release_id: "{{RELEASE_ID}}"
release_name: "{{RELEASE_NAME}}"
release_type: "droughty"
project_type: "droughty"   # the release-type YAML this release resolves against
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

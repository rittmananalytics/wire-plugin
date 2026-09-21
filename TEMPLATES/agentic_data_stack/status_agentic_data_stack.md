---
project_type: agentic_data_stack
project_id: YYYYMMDD_client_agentic_data_stack
client: Client Name
engagement_lead: Consultant Name
start_date: YYYY-MM-DD
target_launch_date: YYYY-MM-DD

# Warehouse configuration
warehouse: bigquery  # bigquery | snowflake | databricks | redshift
bi_tool: looker  # looker | tableau | powerbi | metabase | other
semantic_layer: dbt_semantic_layer  # dbt_semantic_layer | lookml | metricflow | none
dbt_project_path: ./  # relative or absolute path to dbt project
lookml_project_path: ~  # relative or absolute path to LookML project (looker bi_tool only)
primary_domain: ecommerce  # ecommerce | saas | marketing | finance | other
query_history_access: true  # true | false

# Domain configuration (update as audit completes)
domains: []  # populated during dataset_audit

# Eval configuration
eval_default_target: 90  # % pass rate required per domain
adversarial_review: true  # true | false

docstore:
  provider: null  # confluence | notion | both | null
  confluence:
    cloud_id: null
    space_key: null
    parent_page_id: null
    artifacts:
      dataset_audit:
        page_id: null
        page_url: null
        last_synced: null
      metric_audit:
        page_id: null
        page_url: null
        last_synced: null
      query_audit:
        page_id: null
        page_url: null
        last_synced: null
      governance_design:
        page_id: null
        page_url: null
        last_synced: null
      semantic_layer_design:
        page_id: null
        page_url: null
        last_synced: null
      canonical_models:
        page_id: null
        page_url: null
        last_synced: null
      lookml_views:
        page_id: null
        page_url: null
        last_synced: null
      semantic_layer:
        page_id: null
        page_url: null
        last_synced: null
      knowledge_skill:
        page_id: null
        page_url: null
        last_synced: null
      agent_config:
        page_id: null
        page_url: null
        last_synced: null
      eval_suite:
        page_id: null
        page_url: null
        last_synced: null
      adversarial_config:
        page_id: null
        page_url: null
        last_synced: null
      enablement:
        page_id: null
        page_url: null
        last_synced: null
  notion:
    parent_page_id: null
    artifacts:
      dataset_audit:
        page_id: null
        page_url: null
        last_synced: null
      metric_audit:
        page_id: null
        page_url: null
        last_synced: null
      query_audit:
        page_id: null
        page_url: null
        last_synced: null
      governance_design:
        page_id: null
        page_url: null
        last_synced: null
      semantic_layer_design:
        page_id: null
        page_url: null
        last_synced: null
      canonical_models:
        page_id: null
        page_url: null
        last_synced: null
      lookml_views:
        page_id: null
        page_url: null
        last_synced: null
      semantic_layer:
        page_id: null
        page_url: null
        last_synced: null
      knowledge_skill:
        page_id: null
        page_url: null
        last_synced: null
      agent_config:
        page_id: null
        page_url: null
        last_synced: null
      eval_suite:
        page_id: null
        page_url: null
        last_synced: null
      adversarial_config:
        page_id: null
        page_url: null
        last_synced: null
      enablement:
        page_id: null
        page_url: null
        last_synced: null

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

# Agentic Data Stack Release Status

## Phase 1 — Audit

### Dataset Audit
```yaml
dataset_audit:
  generate: not_started
  validate: not_started
  review: not_started
  tables_discovered: ~
  duplicate_groups: ~
  domains_assessed: ~
  overall_grade: ~
```

### Metric Audit
```yaml
metric_audit:
  generate: not_started
  validate: not_started
  review: not_started
  metrics_found: ~
  conflicts_found: ~
  coverage_pct: ~
```

### Query Audit
```yaml
query_audit:
  generate: not_started
  validate: not_started
  review: not_started
  queries_analysed: ~
  patterns_found: ~
  sl_coverage_pct: ~
  source: ~
```

## Phase 2 — Design

### Governance Design
```yaml
governance_design:
  generate: not_started
  validate: not_started
  review: not_started
  domains_covered: ~
  canonical_tables: ~
  tables_deprecated: ~
```

### Semantic Layer Design
```yaml
semantic_layer_design:
  generate: not_started
  validate: not_started
  review: not_started
  metrics_designed: ~
  domains_covered: ~
```

## Phase 3 — Build

### Canonical Models
```yaml
canonical_models:
  generate: not_started
  validate: not_started
  review: not_started
  models_canonicalized: ~
  models_deprecated: ~
  dbt_test_pass_rate: ~
```

### LookML Views
```yaml
lookml_views:
  generate: not_started  # set to skipped automatically if bi_tool != looker
  validate: not_started
  review: not_started
  views_created: ~
  views_updated: ~
  explores_updated: ~
  lookml_project_path: ~
```

### Semantic Layer
```yaml
semantic_layer:
  generate: not_started
  validate: not_started
  review: not_started
  metrics_implemented: ~
  sl_coverage_pct: ~
```

### Knowledge Skill
```yaml
knowledge_skill:
  generate: not_started
  validate: not_started
  review: not_started
  domains_covered: ~
  files_written: ~
  ci_check_added: ~
```

### Agent Config
```yaml
agent_config:
  generate: not_started
  validate: not_started
  review: not_started
  routing_tiers: 3
  adversarial_review: ~
  provenance_footer: ~
```

## Phase 4 — Validation

### Eval Suite
```yaml
eval_suite:
  generate: not_started
  validate: not_started
  review: not_started
  total_questions: ~
  domains_covered: ~
  overall_pass_rate: ~
  domains_passing: ~
  domains_failing: ~
```

### Adversarial Config
```yaml
adversarial_config:
  generate: not_started
  validate: not_started
  review: not_started
  mode: inline
  calibration_pass_rate: ~
```

## Phase 5 — Launch

### Launch Gate
```yaml
launch_gate:
  validate: not_started
  review: not_started
  domains_cleared: []
  domains_blocked: []
```

### Enablement
```yaml
enablement:
  generate: not_started
  validate: not_started
  review: not_started
```

## Execution Log

See `execution_log.md` for a full record of commands run.

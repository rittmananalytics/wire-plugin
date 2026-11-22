---
wire_schema: "1.0"
command: generate
artifact: semantic_layer
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: semantic_layer_design
    action: review
    outcome: approved
  - artifact: canonical_models
    action: validate
    outcome: PASS
auto_validate: false          # validate runs a real `dbt sl query` against the warehouse plus a LookML compile
delegates_to:
  - utils/precondition_gate
description: Implement semantic layer metrics from the approved design — MetricFlow YAML or LookML measures
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Semantic Layer Generate

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.

## Purpose

Implement the metric and dimension definitions from `semantic_layer_design.md` in the client's semantic layer — either as MetricFlow/dbt Semantic Layer YAML, LookML measures and explores, or both where dual-layer configuration is in use.

## Usage

```bash
/wire:ads_semantic-layer-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `canonical_models.review: approved`
- `semantic_layer_design.review: approved`

## Workflow

### Step 1: Read Design

1. Read `artifacts/semantic_layer_design.md` — full metric and dimension specifications
2. Read `artifacts/semantic_layer_design_decisions.md` — any name changes from review
3. Read status.md `semantic_layer` field to confirm implementation target

### Step 2: Implement — dbt Semantic Layer (MetricFlow)

For dbt Semantic Layer projects, create or extend semantic model YAML files collocated with the dbt mart models:

```yaml
# models/marts/orders/fct_orders.yml (semantic extension)

semantic_models:
  - name: orders
    description: "Order-level fact model — grain is one row per order"
    model: ref('fct_orders')
    
    entities:
      - name: order
        type: primary
        expr: order_pk
      - name: customer
        type: foreign
        expr: customer_fk
    
    dimensions:
      - name: order_date
        type: time
        type_params:
          time_granularity: day
        expr: order_date
      - name: channel
        type: categorical
        expr: channel
      - name: status
        type: categorical
        expr: status
    
    measures:
      - name: total_revenue
        description: "Net revenue post-returns and tax"
        agg: sum
        expr: net_revenue
      - name: order_count
        description: "Distinct confirmed orders"
        agg: count_distinct
        expr: order_pk

metrics:
  - name: total_revenue
    description: "Net revenue from confirmed orders"
    label: "Total Revenue"
    type: simple
    type_params:
      measure:
        name: total_revenue
        filter: "{{ Dimension('order__status') }} = 'confirmed'"
  
  - name: active_customers_30d
    description: "Customers with at least one order in the last 30 days"
    label: "Active Customers (30d)"
    type: simple
    type_params:
      measure:
        name: customer_count
```

Verify after writing:
```bash
dbt parse
dbt sl list metrics
```

### Step 3: Implement — LookML (Looker)

For Looker-primary projects, add measures to the canonical explore views:

```lookml
# views/fct_orders.view.lkml

view: fct_orders {
  sql_table_name: `project.analytics.fct_orders` ;;
  
  # Dimensions
  dimension: order_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.order_pk ;;
  }
  
  dimension_group: order {
    type: time
    timeframes: [date, week, month, quarter, year]
    datatype: date
    sql: ${TABLE}.order_date ;;
  }
  
  dimension: channel {
    type: string
    sql: ${TABLE}.channel ;;
  }
  
  # Measures
  measure: total_revenue {
    type: sum
    sql: ${TABLE}.net_revenue ;;
    filters: [status: "confirmed"]
    description: "Net revenue post-returns and tax from confirmed orders"
    label: "Total Revenue"
    value_format_name: usd
  }
  
  measure: order_count {
    type: count_distinct
    sql: ${TABLE}.order_pk ;;
    filters: [status: "confirmed"]
    description: "Count of confirmed orders"
    label: "Orders"
  }
}
```

Verify by running the LookML validator in the Looker IDE, or:
```bash
lookml-lint <lookml_project_path>
```

### Step 4: Verify Metric Coverage

After implementation, verify that the semantic layer now covers the target questions from the query audit:

```bash
# For dbt Semantic Layer
dbt sl query --metrics total_revenue --group-by order__order_date__month --limit 5

# For LookML — use the Looker API or Explore in the UI
```

For each must-have SL-gap question from query_audit, confirm it is now answerable via the semantic layer. Mark `sl_coverage_pct` in status.md.

### Step 5: Update Status

```yaml
semantic_layer:
  generate: complete
  generated_date: YYYY-MM-DD
  metrics_implemented: N
  sl_coverage_pct: X  # % of must-have query patterns now answerable
  platform: dbt_semantic_layer  # or lookml
```

## Edge Cases

### No Existing Semantic Layer

If `semantic_layer: none` in status.md, initialise the semantic layer first:
- **dbt SL**: follow `/wire:semantic_layer-generate` to scaffold MetricFlow setup
- **Looker**: create the explore file and initial views before adding metrics

### Metric Fails After Implementation

If `dbt sl query` returns an error for a newly defined metric, check:
1. Entity join paths are fully specified (no ambiguous foreign key paths)
2. The referenced measure exists in the semantic model
3. The filter expression uses valid dimension references

## Output

- Modified YAML or LookML files in `<dbt_project_path>` or `<lookml_project_path>`
- Updated `status.md`

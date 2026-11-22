---
wire_schema: "1.0"
command: generate
artifact: semantic_layer_design
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
  - artifact: governance_design
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Design metric definitions, dimensions, and entities for the semantic layer
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Semantic Layer Design Generate

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.

## Purpose

Produce the complete metric and dimension specification for the semantic layer build — covering new metrics to add, existing metrics to rename or consolidate, and the dimension model that supports them. This document is the input to `semantic_layer-generate`.

## Usage

```bash
/wire:ads_semantic-layer-design-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `governance_design.review: approved`
- `metric_audit.review: approved`
- `query_audit.review: approved` (provides prioritised gap list)

## Workflow

### Step 1: Read Inputs

1. `artifacts/governance_design.md` — canonical tables and their key fields
2. `artifacts/metric_audit_decisions.md` — conflict resolutions and agreed definitions
3. `artifacts/query_audit.md` — SL-gap and SL-extendable patterns, prioritised
4. Status.md `semantic_layer` field — which platform to target

### Step 2: Design First-Class Metrics

For each high-priority SL-gap and SL-extendable pattern from the query audit, design a metric definition. Use the canonical table fields from governance_design as the source.

For each metric, specify:

```yaml
# MetricFlow / dbt Semantic Layer format
metric:
  name: total_revenue
  description: "Net revenue (post-returns, post-tax) from confirmed orders"
  type: simple
  type_params:
    measure:
      name: net_amount
      agg: sum
      expr: net_amount
  filter: |
    {{ Dimension('order__status') }} = 'confirmed'
  label: "Total Revenue"
```

or for LookML:

```lookml
measure: total_revenue {
  type: sum
  sql: ${net_amount} ;;
  filters: [status: "confirmed"]
  description: "Net revenue post-returns and tax from confirmed orders"
  label: "Total Revenue"
  value_format_name: usd
}
```

### Step 3: Design Dimension Model

For each metric domain, specify the time and categorical dimensions needed:

```markdown
## Orders Domain — Dimension Model

**Entity:** order (primary key: order_id)

**Time dimensions:**
- order_date (DATE) — grain: day, week, month, quarter, year
- shipped_date (DATE) — grain: day, month

**Categorical dimensions:**
- channel (STRING) — acquisition channel
- status (STRING) — order status: pending, confirmed, cancelled, returned
- product_category (STRING) — join via dim_products
- customer_segment (STRING) — join via dim_customers
```

### Step 4: Identify Metric Dependencies

For complex metrics (ratios, running totals, period comparisons), document dependencies:

```markdown
## Derived Metrics

**conversion_rate:**
- Numerator: `orders_placed` (count distinct order_id WHERE status != 'cancelled')
- Denominator: `sessions` (from web_sessions domain — cross-domain join)
- Note: requires cross-domain join — verify MetricFlow / LookML join path

**revenue_vs_prior_period:**
- Base metric: `total_revenue`
- Comparison: prior period offset (30 days / same month prior year)
- Implementation: MetricFlow offset metric or LookML comparison period dimension
```

### Step 5: Write Semantic Layer Design Document

Write `.wire/<release-folder>/artifacts/semantic_layer_design.md` containing:
- Metric inventory by domain (new + modified)
- Dimension model per domain
- Derived metrics with dependency notes
- Implementation notes (MetricFlow YAML structure vs LookML measure format)
- Out-of-scope metrics (low-priority gaps deferred to future release)

### Step 6: Update Status

```yaml
semantic_layer_design:
  generate: complete
  generated_date: YYYY-MM-DD
  metrics_designed: N
  domains_covered: N
  platform: dbt_semantic_layer  # or lookml
```

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `semantic_layer_design`
- `artifact_name`: `Semantic Layer Design`
- `file_path`: `.wire/[release_folder]/artifacts/semantic_layer_design.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- `.wire/<release-folder>/artifacts/semantic_layer_design.md`
- Updated `status.md`

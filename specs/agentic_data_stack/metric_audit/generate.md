---
wire_schema: "1.0"
command: generate
artifact: metric_audit
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Inventory existing metric definitions, identify conflicts and coverage gaps
argument-hint: <release-folder>

delegates_to:
  - utils/definition_extract
---

# Agentic Data Stack — Metric Audit Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Map every metric definition that exists across the client's semantic layer, BI tool, and ad-hoc SQL — then identify definition conflicts, coverage gaps against the most common analytical questions, and which metrics are safe to promote as first-class semantic layer citizens.

## Usage

```bash
/wire:ads_metric-audit-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `.wire/<release-folder>/status.md` with `project_type: agentic_data_stack`
- Access to at least one of: dbt Semantic Layer / MetricFlow YAML, LookML project, BI tool metric definitions, or dbt schema.yml measures

## Workflow

### Step 1: Read Context

1. Read status.md for `semantic_layer`, `bi_tool`, `dbt_project_path`, `warehouse`
2. If dataset_audit is complete, read `artifacts/dataset_audit.md` for domain list

### Step 2: Enumerate Metric Definitions

Follow `specs/utils/definition_extract.md`, Step 2. It carries the enumeration
across dbt Semantic Layer / MetricFlow, LookML and dbt `schema.yml` measures, and
the per-definition fields to record.

`--import <path>` is available here too, for a client whose BI-layer logic sits in
a system Wire cannot read.

### Step 3: Identify Definition Conflicts

Follow `specs/utils/definition_extract.md`, Step 3. It carries the conflict
taxonomy: filter difference, aggregation difference, grain difference, name
collision.

For each conflict, document both definitions and flag for governance_design
resolution.

**Where `artifacts/business_rules.yaml` exists in the release**, read the agreed
decisions from it rather than re-deriving the conflict as open. A rule already
carrying a decision and a named approver is settled, and re-opening it here would
put a second, weaker recommendation next to a signed-off one.
### Step 4: Identify Coverage Gaps

Compare the metric inventory against the most frequently asked analytics questions. Derive the question list from:

1. `artifacts/query_audit.md` (if query_audit has already run)
2. The SOW and engagement context — any KPIs mentioned
3. Direct consultation: ask the data team "What are the ten questions your executives ask most?"

For each high-frequency question, classify:
- **Covered**: a semantic metric answers it directly
- **Partial**: a metric exists but needs modification (missing dimension, different time grain)
- **Gap**: no metric covers this — raw SQL required today

### Step 5: Write Metric Audit Document

Write `.wire/<release-folder>/artifacts/metric_audit.md`:

```markdown
---
artifact: metric_audit
generated: YYYY-MM-DD
---

# Metric Audit

## Summary

| Metric | Count |
|---|---|
| Total metric definitions found | N |
| Definition conflicts identified | N |
| High-frequency questions covered by semantic layer | N/N (X%) |
| New metrics recommended | N |

## Metric Inventory

### [Domain: Orders]

| Metric | Source | Definition | Conflicts |
|---|---|---|---|
| total_revenue | dbt SL | SUM(net_amount) on fct_orders | ⚠️ Looker uses gross_amount |
| order_count | LookML | COUNT(DISTINCT order_id) | None |

## Definition Conflicts

### Revenue Definition Conflict

**dbt Semantic Layer:** `SUM(net_amount)` — excludes tax and returns  
**Looker:** `SUM(gross_amount)` — pre-deduction gross  

**Recommendation:** Standardise on `SUM(net_amount)` as `total_revenue`; add `gross_revenue` as a separate named metric to avoid silent mismatches.

## Coverage Gap Analysis

| Question | Status | Gap Detail |
|---|---|---|
| Revenue by channel last 30 days | ✅ Covered | `total_revenue` + `channel` dimension |
| Active customers this month | ⚠️ Partial | Metric exists; 30-day window missing |
| Marketing spend by campaign | ❌ Gap | No metric — raw SQL against ad tables required |

## Recommended New Metrics

| Metric | Domain | Priority | Definition |
|---|---|---|---|
| active_customers_30d | customers | High | COUNT DISTINCT customer_id WHERE last_order >= CURRENT_DATE - 30 |
```

### Step 6: Update Status

```yaml
metric_audit:
  generate: complete
  generated_date: YYYY-MM-DD
  metrics_found: N
  conflicts_found: N
  coverage_pct: X
```

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `metric_audit`
- `artifact_name`: `Metric Audit`
- `file_path`: `.wire/[release_folder]/artifacts/metric_audit.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Edge Cases

### No Semantic Layer Exists

If `semantic_layer: none` in status.md, the metric audit is primarily a gap analysis. Record all BI tool measures (Looker measures, Tableau calculated fields, etc.) as the existing definitions, grade coverage against the question list, and set `semantic_layer_maturity: none` in the audit. The semantic_layer_design phase will build from scratch.

### LookML Access Not Available

If the consultant cannot access the LookML project directly, ask them to run:
```bash
lookml-lint --list-measures <project_path>
```
or export a list of explores and their measures from the Looker IDE.

## Output

- `.wire/<release-folder>/artifacts/metric_audit.md`
- Updated `status.md`

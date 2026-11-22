---
wire_schema: "1.0"
command: review
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
  - artifact: semantic_layer_design
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Stakeholder sign-off on metric definitions and dimension model before implementation
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Semantic Layer Design Review

## Purpose

Confirm metric definitions with the data team and business stakeholders before implementation. Metric names and definitions are difficult to change after the semantic layer is built — getting them right here saves significant rework.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for prior conversations about metric naming, KPI definitions, or disagreements about "what does X mean" that have come up in stakeholder meetings.

### Step 2: Present the Metric List

Group by domain. For each metric, show: name, definition, and example output:

```
## Semantic Layer Design Review

### Orders Domain — 8 metrics

| Metric | Definition | Example |
|---|---|---|
| total_revenue | SUM(net_amount) on confirmed orders | $1.2M last month |
| order_count | COUNT DISTINCT order_id | 8,432 last month |
```

### Step 2: Walk Through Conflict Resolutions

For each metric that resolved a conflict from the metric audit, confirm the agreed definition is correctly implemented.

### Step 3: Confirm Metric Names

Business stakeholders often have strong views on naming. "Gross Merchandise Value" vs "Revenue" vs "Total Sales" matters to them. Confirm the display labels even if the technical names are fixed.

### Step 4: Record Decisions

Write `.wire/<release-folder>/artifacts/semantic_layer_design_decisions.md` with:
- Any metric name changes agreed in review
- Any definition adjustments
- Any metrics added or deferred

### Step 5: Update Status

```yaml
semantic_layer_design:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```

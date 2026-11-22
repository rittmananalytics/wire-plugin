---
wire_schema: "1.0"
command: review
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
preconditions:
  - artifact: metric_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Stakeholder sign-off on metric definitions, conflicts, and coverage gap priorities
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Metric Audit Review

## Purpose

Agree canonical metric definitions with the data team and business stakeholders. Resolve conflicts before they are encoded into the semantic layer. Prioritise the coverage gaps so the semantic_layer_design phase addresses the highest-value questions first.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for prior discussions about metric definitions, "what does X mean", or disagreements about numbers in executive reports.

### Step 2: Present Conflicts First

Lead with conflicts — these are the highest-risk items and the ones most likely to have strong stakeholder opinions:

```
## Metric Audit Review

### [N] Conflicts Requiring Resolution

**1. Revenue definition conflict**

| Source | Definition | Implication |
|---|---|---|
| dbt Semantic Layer | SUM(net_amount) — net of returns and tax | Lower number |
| Looker | SUM(gross_amount) — pre-deduction | Higher number |

**Proposed resolution:** Standardise on net_amount as `total_revenue`. Retire Looker gross measure or rename it `gross_revenue` to avoid silent swaps.

Which definition should be canonical?
```

### Step 3: Prioritise Coverage Gaps

Present the gap analysis and ask the reviewer to prioritise which gaps to close in this release vs defer:

```
### Coverage Gaps — Priority Ranking

| Question | Status | Priority (reviewer to confirm) |
|---|---|---|
| Active customers this month | ⚠️ Partial | Must-have / Nice-to-have / Defer |
| Marketing spend by campaign | ❌ Gap | Must-have / Nice-to-have / Defer |
```

### Step 4: Record Decisions

Write `.wire/<release-folder>/artifacts/metric_audit_decisions.md` recording:
- Conflict resolutions with the agreed canonical definition
- Coverage gap priorities (must-have vs nice-to-have vs defer)
- Any new metric names agreed (business stakeholders often have strong naming preferences)

### Step 5: Update Status

```yaml
metric_audit:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```

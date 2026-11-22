---
wire_schema: "1.0"
command: review
artifact: governance_design
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Stakeholder sign-off on canonical model, deprecation plan, and tiering policy
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Governance Design Review

## Purpose

Get formal sign-off on the canonical dataset model and deprecation schedule from the data platform owner. This is the highest-stakes review in the release — changes to canonical table selections after this point cascade through every downstream artifact.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for any prior conversations about data ownership, table deprecation, or "single source of truth" initiatives.

### Step 2: Present Governance Design

Lead with the deprecation schedule — it's the most operationally impactful element:

```
## Governance Design Review

### Deprecation Schedule

[N] tables will be sunset over the next 90 days. All have canonical replacements.

| Table | Sunset date | Replace with | Teams affected |
|---|---|---|---|
| orders_raw | YYYY-MM-DD | fct_orders | Finance, Marketing |

⚠️  The following tables have active dependencies that need migration before sunset:
- orders_raw: 3 Looker Looks, 1 Scheduled Extract

### Canonical Model Summary

[One line per domain: "orders → fct_orders (owner: data-platform)"]
```

### Step 3: Confirm Ownership

Walk through the ownership register. Data platform owners often push back on ownership assignments — resolve disputes now rather than during the enablement phase.

### Step 4: Agree Deprecation Timeline

Present the proposed 90-day sunset for each table. Negotiate extensions for tables with complex dependencies. Record final dates.

### Step 5: Record Sign-off

Write `.wire/<release-folder>/artifacts/governance_design_signoff.md`:

```markdown
# Governance Design — Sign-off

Approved by: [Name], [Role]  
Date: YYYY-MM-DD  

Canonical model: approved for N domains  
Deprecation schedule: approved with the following modifications:
- orders_raw sunset extended to YYYY-MM-DD due to Finance team migration dependency

Tiering policy: approved
```

### Step 6: Update Status

```yaml
governance_design:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```

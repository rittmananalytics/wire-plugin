---
wire_schema: "1.0"
command: review
artifact: lookml_views
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
  - artifact: lookml_views
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Looker admin and data team sign-off on new and updated LookML view files before semantic layer metric build
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — LookML Views Review

## Purpose

Get confirmation from the Looker admin and data team that the generated view files correctly expose the canonical models, are wired into the right explores, and are ready to receive metric definitions from `ads_semantic-layer-generate`.

The audience is technical — Looker developers and analytics engineers, not business stakeholders.

## Usage

```bash
/wire:ads_lookml-views-review YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `lookml_views.validate: complete`

## Skip Condition

If `lookml_views.generate: skipped` in status.md, output:

```
LookML Views — Review Skipped (bi_tool is not looker)
```

Update status and stop.

---

## Workflow

### Step 1: Search Meeting Context

Before presenting the review summary, search Fathom for recent calls that discussed LookML structure, explore design, or Looker project conventions for this client. Surface any decisions or constraints that bear on view file design.

---

### Step 2: Present Review Summary

```
## LookML Views Review

### Views Created (N)

| View | File | Canonical Model | Explore |
|---|---|---|---|
| fct_orders | views/fct_orders.view.lkml | fct_orders | orders_explore |
| dim_customers | views/dim_customers.view.lkml | dim_customers | orders_explore |

### Views Updated (N)

| View | File | Changes |
|---|---|---|
| fct_subscriptions | views/fct_subscriptions.view.lkml | net_mrr renamed from mrr_amount; churn_date added |

### Validation Results

- LookML syntax: PASS (0 errors)
- Column references: PASS (0 orphaned)
- Primary keys: PASS
- Explore wiring: PASS (all views reachable)

### What Happens Next

ads_semantic-layer-generate will add measure definitions to these view files
(no structural changes — measures only). Confirm the view scaffolding is
correct before proceeding.
```

---

### Step 3: Review Questions

Ask the Looker admin and data team to confirm:

1. **Explore coverage** — are all new views in the correct explores? Are there existing explores that also need access to the new views?
2. **View naming** — do the generated view names follow the project's existing convention?
3. **Label conventions** — do dimension labels match how the business refers to these fields?
4. **Hidden fields** — are the correct FK and technical columns marked `hidden: yes`?
5. **Missing dimensions** — are there ARRAY/STRUCT columns (skipped in generation) that need manual view expansion before metrics can reference them?

---

### Step 4: Handle Feedback

For each piece of feedback, apply changes to the view files and re-run `ads_lookml-views-validate` before returning to this review.

Common changes at this stage:
- Rename a view or dimension to match existing project conventions
- Add a missing explore join
- Adjust `hidden` flags
- Resolve a `# TODO: confirm primary_key` comment

Do not add measures — any metric-level feedback belongs in the `ads_semantic-layer-design` review, which has already been completed. Log it in `lookml_views_notes.md` under a "Deferred to semantic layer" section instead.

---

### Step 5: Record Sign-off

```yaml
lookml_views:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
  notes: ""
```

Once approved, `ads_semantic-layer-generate` can proceed.

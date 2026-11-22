---
wire_schema: "1.0"
command: generate
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
  - artifact: dataset_audit
    action: review
    outcome: approved
  - artifact: metric_audit
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Produce the canonical dataset model, deprecation plan, ownership register, and tiering policy
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Governance Design Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Convert the dataset audit findings into a concrete governance model: one canonical table per entity, a deprecation schedule, ownership assignments, and a tiering policy that the agent_config will enforce. This document is the authority that makes concept-entity ambiguity resolvable.

## Usage

```bash
/wire:ads_governance-design-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `dataset_audit.review: approved`
- `dataset_audit_decisions.md` exists with confirmed canonical table selections

## Workflow

### Step 1: Read Audit Decisions

Read:
- `.wire/<release-folder>/artifacts/dataset_audit.md`
- `.wire/<release-folder>/artifacts/dataset_audit_decisions.md`
- `.wire/<release-folder>/artifacts/metric_audit_decisions.md` (if approved)

### Step 2: Build the Canonical Dataset Model

For each domain, produce a canonical model entry:

```markdown
## Domain: Orders

**Canonical entity table:** `project.analytics.fct_orders`  
**Grain:** One row per order  
**Owner:** data-platform@company.com  
**Tier:** Curated  

**Key fields:**
| Field | Type | Description |
|---|---|---|
| order_id | STRING | Unique order identifier (surrogate key) |
| customer_id | STRING | FK to dim_customers |
| order_date | DATE | Date order was placed |
| net_revenue | NUMERIC | Revenue net of returns and tax |
| gross_revenue | NUMERIC | Pre-deduction gross amount |
| channel | STRING | Acquisition channel |

**Deprecation schedule:**
| Table | Sunset date | Migration notes |
|---|---|---|
| orders_raw | YYYY-MM-DD (+90 days) | Replace with fct_orders |
| revenue_v2 | YYYY-MM-DD (+90 days) | Replace with fct_orders |
```

Repeat for every domain confirmed in the audit review.

### Step 3: Write the Tiering Policy

Define the three-tier routing rule explicitly — this becomes a section in the agent_config skill:

```markdown
## Tiering Policy

When answering an analytical question, the agent MUST follow this routing order:

1. **Semantic tier** — check for a defined metric in the semantic layer first
   - dbt Semantic Layer: call `dbt sl query --metrics <metric_name>`
   - LookML / Looker: use the defined measure in the canonical explore
   - If a metric exists and answers the question: use it. Do not fall through to raw SQL.

2. **Curated tier** — if no semantic metric covers the question
   - Use only canonical tables listed in this governance design
   - Do not query deprecated tables even if they are more convenient
   - Write SQL against the canonical table and note the tier in the provenance footer

3. **Raw tier** — only if curated tables cannot answer the question
   - Document why the curated/semantic tiers were insufficient
   - Flag the gap as a potential semantic layer addition
   - Include the provenance footer tier: "Raw"
```

### Step 4: Write the Ownership Register

```markdown
## Ownership Register

| Domain | Canonical Table | Owner | Slack / contact | Review cadence |
|---|---|---|---|---|
| orders | fct_orders | data-platform | #data-platform | Monthly |
| customers | dim_customers | analytics-eng | #analytics | Monthly |
| marketing | fct_ad_spend | marketing-analytics | #marketing-data | Bi-weekly |
```

### Step 5: Write Governance Design Document

Write `.wire/<release-folder>/artifacts/governance_design.md` containing:
- Executive summary (one paragraph)
- Canonical dataset model (one entry per domain)
- Tiering policy
- Deprecation schedule with dates
- Ownership register
- Implementation checklist for canonical_models phase

### Step 6: Update Status

```yaml
governance_design:
  generate: complete
  generated_date: YYYY-MM-DD
  domains_covered: N
  tables_deprecated: N
  canonical_tables: N
```

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `governance_design`
- `artifact_name`: `Governance Design`
- `file_path`: `.wire/[release_folder]/artifacts/governance_design.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- `.wire/<release-folder>/artifacts/governance_design.md`
- Updated `status.md`

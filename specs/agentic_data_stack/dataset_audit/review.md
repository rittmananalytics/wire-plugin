---
wire_schema: "1.0"
command: review
artifact: dataset_audit
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Stakeholder sign-off on dataset audit findings and deprecation recommendations
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Dataset Audit Review

## Purpose

Present dataset audit findings to the data platform owner and domain leads. Agree which tables are canonical, which are deprecated, and confirm the governance maturity assessment before proceeding to design.

## Usage

```bash
/wire:ads_dataset-audit-review YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `dataset_audit.validate: complete` with result `pass` or `pass_with_warnings`

## Workflow

### Step 1: Surface Meeting Context

Search Fathom (if available) for any prior conversations about data quality, table proliferation, or "which table should we use":

```
Search Fathom for: "[client] canonical tables OR data governance OR which table OR revenue definition"
```

Surface any relevant excerpts — stakeholders may have strong prior opinions about specific tables.

### Step 2: Present Findings

Present the audit findings as a structured summary, leading with the governance grade and the highest-risk duplicate groups:

```
## Dataset Audit Review

**Overall governance grade: [B]**
**[N] tables across [N] domains**
**[N] near-duplicate groups — [N] tables recommended for deprecation**

### Domain Grades

| Domain | Grade | Top Issue |
|---|---|---|
| orders | B | 3 competing revenue definitions |
| marketing | C | No dbt management — raw tables primary |
| ... | | |

### Highest-Priority Deprecation Recommendations

1. **Revenue/orders group** (4 tables → 1 canonical)
   - Retain: `fct_orders`
   - Deprecate: `orders_raw`, `revenue_v2`, `fct_orders_v3`
   
2. **[Next group]**
```

### Step 3: Gather Reviewer Feedback

Ask the reviewer to confirm or modify:

1. **Canonical table selections** — Are the proposed canonical tables correct? Any disagreements?
2. **Deprecation list** — Are all proposed deprecations safe? Any tables on the list still actively used by upstream processes?
3. **Domain grades** — Do the governance grades reflect the team's own assessment? Any surprises?
4. **Missing domains** — Any business domains not covered in the audit?
5. **Timeline** — Is the 90-day deprecation sunset acceptable? Any tables needing longer notice?

### Step 4: Record Decisions

Record all reviewer decisions in `.wire/<release-folder>/artifacts/dataset_audit_decisions.md`:

```markdown
# Dataset Audit — Review Decisions

Reviewer: [Name], [Role]
Review date: YYYY-MM-DD

## Canonical Table Confirmations

| Domain | Canonical Table | Decision | Notes |
|---|---|---|---|
| orders | fct_orders | Confirmed | |
| customers | dim_customers | Modified — use dim_customers_v2 | v2 has GDPR fields required |

## Deprecation List Adjustments

Removed from deprecation list:
- `orders_raw`: Still used by finance team's Looker Looks — needs migration plan before sunset

Added to deprecation list:
- `customer_snapshot_2023`: Confirmed stale, safe to archive

## Governance Grade Adjustments

- marketing: D → C — consultant confirmed 2 dbt models exist but undocumented

## Open Items for Governance Design Phase

- Finance team dependency on `orders_raw` needs dedicated migration sprint
- Marketing domain needs dbt onboarding before canonical models phase
```

### Step 5: Update Status

```yaml
dataset_audit:
  review: approved  # approved | approved_with_conditions | rejected
  reviewer: Name
  review_date: YYYY-MM-DD
  decisions_recorded: true
```

### Step 6: Confirm Next Steps

```
## Dataset Audit Approved ✓

Canonical tables confirmed for [N] domains. [N] tables cleared for deprecation.

**Conditions / open items:**
- [Any conditions to resolve before proceeding]

**Next steps:**
- /wire:ads_metric-audit-review — if metric audit is complete
- /wire:ads_governance-design-generate — once all three audits are approved
```

## Edge Cases

### Reviewer Rejects Canonical Recommendations

Record the rejection with the reviewer's preferred canonical table. Re-run validate against the updated selections before proceeding to governance design.

### Deprecation Dispute

If a table is contested — multiple teams claim to need it — escalate to the platform owner. Do not proceed with canonical_models until the dispute is resolved. Record the open item in the decisions document.

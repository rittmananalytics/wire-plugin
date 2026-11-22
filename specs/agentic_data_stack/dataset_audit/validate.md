---
wire_schema: "1.0"
command: validate
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify dataset audit completeness, duplicate detection, and tier classification accuracy
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Dataset Audit Validate

## Purpose

Check that the dataset audit is complete, the near-duplicate detection is sound, and the governance tier classifications are defensible. Produce a PASS/FAIL report before the audit goes to stakeholder review.

## Usage

```bash
/wire:ads_dataset-audit-validate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `dataset_audit.generate: complete` in status.md
- `.wire/<release-folder>/artifacts/dataset_audit.md` exists

## Validation Checks

### Completeness Checks

- [ ] Table count matches warehouse information_schema row count (within 5% — some views/temp tables expected to differ)
- [ ] Every domain mentioned in the SOW or engagement context is represented
- [ ] Every table in the audit has a tier classification (Semantic / Curated / Raw)
- [ ] Every near-duplicate group has exactly one canonical candidate identified
- [ ] Governance grade assigned to every domain

### Near-Duplicate Quality Checks

- [ ] No canonical candidate is a raw or undocumented table (unless no managed alternative exists — must be noted)
- [ ] Duplicate groups are genuinely overlapping, not just similarly named tables with different grain
- [ ] All tables flagged for deprecation have a documented canonical replacement
- [ ] No table is flagged for deprecation without a stated justification

### Tier Classification Checks

- [ ] Semantic tier: every table classified Semantic has a verifiable metric definition in the semantic layer
- [ ] Curated tier: every table classified Curated has evidence of dbt management (appears in `dbt ls` output or has a documented schema.yml entry)
- [ ] Raw tier: tables classified Raw are not primary query targets in recent query history (if query_audit has run)

### Governance Grade Calibration

- [ ] Grade A domains genuinely have >80% semantic layer coverage
- [ ] Grade D domains have documented evidence of widespread duplication
- [ ] No domain is graded higher than C if it has undocumented canonical tables

## Automated Checks

Where possible, run these automatically:

```bash
# Check every table in the audit has a tier classification
grep -c "| Semantic \|| Curated \|| Raw " artifacts/dataset_audit.md

# Check no canonical candidate is raw
grep -A2 "Canonical — retain" artifacts/dataset_audit.md | grep -i "raw\|undocumented" && echo "WARNING: Raw table marked canonical"

# Check all duplicate groups have a recommendation
grep -c "Recommendation:" artifacts/dataset_audit.md
```

## Output Format

```markdown
## Dataset Audit Validation

**Result: PASS / FAIL / PASS WITH WARNINGS**

### Checks Run: N
### Checks Passed: N
### Checks Failed: N

### Failed Checks

| Check | Detail | Severity |
|---|---|---|
| Curated tier without dbt evidence | `revenue_summary` classified Curated but not in dbt ls output | High |

### Warnings

| Warning | Detail |
|---|---|
| Canonical candidate is undocumented | `orders_combined` marked canonical for orders domain but has no schema.yml entry |

### Recommended Actions Before Review

1. Verify `revenue_summary` dbt management status
2. Add schema.yml documentation for `orders_combined` before proceeding to canonical_models phase
```

## Status Update

```yaml
dataset_audit:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass  # pass | pass_with_warnings | fail
  checks_run: N
  checks_passed: N
```

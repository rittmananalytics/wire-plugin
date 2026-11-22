---
wire_schema: "1.0"
command: utility
artifact: ads_audit_all
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Run all three agentic data stack audits in parallel using dynamic workflow
argument-hint: <release-folder>

---

# Wire Utility — Analytics Audit All

## Purpose

Fan out all three agentic data stack audits (dataset_audit, metric_audit, query_audit) in parallel to reduce the time spent in the audit phase. The three audits are largely independent — running them sequentially adds unnecessary wall-clock time.

## Usage

```bash
/wire:ads-audit-all YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `.wire/<release-folder>/status.md` with `project_type: agentic_data_stack`
- Warehouse access configured
- dbt project path available (enriches all three audits)

## Workflow

### Step 1: Confirm Prerequisites

Read status.md and confirm all three audits are `not_started`. If any are already complete, skip those and run only the remaining ones.

### Step 2: Cost and Token Prompt

Running three audits in parallel uses approximately 3× the tokens of a single audit. Present the trade-off:

```
## Analytics Audit — Parallel Run

Running all three audits in parallel will:
- Reduce audit phase from ~3 hours to ~1 hour
- Use approximately 3× more context tokens this session

Options:
A) Run all three in parallel (recommended — saves ~2 hours)
B) Run sequentially — dataset_audit first, then metric_audit, then query_audit
```

If the user selects B, run `/wire:ads_dataset-audit-generate`, then `/wire:ads_metric-audit-generate`, then `/wire:ads_query-audit-generate` in sequence.

### Step 3: Parallel Execution (Option A)

Invoke all three generate commands concurrently as subagents:

**Subagent 1 — Dataset Audit:**
Follow the full workflow in `agentic_data_stack/dataset_audit/generate.md`

**Subagent 2 — Metric Audit:**
Follow the full workflow in `agentic_data_stack/metric_audit/generate.md`

**Subagent 3 — Query Audit:**
Follow the full workflow in `agentic_data_stack/query_audit/generate.md`

All three write to separate artifact files — no conflicts.

### Step 4: Consolidate Results

After all three complete, output a consolidated audit summary:

```
## Analytics Audit Complete

All three audits completed successfully.

### Summary

| Audit | Key Finding |
|---|---|
| Dataset | N tables, N duplicate groups, overall grade: B |
| Metric | N metrics found, N conflicts, X% coverage |
| Query | N patterns, X% SL-covered today |

### Recommended Next Steps

1. /wire:ads_dataset-audit-validate — check audit completeness
2. /wire:ads_metric-audit-validate
3. /wire:ads_query-audit-validate
4. Then schedule three review sessions with domain stakeholders

Or proceed directly to reviews if you have high confidence in audit quality:
/wire:ads_dataset-audit-review → /wire:ads_metric-audit-review → /wire:ads_query-audit-review
```

## Output

- All three audit artifacts written
- Updated status.md for all three audits

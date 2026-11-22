---
wire_schema: "1.0"
command: generate
artifact: analytics_enablement
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
  - artifact: launch_gate
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate user training materials and handover documentation for the agentic data stack
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Enablement Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce the user-facing documentation and data team handover materials for the agentic data stack. Users need to know what to ask, what the agent's limitations are, and how to interpret the provenance footer. The data team needs to know how to maintain the skill files as models evolve.

## Usage

```bash
/wire:ads_analytics-enablement-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `launch_gate.review: approved`

## Workflow

### Step 1: Generate User Guide

Write `.wire/<release-folder>/artifacts/agentic_data_stack_user_guide.md`:

```markdown
# [Client] Agentic Data Stack — User Guide

## What It Does

The agentic data stack answers business questions about your data platform in plain English. 
Ask it like you'd ask a data analyst.

## How to Ask Good Questions

**Be specific about time periods:**
- ✅ "Revenue last month" / "Revenue in Q1 2025"
- ❌ "Recent revenue" (ambiguous)

**Name the metric you want:**
- ✅ "Total revenue" / "Order count" / "Active customers"
- ❌ "How are we doing?" (too broad)

**Specify dimensions if you want a breakdown:**
- ✅ "Revenue by channel last quarter"
- ❌ "Revenue" (returns aggregate only)

## Understanding the Source Footer

Every answer includes:
```
Source tier: Semantic | Curated | Raw
Dataset: [table or metric name]
Freshness: [last updated timestamp]
Domain owner: [contact email]
```

**Semantic**: The answer comes from a defined business metric. Highest confidence.  
**Curated**: The answer comes from a governed dbt model. High confidence.  
**Raw**: The answer required ad-hoc SQL. Use with care — verify against a dashboard 
before including in external reports.

## What the Agent Can and Cannot Do

**Can do:**
- Answer questions about [list cleared domains]
- Break down metrics by standard dimensions (date, channel, region, category)
- Identify top-N or bottom-N rankings

**Cannot do (yet):**
- [List blocked domains] — launching in [second wave date]
- Multi-step attribution modelling
- Real-time data (data freshness is [X hours] behind live)
- Write to or modify any data

## When to Double-Check

Always verify against your canonical dashboard or with the domain owner before:
- Including a number in an external report or client presentation
- Making a significant budget or staffing decision
- The answer surprises you significantly
```

### Step 2: Generate Data Team Maintenance Guide

Write `.wire/<release-folder>/artifacts/agentic_data_stack_maintenance_guide.md`:

```markdown
# Agentic Data Stack — Maintenance Guide

## How the Agent Works

The agentic data stack uses three sources:
1. **Semantic layer** (dbt SL / LookML) — defined metrics
2. **DOMAIN_REFERENCE.md files** — per-domain knowledge, collocated with dbt models
3. **Canonical dbt models** — direct SQL fallback

## How to Keep It Accurate

### When you change a dbt model

If you modify a canonical mart model, update the collocated DOMAIN_REFERENCE.md:
- Check the "Key fields" table is still accurate
- Check the "Common Questions" examples still return correct results
- Check the "Known Limitations" section still applies

The CI check will warn if a model SQL changes without the reference file changing.

### When you add a new metric

After adding a metric to the semantic layer:
1. Add it to the relevant DOMAIN_REFERENCE.md "Semantic Layer Metrics" table
2. Add 1–2 example questions covering the new metric to the eval suite
3. Run `./eval/run_evals.sh <domain>` to confirm accuracy is maintained

### Monthly accuracy check

Run the full eval suite monthly:
```bash
cd <dbt_project_path> && ./.claude/eval/run_evals.sh all
```

If any domain drops below its target, investigate immediately — don't wait for users 
to report wrong answers.

## Key Contacts

| Domain | Owner | Contact |
|---|---|---|
| orders | Data Platform | data-platform@company.com |
| customers | Analytics Engineering | analytics@company.com |
```

### Step 3: Update Status

```yaml
enablement:
  generate: complete
  generated_date: YYYY-MM-DD
  user_guide: complete
  maintenance_guide: complete
```

### Step 4: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `enablement`
- `artifact_name`: `Enablement`
- `file_path`: `.wire/[release_folder]/artifacts/agentic_data_stack_user_guide.md`
- Also sync: `.wire/[release_folder]/artifacts/agentic_data_stack_maintenance_guide.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- `.wire/<release-folder>/artifacts/agentic_data_stack_user_guide.md`
- `.wire/<release-folder>/artifacts/agentic_data_stack_maintenance_guide.md`
- Updated `status.md`

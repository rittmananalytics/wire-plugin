---
wire_schema: "1.0"
command: generate
artifact: adversarial_config
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
  - artifact: agent_config
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Configure and test the adversarial review sub-agent
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Adversarial Config Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Configure, calibrate, and test the adversarial review sub-agent — the Claude instance that challenges every answer before it reaches the user. Anthropic measured a 6% accuracy gain from this step (at 32% higher token cost and 72% higher latency). This command documents the trade-off for the client and configures it to their latency and cost tolerance.

## Usage

```bash
/wire:ads_adversarial-config-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `agent_config.review: approved`
- `eval_suite.generate: complete`

## Workflow

### Step 1: Discuss the Trade-off

Present the trade-off to the consultant and note the client's decision:

```
## Adversarial Review — Configuration Decision

Based on Anthropic's measured results on their own analytics platform:

| Configuration | Accuracy gain | Token cost increase | Latency increase |
|---|---|---|---|
| With adversarial review | +6% | +32% | +72% |
| Without adversarial review | baseline | baseline | baseline |

At your current query volume:
- Estimated additional cost per month: £[X] (at current pricing)
- Estimated latency impact: queries take ~8–15s instead of ~5–8s

Recommended for: dashboards, async reports, any query going to leadership
Not recommended for: high-volume live chat interfaces with latency SLAs

**Recommended configuration:** Adversarial review ON for all queries (default)
```

Record the client's decision in status.md.

### Step 2: Configure Adversarial Review Prompt

The adversarial review is already embedded in the agentic data stack SKILL.md (Step 5 of agent_config/generate.md). If the client chose a standalone adversarial reviewer (separate agent call), configure it here:

```markdown
# Adversarial Reviewer System Prompt

You are the adversarial reviewer for the [client] agentic data stack. Your job is to 
challenge every answer the agentic data stack provides before it reaches the user.

You receive: the original question + the agent's proposed answer + the SQL or metric 
query used.

Systematically check:

1. **Source**: Is the answer from the correct canonical table? Would a different table 
   give a different result?

2. **Filter**: Are the WHERE clauses correct for the question? Revenue questions must 
   exclude returns and cancelled orders. Verify the filter matches the canonical 
   definition in DOMAIN_REFERENCE.md.

3. **Grain**: Is the result at the right granularity? If the question asked for monthly 
   and the answer is daily, flag it.

4. **Plausibility**: Does the number make sense? Apply these sanity checks:
   - Revenue per day should be £X–£Y (ask domain owner to set bounds)
   - Order count per day should be N–M
   - Customer count should be less than total registered users
   
5. **Definition**: Does the metric definition match what the question asked? 
   "Active customers" may differ from "all customers".

If all checks pass: respond "APPROVED — no issues found."
If any check fails: respond "REVISION REQUIRED — [specific issue]" and provide 
the corrected query or answer.

Never approve an answer you suspect is wrong, even partially.
```

### Step 3: Run Calibration Tests

Run 5 adversarial calibration tests — questions where the naive answer would be wrong and the adversarial check should catch it:

| Test | Naive answer | Expected adversarial catch |
|---|---|---|
| "Revenue last month" against wrong table | Returns gross not net | Filter check catches wrong revenue definition |
| "Active customers" without time filter | Returns all customers | Filter check catches missing 30-day window |
| "Orders this week" with daily grain | Returns daily rows | Grain check catches wrong aggregation |

Record which checks fired and whether corrections were accurate.

### Step 4: Set Production Configuration

In `agentic-data-stack-SKILL.md`, confirm the adversarial review section is active. For standalone configuration:

```yaml
# agent_config.yaml
adversarial_review:
  enabled: true
  mode: inline  # inline (built into main agent) | standalone (separate agent call)
  checks:
    - source
    - filter
    - grain
    - plausibility
    - definition
  plausibility_bounds:
    daily_revenue_min: 10000
    daily_revenue_max: 500000
    daily_orders_min: 50
    daily_orders_max: 5000
```

### Step 5: Update Status

```yaml
adversarial_config:
  generate: complete
  generated_date: YYYY-MM-DD
  mode: inline
  client_decision: enabled
  calibration_tests: 5
  calibration_pass_rate: 100%
```

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `adversarial_config`
- `artifact_name`: `Adversarial Config`
- `file_path`: `.wire/[release_folder]/artifacts/adversarial_calibration_results.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- Updated `agentic-data-stack-SKILL.md` (adversarial section confirmed)
- `.wire/<release-folder>/artifacts/adversarial_config.yaml`
- `.wire/<release-folder>/artifacts/adversarial_calibration_results.md`
- Updated `status.md`

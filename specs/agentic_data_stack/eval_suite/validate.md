---
wire_schema: "1.0"
command: validate
artifact: eval_suite
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
  - artifact: eval_suite
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Run eval suite and check per-domain accuracy against targets
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Eval Suite Validate

## Purpose

Run the full eval suite against the agentic data stack and produce a per-domain accuracy report. This is the gate before the launch gate review — domains that don't meet their target are not ready to announce.

## Validation Checks

**Structure checks:**
- [ ] Every domain has ≥10 question-answer pairs (or the target from eval_targets.yaml)
- [ ] Every question has an expected_tier, correct_answer, and verification status
- [ ] eval_targets.yaml exists with a threshold for every domain
- [ ] run_evals.sh exists and is executable

**Accuracy checks (run the eval suite):**

```bash
cd <dbt_project_path> && ./.claude/eval/run_evals.sh all
```

For each domain, compare pass rate against `eval_targets.yaml` threshold.

## Output Format

```markdown
## Eval Suite Validation Results

Run date: YYYY-MM-DD

| Domain | Questions | Passed | Failed | Pass Rate | Target | Status |
|---|---|---|---|---|---|---|
| orders | 15 | 14 | 1 | 93% | 90% | ✅ PASS |
| customers | 12 | 10 | 2 | 83% | 85% | ❌ FAIL |
| marketing | 10 | 9 | 1 | 90% | 80% | ✅ PASS |

**Overall: 2/3 domains passing**

### Failed Questions

**customers_007**: "Show active customers in the EMEA region"  
Expected: customers with last_order in last 30 days AND region = 'EMEA'  
Actual: agent returned all EMEA customers without the 30-day filter  
Root cause: `active_customers_30d` metric does not have a region dimension  
Recommended fix: add region dimension to the active_customers semantic model  
```

Domains that fail are blocked from launch. Record the failed questions and root causes.

## Status Update

```yaml
eval_suite:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass_with_failures  # pass | pass_with_failures | fail
  overall_pass_rate: X%
  domains_passing: N
  domains_failing: N
  domains_blocked: ["customers"]
```

---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Stakeholder review of eval suite question coverage and accuracy results
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Eval Suite Review

## Purpose

Review the eval suite question coverage with domain owners, confirm accuracy results are acceptable, and agree which domains are cleared for launch.

## Workflow

### Step 1: Present Per-Domain Accuracy

Lead with the pass rate table. Be direct about which domains are not ready:

```
## Eval Suite Review

### Domain Accuracy Results

| Domain | Pass Rate | Target | Ready? |
|---|---|---|---|
| orders | 93% | 90% | ✅ Yes |
| customers | 83% | 85% | ❌ No — 2% below target |
| marketing | 90% | 80% | ✅ Yes |
```

### Step 2: Walk Through Failures

For each domain below target, walk through the failing questions with the domain owner:

1. Is the question valid? (Sometimes the question is poorly worded — adjust the eval)
2. Is the expected answer correct? (Sometimes the "correct" answer was wrong — update the baseline)
3. Is the agent genuinely failing? (If yes, identify the root cause and fix before proceeding)

### Step 3: Agree Domain Launch Gates

For each domain, confirm:
- Domains at or above target: cleared for launch announcement
- Domains below target: blocked until the specific failing questions are fixed

Do not let social pressure lower the threshold. A domain launched with 70% accuracy will erode user trust faster than a delayed launch.

### Step 4: Record Sign-off

```markdown
## Eval Suite Review Sign-off

Reviewer: [Name(s)]
Date: YYYY-MM-DD

Domains approved for launch: orders, marketing
Domains blocked pending fixes: customers

Blocked domain actions:
- customers: add region dimension to active_customers_30d metric, re-run evals
```

### Step 5: Update Status

```yaml
eval_suite:
  review: approved_with_conditions
  reviewer: Name
  review_date: YYYY-MM-DD
  domains_cleared: ["orders", "marketing"]
  domains_blocked: ["customers"]
```
